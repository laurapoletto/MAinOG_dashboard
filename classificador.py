"""Classificação automática (somente regras, sem IA, sem custo)."""
import re, warnings
import numpy as np
import pandas as pd
import regras as R0

warnings.filterwarnings("ignore")

CATS = ["Caso concreto de peça", "Geral/revisão", "Material/processo c/ foco setorial",
        "Material/processo sem foco setorial", "Periférico (MA como ferramenta de lab)",
        "Fora do tema", "Sem conteúdo (anais/errata)"]
NUCLEO = CATS[:3]
SEGS = ["Upstream", "Midstream", "Downstream", "O&G (não esp.)", "Marítimo/naval", "Outro setor", "Sem contexto setorial", "Não identificável"]
TIPOS = ["Nova", "Protótipo", "Substituição", "Reparo"]


def regras_padrao():
    return {"AM": R0.AM, "SETOR": R0.SETOR, "BIO": R0.BIO, "PERIF": R0.PERIF}


def _cnt(s, p):
    return s.str.count(p)


def _has(s, p):
    return s.str.contains(p, regex=True)


def preparar(df):
    d = df.copy()
    for c in ["Title", "Abstract", "Author Keywords", "Index Keywords", "Document Type"]:
        if c not in d.columns:
            d[c] = ""
        d[c] = d[c].fillna("").astype(str)
    d["_t"] = d["Title"].str.lower()
    d["_a"] = d["Abstract"].str.lower()
    d["_k"] = (d["Author Keywords"] + " ; " + d["Index Keywords"]).str.lower()
    d["_txt"] = d["_t"] + " . " + d["_a"] + " . " + d["_k"]
    return d


def classificar(df, regras=None):
    R = regras_padrao()
    if regras:
        R.update({k: v for k, v in regras.items() if v})
    d = preparar(df)
    t, a, k, txt = d["_t"], d["_a"], d["_k"], d["_txt"]

    am = _has(txt, R["AM"])
    score = 3 * _cnt(t, R["SETOR"]) + 2 * _cnt(k, R["SETOR"]) + np.minimum(_cnt(a, R["SETOR"]), 4)
    bio = _cnt(txt, R["BIO"])
    d["Score setorial"] = score.astype(int)

    sem = d["Document Type"].isin(R0.SEM_CONTEUDO_TIPOS) | (
        (d["Abstract"].str.len() < 30) & _has(t, R0.SEM_CONTEUDO_TITULO) & ~_has(t, r"additive|3d print"))
    fora = (~am) | ((bio >= 3) & (score < 6)) | ((bio >= 2) & (score < 3)) | (_has(t, R["BIO"]) & (score < 3))
    per = am & (_has(t, R["PERIF"]) | _has(k, R["PERIF"]) | (_cnt(a, R["PERIF"]) >= 2))
    revisao = (d["Document Type"].isin(["Review"]) | _has(t, R0.REVISAO_TITULO) | _has(a, R0.REVISAO_RESUMO))

    # peça: rótulo mais provável (título pesa 3x)
    pts = pd.DataFrame({lab: 3 * _cnt(t, p) + _cnt(a, p) for lab, p in R0.PARTES.items()})
    pts_t = pd.DataFrame({lab: _cnt(t, p) for lab, p in R0.PARTES.items()})
    melhor = pts.idxmax(axis=1).where(pts.max(axis=1) > 0, "")
    part_titulo = pts_t.max(axis=1) > 0
    part_abs = pts.max(axis=1) >= 2
    fabr = _has(a, R0.FABRICACAO)

    concreto = am & ~sem & ~fora & ~per & ~revisao & fabr & (score >= 3) & (part_titulo | (pts.max(axis=1) >= 4))
    alta = concreto & part_titulo & (score >= 4)

    geral = am & ~sem & ~fora & ~per & ~concreto & (revisao | _has(t, R0.REVISAO_TITULO))
    mat_foco = am & ~sem & ~fora & ~per & ~concreto & ~geral & (score >= 3)

    cat = np.select([sem, concreto, per & ~fora, fora, geral, mat_foco],
                    [CATS[6], CATS[0], CATS[4], CATS[5], CATS[1], CATS[2]], default=CATS[3])
    d["Categoria"] = cat
    d["Núcleo setorial"] = np.where(d["Categoria"].isin(NUCLEO), "Sim", "Não")
    d["Confiança"] = np.where(d["Categoria"] == CATS[0], np.where(alta, "Alta", "Média (revisar)"), "")

    # tipo do caso (prioridade: reparo > reposição > protótipo > nova)
    def tipo(i):
        if _hit(t.iloc[i], a.iloc[i], R0.REPARO, 2): return "Reparo"
        if _hit(t.iloc[i], a.iloc[i], R0.SUBSTITUIÇÃO, 2): return "Substituição"
        if _hit(t.iloc[i], a.iloc[i], R0.PROTOTIPO, 2): return "Protótipo"
        return "Nova"
    is_c = (d["Categoria"] == CATS[0]).values
    d["Tipo de caso"] = ""
    d["Peça/componente"] = ""
    for i in np.where(is_c)[0]:
        d.iloc[i, d.columns.get_loc("Tipo de caso")] = tipo(i)
        d.iloc[i, d.columns.get_loc("Peça/componente")] = melhor.iloc[i]

    # segmento
    segs = []
    for i in range(len(d)):
        segs.append(_segmento(txt.iloc[i], int(score.iloc[i]), is_c[i]))
    d["Segmento"] = segs

    # flags de peças / materiais / tecnologias
    for pref, D in (("P", R0.PARTES), ("M", R0.MATERIAIS), ("T", R0.TECNOLOGIAS)):
        for lab, p in D.items():
            d[f"{pref}: {lab}"] = _has(txt, p).astype(int)
    d["Open Access (sim/não)"] = np.where(d.get("Open Access", pd.Series("", index=d.index)).fillna("").astype(str).str.len() > 0, "Sim", "Não")
    return d.drop(columns=["_t", "_a", "_k", "_txt"])


def _hit(t, a, p, n_abs):
    return bool(re.search(p, t)) or len(re.findall(p, a)) >= n_abs


def _segmento(txt, score, concreto):
    if score < 3:
        return "Outro setor" if concreto else "Sem contexto setorial"
    c = {s: len(re.findall(p, txt)) for s, p in R0.SEGMENTOS.items()}
    ma = len(re.findall(R0.MARITIMO, txt))
    og = len(re.findall(R0.OG_GERAL, txt))
    top = max(c, key=c.get)
    if c[top] >= 2 and c[top] >= ma: return top
    if og > 0 and max(c.values()) < 2: return "O&G (não esp.)"
    if ma > 0 and ma >= max(c.values()): return "Marítimo/naval"
    if max(c.values()) >= 1: return top
    return "Não identificável"
