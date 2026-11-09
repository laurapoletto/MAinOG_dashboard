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

FORTE = re.compile(r"universit|universid|université|università|universität|institut|polytechn|politecn|college|academy|academia|"
                   r"fraunhofer|sintef|\bcnrs\b|aramco|\bcnpc\b|petrobras|equinor|\bmit\b|\bnasa\b|\bcsiro\b|\bkaust\b|\bkfupm\b|"
                   r"schlumberger|halliburton|baker hughes|shell\b|\bcnooc\b|\bsinopec\b|\buniv\b|\binst\b|\bacad\b|\bcoll\b|\bpolytech", re.I)
FRACO = re.compile(r"company|corporation|\bcorp\b|\bltd\b|\binc\b|gmbh|\bag\b|\bas\b|\bsa\b|laborator|centre|center|centro|"
                   r"research|school|council|ministry|foundation|fundação|hospital|\bltda\b|\bllc\b|\bctr\b|\blab\b|\bres\b|\bco\b|\bsch\b", re.I)


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
    partes = [x.strip() for x in segmento.split(",") if x.strip()]
    if len(partes) >= 2: partes = partes[:-1]            # remove o país
    for rx in (FORTE, FRACO):
        for p in partes:
            if rx.search(p): return p
    if not partes: return None
    return partes[0] if len(partes) <= 2 else partes[1]


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
