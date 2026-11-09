"""Leitura, junção e remoção de duplicatas de exportações do Scopus (CSV)."""
import re
import pandas as pd


def _chaves(r):
    """Chaves de um registro: (ids fortes: id do Scopus no link e DOI, título normalizado)."""
    fortes = []
    link = str(r.get("Link", "") or "")
    m = re.search(r"2-s2\.0-(\d+)|/publications?/(\d+)|/record/(\d+)", link)
    if m: fortes.append("scopus:" + next(g for g in m.groups() if g))
    else:
        m = re.search(r"eid=([^&]+)", link)
        if m: fortes.append("eid:" + m.group(1))
    doi = str(r.get("DOI", "") or "").strip().lower()
    if doi and doi != "nan": fortes.append("doi:" + doi)
    t = re.sub(r"[^a-z0-9]", "", str(r.get("Title", "")).lower())
    return fortes, (t if len(t) > 25 else None)


def _grupos(base):
    """Junta registros iguais vindos de arquivos diferentes (campos diferentes, mesmo artigo).
    1) une por id do Scopus ou DOI; 2) une por título idêntico, desde que os ids/DOIs não se contradigam
    (um artigo de conferência e a versão de periódico, com o mesmo título, continuam separados)."""
    n = len(base); pai = list(range(n))

    def raiz(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]; x = pai[x]
        return x
    info = [_chaves(r) for _, r in base.iterrows()]
    # 1) une por id do Scopus
    visto = {}
    for i, (fortes, _) in enumerate(info):
        for k in fortes:
            if k.startswith("doi:"): continue
            if k in visto: pai[raiz(i)] = raiz(visto[k])
            else: visto[k] = i
    ids = {}
    for i, (fortes, _) in enumerate(info):
        ids.setdefault(raiz(i), set()).update(k for k in fortes if not k.startswith("doi:"))
    # 2) une por DOI, exceto se os ids do Scopus forem diferentes (registros distintos que repetem o DOI)
    por_doi = {}
    for i, (fortes, _) in enumerate(info):
        for k in fortes:
            if k.startswith("doi:"): por_doi.setdefault(k, []).append(i)
    for lst in por_doi.values():
        base_r = None
        for i in lst:
            r_ = raiz(i)
            if base_r is None: base_r = r_; continue
            if r_ == base_r: continue
            if ids[base_r] and ids[r_] and not (ids[base_r] & ids[r_]): continue
            pai[r_] = base_r; ids[base_r] |= ids[r_]
    dois = {}
    for i, (fortes, _) in enumerate(info):
        dois.setdefault(raiz(i), set()).update(k for k in fortes if k.startswith("doi:"))
    ids2 = {}
    for i, (fortes, _) in enumerate(info):
        ids2.setdefault(raiz(i), set()).update(k for k in fortes if not k.startswith("doi:"))
    ids = ids2
    por_titulo = {}
    for i, (_, t) in enumerate(info):
        if t: por_titulo.setdefault(t, []).append(i)
    for lst in por_titulo.values():
        base_r = None
        for i in lst:
            r_ = raiz(i)
            if base_r is None: base_r = r_; continue
            if r_ == base_r: continue
            conflito = (ids[base_r] and ids[r_] and not (ids[base_r] & ids[r_])) or (dois[base_r] and dois[r_] and not (dois[base_r] & dois[r_]))
            if not conflito:
                pai[r_] = base_r
                ids[base_r] |= ids[r_]; dois[base_r] |= dois[r_]
    return [raiz(i) for i in range(n)]


def ler_csv(arquivo, busca):
    df = pd.read_csv(arquivo, encoding="utf-8-sig")
    df.columns = [c.strip().strip('"').replace("\ufeff", "") for c in df.columns]
    df["Busca"] = busca
    df["Base"] = "Scopus"
    return df


def juntar(lista):
    """lista = [(DataFrame, nome_da_busca), ...]. Une tudo; duplicatas viram uma linha com várias buscas."""
    base = pd.concat([d.assign(Busca=n) for d, n in lista], ignore_index=True)
    base["_k"] = _grupos(base)
    juntar_ = lambda s: "; ".join(dict.fromkeys(s))
    buscas = base.groupby("_k")["Busca"].agg(juntar_)
    bases = base.groupby("_k")["Base"].agg(juntar_) if "Base" in base.columns else None
    total = len(base)
    unico = base.groupby("_k", sort=False).first()  # primeiro valor não nulo de cada coluna
    unico["Busca"] = buscas.reindex(unico.index)
    if bases is not None: unico["Base"] = bases.reindex(unico.index)
    unico = unico.reset_index(drop=True)
    unico.attrs["duplicatas_removidas"] = total - len(unico)
    return unico


# colunas que o app usa e o que se perde quando faltam
IMPORTANTES = {
    "Year": "gráfico e filtro de ano",
    "Open Access": "porcentagem de Open Access",
    "Source title": "ranking de fontes (revistas/eventos)",
    "Document Type": "detecção de capas de anais e errata",
    "Abstract": "classificação por resumo (fica muito pior só com o título)",
}


def garantir_colunas(df):
    """Cria colunas ausentes (vazias) para o app não quebrar e devolve a lista do que está faltando."""
    faltando = [c for c in IMPORTANTES if c not in df.columns or (c == "Year" and pd.to_numeric(df[c], errors="coerce").isna().all())]
    for c in ["Title", "Year", "Source title", "Cited by", "DOI", "Link", "Abstract", "Author Keywords", "Index Keywords",
              "Document Type", "Open Access"]:
        if c not in df.columns: df[c] = pd.NA
    return df, faltando
