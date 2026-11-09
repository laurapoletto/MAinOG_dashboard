"""Leitura de exportações do Web of Science (tab-delimited .txt, .xls e .xlsx) no formato interno (colunas estilo Scopus)."""
import csv
import io
import re

import pandas as pd

# Tab-delimited / plain text (cabeçalho com etiquetas de 2 letras)
TAGS = {"TI": "Title", "AB": "Abstract", "DE": "Author Keywords", "ID": "Index Keywords", "PY": "Year", "DI": "DOI",
        "SO": "Source title", "DT": "Document Type", "TC": "Cited by", "AU": "Authors", "AF": "Author full names",
        "C1": "_enderecos", "OA": "Open Access", "UT": "_UT"}
# Excel (cabeçalho com nomes longos)
LONGOS = {"Article Title": "Title", "Abstract": "Abstract", "Author Keywords": "Author Keywords", "Keywords Plus": "Index Keywords",
          "Publication Year": "Year", "DOI": "DOI", "Source Title": "Source title", "Document Type": "Document Type",
          "Times Cited, WoS Core": "Cited by", "Authors": "Authors", "Author Full Names": "Author full names",
          "Addresses": "_enderecos", "Open Access Designations": "Open Access", "UT (Unique WOS ID)": "_UT"}

TIPOS = {"proceedings paper": "Conference paper", "editorial material": "Editorial", "meeting abstract": "Conference review",
         "correction": "Erratum", "retracted publication": "Retracted", "retraction": "Retracted", "book chapter": "Book chapter",
         "review": "Review", "article": "Article", "note": "Note", "letter": "Letter"}


def _tipo(s):
    if not isinstance(s, str) or not s.strip(): return ""
    partes = [p.strip().lower() for p in s.split(";")]
    for p in partes:                       # "Review" e tipos sem conteúdo têm prioridade
        if p in ("review", "correction", "retracted publication", "retraction", "meeting abstract", "editorial material"):
            return TIPOS[p]
    return TIPOS.get(partes[0], s.split(";")[0].strip())


def enderecos(c1):
    """Endereços do campo C1/Addresses: remove '[autores]' e devolve 'end1; end2'."""
    if not isinstance(c1, str) or not c1.strip(): return ""
    c1 = c1.strip()
    itens = re.findall(r"\[[^\]]*\]\s*([^\[]*)", c1) if "[" in c1 else c1.split(";")
    limpos = []
    for it in itens:
        it = it.strip().rstrip(";").strip().rstrip(".").strip()
        if it: limpos.append(it)
    return "; ".join(limpos)


def _decodificar(b):
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"): return b.decode("utf-16")
    try: return b.decode("utf-8-sig")
    except UnicodeDecodeError: return b.decode("latin-1")


def ler(conteudo, nome_arquivo, busca):
    n = nome_arquivo.lower()
    if n.endswith((".xls", ".xlsx")):
        try:
            df = pd.read_excel(io.BytesIO(conteudo), dtype=str)
        except ImportError as e:
            raise ImportError("Para ler .xls antigo instale xlrd: pip install xlrd  (ou exporte do WoS como 'Tab delimited file')") from e
    elif n.endswith((".txt", ".tsv", ".tab")):
        df = pd.read_csv(io.StringIO(_decodificar(conteudo)), sep="\t", dtype=str, quoting=csv.QUOTE_NONE, on_bad_lines="skip")
    else:
        raise ValueError("Formato não suportado. Exporte do Web of Science como 'Tab delimited file' (.txt) ou 'Excel'.")
    df.columns = [str(c).strip().strip('"').replace("\ufeff", "") for c in df.columns]
    mapa = {**{k: v for k, v in TAGS.items()}, **LONGOS}
    if "TI" not in df.columns and "Article Title" not in df.columns:
        raise ValueError("Não encontrei as colunas do Web of Science (TI / Article Title). Exporte com 'Full Record'.")
    out = pd.DataFrame(index=df.index)
    for origem, destino in mapa.items():
        if origem in df.columns and destino not in out.columns: out[destino] = df[origem]
    for c in ("Title", "Abstract", "Author Keywords", "Index Keywords", "Authors", "Author full names", "Source title", "DOI"):
        if c not in out: out[c] = ""
    out["Year"] = pd.to_numeric(out.get("Year"), errors="coerce")
    out["Cited by"] = pd.to_numeric(out.get("Cited by"), errors="coerce")
    out["Document Type"] = out.get("Document Type", pd.Series("", index=out.index)).map(_tipo)
    if "Open Access" not in out: out["Open Access"] = ""
    out["Affiliations"] = out["_enderecos"].map(enderecos) if "_enderecos" in out else ""
    ut = out["_UT"].fillna("") if "_UT" in out else pd.Series("", index=out.index)
    out["Link"] = ut.map(lambda u: f"https://www.webofscience.com/wos/woscc/full-record/{u}" if u else "")
    out = out.drop(columns=[c for c in ("_enderecos", "_UT") if c in out])
    out = out[out["Title"].fillna("").str.strip() != ""].reset_index(drop=True)
    out["Busca"] = busca; out["Base"] = "Web of Science"
    return out
