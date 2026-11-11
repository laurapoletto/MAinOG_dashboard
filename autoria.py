"""Países, instituições e autores a partir das colunas do Scopus (Affiliations, Author full names / Authors)."""
import re
import unicodedata
from collections import Counter
from itertools import combinations
import pandas as pd

SEP = "; "

PAIS_PT = {
    "United States": "EUA", "United Kingdom": "Reino Unido", "Russian Federation": "Rússia", "South Korea": "Coreia do Sul",
    "Czech Republic": "Tchéquia", "Germany": "Alemanha", "France": "França", "Italy": "Itália", "Spain": "Espanha",
    "Brazil": "Brasil", "Norway": "Noruega", "Netherlands": "Países Baixos", "Japan": "Japão", "India": "Índia",
    "Saudi Arabia": "Arábia Saudita", "United Arab Emirates": "Emirados Árabes", "Singapore": "Singapura", "Canada": "Canadá",
    "Australia": "Austrália", "Turkey": "Turquia", "Türkiye": "Turquia", "Iran": "Irã", "Switzerland": "Suíça", "Sweden": "Suécia",
    "Denmark": "Dinamarca", "Finland": "Finlândia", "Austria": "Áustria", "Belgium": "Bélgica", "Poland": "Polônia",
    "Portugal": "Portugal", "Greece": "Grécia", "Malaysia": "Malásia", "Indonesia": "Indonésia", "Thailand": "Tailândia",
    "Egypt": "Egito", "Algeria": "Argélia", "Croatia": "Croácia", "Hungary": "Hungria", "Romania": "Romênia",
    "Ukraine": "Ucrânia", "Mexico": "México", "Argentina": "Argentina", "Chile": "Chile", "Colombia": "Colômbia",
    "South Africa": "África do Sul", "Nigeria": "Nigéria", "Pakistan": "Paquistão", "Qatar": "Catar", "Kuwait": "Kuwait",
    "Oman": "Omã", "Iraq": "Iraque", "Israel": "Israel", "Ireland": "Irlanda", "New Zealand": "Nova Zelândia",
    "Hong Kong": "Hong Kong", "Taiwan": "Taiwan", "China": "China", "Vietnam": "Vietnã", "Slovenia": "Eslovênia",
    "USA": "EUA", "Peoples R China": "China", "England": "Reino Unido", "Scotland": "Reino Unido", "Wales": "Reino Unido",
    "North Ireland": "Reino Unido", "Northern Ireland": "Reino Unido", "Russia": "Rússia", "U Arab Emirates": "Emirados Árabes",
    "Turkiye": "Turquia", "Viet Nam": "Vietnã", "Czechia": "Tchéquia",
    "Slovakia": "Eslováquia", "Serbia": "Sérvia", "Bulgaria": "Bulgária", "Lithuania": "Lituânia", "Estonia": "Estônia",
}

# Níveis de prioridade para achar o NOME da instituição dentro de uma afiliação "Dept, Instituição, Cidade, País".
# 1) universidades; 2) institutos/empresas conhecidas; 3) empresas e centros genéricos; 4) subunidades (faculdade, escola, depto) só em último caso.
T1 = re.compile(r"universit|universid|université|università|universität|universiti|universitas|\buniv\b|polytechn|politecn", re.I)
T2 = re.compile(r"institut|\binst\b|academy|academia|\bacad\b|fraunhofer|sintef|\bcnrs\b|aramco|\bcnpc\b|petrobras|equinor|\bmit\b|"
                r"\bnasa\b|\bcsiro\b|\bkaust\b|\bkfupm\b|schlumberger|halliburton|baker hughes|shell\b|\bcnooc\b|\bsinopec\b|"
                r"council|ministry|foundation|fundação|hospital", re.I)
T3 = re.compile(r"company|corporation|\bcorp\b|\bltd\b|\binc\b|gmbh|\bag\b|\bas\b|\bsa\b|\bltda\b|\bllc\b|\bco\b|\bplc\b|"
                r"research|laborator|centre|center|centro|\bctr\b|\blab\b|\bres\b", re.I)
T4 = re.compile(r"college|\bcoll\b|school|\bsch\b|department|\bdept\b|faculty|division", re.I)
# "Ltd.", "Inc.", "Co." soltos (a vírgula separa "X Co." de "Ltd.") e sufixos legais no fim do nome
SUFIXO_SOLTO = re.compile(r"^(?:ltd|ltda|inc|llc|co|corp|corporation|limited|gmbh|ag|sa|s\.a|plc|pty|lp|llp|bv|nv|kg)\.?$", re.I)
SUFIXO_FIM = re.compile(r"(?:[,\s]+(?:co|ltd|ltda|inc|llc|corp|corporation|limited|gmbh|plc|pty|lp|llp|bv|nv|ag|sa|kg)\.?)+$", re.I)


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    s = re.sub(r"^the ", "", s)
    return re.sub(r"\s+", " ", s)


def _pais(segmento):
    p = segmento.split(",")[-1].strip().rstrip(".")
    if re.search(r"\d", p): p = re.sub(r"^.*\d[\d\-]*\s*", "", p).strip()   # "MA 02139 USA" -> "USA" (formato WoS)
    if not p or len(p) > 40 or re.search(r"\d", p): return None
    return PAIS_PT.get(p, p)


def _instituicao(segmento):
    brutas = [x.strip() for x in segmento.split(",") if x.strip()]
    if len(brutas) >= 2: brutas = brutas[:-1]            # remove o país
    partes = []
    for p in brutas:                                      # cola "Ltd.", "Inc." etc. no nome anterior: "X Co." + "Ltd." -> "X Co., Ltd."
        if partes and SUFIXO_SOLTO.match(p): partes[-1] = partes[-1] + ", " + p
        else: partes.append(p)
    if not partes: return None
    escolhida = None
    for rx in (T1, T2, T3, T4):
        escolhida = next((p for p in partes if rx.search(p)), None)
        if escolhida: break
    if not escolhida: escolhida = partes[0] if len(partes) <= 2 else partes[1]
    limpo = SUFIXO_FIM.sub("", escolhida).strip(" ,")      # "Baker Hughes Co." e "Baker Hughes" viram o mesmo nome
    return limpo or escolhida


def _unicos(lista):
    vistos, saida = set(), []
    for x in lista:
        k = _norm(x)
        if k and k not in vistos:
            vistos.add(k); saida.append(x)
    return saida


def _autores(row):
    txt = row.get("Author full names")
    if not isinstance(txt, str) or not txt.strip():
        txt = row.get("Authors")
    if not isinstance(txt, str) or "No author name" in txt: return []
    nomes = [re.sub(r"\s*\(\d+\)\s*$", "", n).strip() for n in txt.split(";")]
    return _unicos([n for n in nomes if n])


def enriquecer(d):
    """Adiciona colunas 'Países', 'Instituições' e 'Autores (lista)' (itens separados por '; ')."""
    d = d.copy()
    tem_aff = "Affiliations" in d.columns and d["Affiliations"].notna().any()
    tem_aut = any(c in d.columns and d[c].notna().any() for c in ("Author full names", "Authors"))
    d.attrs["tem_afiliacao"] = bool(tem_aff); d.attrs["tem_autores"] = bool(tem_aut)
    if tem_aff:
        paises, insts, ip = [], [], []
        for s in d["Affiliations"].fillna(""):
            segs = [x.strip() for x in str(s).split(";") if x.strip()]
            paises.append(SEP.join(_unicos([p for p in map(_pais, segs) if p])))
            insts.append(SEP.join(_unicos([i for i in map(_instituicao, segs) if i])))
            pares = [(_pais(x), _instituicao(x)) for x in segs]
            ip.append(SEP.join(_unicos([f"{p}|{i}" for p, i in pares if p and i])))
        d["Países"], d["Instituições"], d["_InstPais"] = paises, insts, ip
    if tem_aut:
        d["Autores (lista)"] = [SEP.join(_autores(r)) for _, r in d.iterrows()]
    return d


def itens(serie):
    return serie.fillna("").map(lambda s: [x for x in s.split(SEP) if x])


def ranking(d, col, n=15, base=None):
    """Nº de artigos por item (cada artigo conta uma vez por item). base = máscara booleana opcional."""
    x = d if base is None else d[base]
    if col not in x.columns: return pd.Series(dtype=int)
    c = Counter(i for lst in itens(x[col]) for i in lst)
    s = pd.Series(c, dtype=int).sort_values(ascending=False)
    return s.head(n) if n else s


def ranking_instituicoes(d, paises=None, n=15):
    """Instituições mais frequentes. Se `paises` for dado, só conta instituições DESSES países."""
    if "_InstPais" not in d.columns: return pd.Series(dtype=int)
    c = Counter()
    for lst in itens(d["_InstPais"]):
        for x in lst:
            pais, _, inst = x.partition("|")
            if not paises or pais in paises: c[inst] += 1
    s = pd.Series(c, dtype=int).sort_values(ascending=False)
    return s.head(n) if n else s


def com_paises(d, paises):
    """Artigos que têm pelo menos um dos países (lista vazia = todos)."""
    if not paises: return d
    return d[itens(d["Países"]).map(lambda l: any(p in l for p in paises))]


def filtrar_item(d, col, item):
    return d[itens(d[col]).map(lambda l: item in l)]


def pares_paises(d, n=15, base=None, incluir=None):
    """Pares de países que mais colaboram. Se `incluir` for dado, só pares que contêm algum desses países."""
    x = d if base is None else d[base]
    c = Counter()
    for lst in itens(x["Países"]):
        for a, b in combinations(sorted(set(lst)), 2):
            if not incluir or a in incluir or b in incluir: c[(a, b)] += 1
    return pd.DataFrame([(f"{a} – {b}", v) for (a, b), v in c.most_common(n)], columns=["Par de países", "Artigos"])


def pct_colaboracao_internacional(d):
    n = itens(d["Países"]).map(len)
    ok = n > 0
    return (n[ok] >= 2).mean() * 100 if ok.any() else 0.0
