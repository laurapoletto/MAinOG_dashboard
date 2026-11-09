"""Leitura, junção e remoção de duplicatas de exportações do Scopus (CSV)."""
import re
import pandas as pd


def _chave(r):
    doi = str(r.get("DOI", "") or "").strip().lower()
    if doi and doi != "nan":
        return "doi:" + doi
    link = str(r.get("Link", "") or "")
    m = re.search(r"eid=([^&]+)", link)
    if m:
        return "eid:" + m.group(1)
    t = re.sub(r"[^a-z0-9]", "", str(r.get("Title", "")).lower())
    return "t:" + t


def ler_csv(arquivo, busca):
    df = pd.read_csv(arquivo, encoding="utf-8-sig")
    df.columns = [c.strip().strip('"').replace("\ufeff", "") for c in df.columns]
    df["Busca"] = busca
    df["Base"] = "Scopus"
    return df


def juntar(lista):
    """lista = [(DataFrame, nome_da_busca), ...]. Une tudo; duplicatas viram uma linha com várias buscas."""
    base = pd.concat([d.assign(Busca=n) for d, n in lista], ignore_index=True)
    base["_k"] = base.apply(_chave, axis=1)
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
