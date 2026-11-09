"""Gráficos (matplotlib). Cada função recebe o DataFrame classificado e devolve uma Figure."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import classificador as C
import autoria

AZUL, CINZA, LARANJA, VERDE = "#1F3864", "#A6A6A6", "#ED7D31", "#548235"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})


def _barh(serie, titulo, cor=AZUL, xlabel="Nº de registros"):
    serie = serie.sort_values()
    fig, ax = plt.subplots(figsize=(7, 0.42 * max(len(serie), 2) + 1.2))
    ax.barh(serie.index.astype(str), serie.values, color=cor)
    m = max(serie.max(), 1)
    for y, v in enumerate(serie.values): ax.text(v + m * 0.01, y, int(v), va="center", fontsize=9)
    ax.set_title(titulo, loc="left", fontweight="bold"); ax.set_xlabel(xlabel)
    return fig


def relevancia(d):
    return _barh(d["Categoria"].value_counts().reindex(C.CATS).fillna(0), f"Relevância ({len(d)} registros)")


def open_access(d):
    oa = d["Open Access (sim/não)"].eq("Sim")
    t = pd.DataFrame({"s": oa.groupby(d["Categoria"]).sum(), "n": oa.groupby(d["Categoria"]).count()}).reindex(C.CATS).dropna()
    t["p"] = t.s / t.n * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(t.index[::-1], t.p[::-1], color=VERDE)
    for y, (p, s, n) in enumerate(zip(t.p[::-1], t.s[::-1], t.n[::-1])): ax.text(p + 1, y, f"{p:.0f}% ({int(s)}/{int(n)})", va="center", fontsize=9)
    ax.axvline(oa.mean() * 100, color=LARANJA, ls="--", lw=1)
    ax.set_xlim(0, 80); ax.set_xlabel("% Open Access"); ax.set_title(f"Open Access por categoria (média {oa.mean()*100:.0f}%)", loc="left", fontweight="bold")
    return fig


def por_ano(d):
    a = d.copy(); a["Year"] = pd.to_numeric(a["Year"], errors="coerce"); a = a[a["Year"] >= 2005]
    a["g"] = a["Núcleo setorial"].map({"Sim": "Núcleo setorial", "Não": "Demais"})
    if a.empty:
        fig, ax = plt.subplots(figsize=(8, 2)); ax.axis("off")
        ax.text(0.5, 0.5, "Sem dados de ano nos arquivos enviados", ha="center", va="center"); return fig
    p = a.groupby(["Year", "g"]).size().unstack(fill_value=0)
    for c in ["Núcleo setorial", "Demais"]:
        if c not in p: p[c] = 0
    fig, ax = plt.subplots(figsize=(8, 4))
    p[["Núcleo setorial", "Demais"]].rename(index=int).plot(kind="bar", stacked=True, ax=ax, color=[AZUL, CINZA], width=0.8)
    ax.set_xlabel(""); ax.set_ylabel("Nº de registros"); ax.legend(frameon=False); ax.set_title("Publicações por ano", loc="left", fontweight="bold")
    return fig


def tipo_caso(d):
    c = d[d["Categoria"] == C.CATS[0]]["Tipo de caso"].value_counts().reindex(C.TIPOS).fillna(0)
    return _barh(c, f"Casos concretos: tipo (n={int(c.sum())})", LARANJA)


def segmento(d):
    nuc = d["Núcleo setorial"].eq("Sim"); con = d["Categoria"].eq(C.CATS[0])
    S = [s for s in C.SEGS if s not in ("Sem contexto setorial",)]
    s1 = d[con]["Segmento"].value_counts().reindex(S).fillna(0); s2 = d[nuc]["Segmento"].value_counts().reindex(S).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4)); w = 0.4; x = range(len(S))
    ax.bar([i - w / 2 for i in x], s1, w, label=f"Casos concretos (n={con.sum()})", color=LARANJA)
    ax.bar([i + w / 2 for i in x], s2, w, label=f"Núcleo setorial (n={nuc.sum()})", color=AZUL)
    for i, (u, v) in enumerate(zip(s1, s2)):
        ax.text(i - w / 2, u + .5, int(u), ha="center", fontsize=8); ax.text(i + w / 2, v + .5, int(v), ha="center", fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels(S, rotation=25, ha="right"); ax.legend(frameon=False)
    ax.set_title("Segmento da cadeia", loc="left", fontweight="bold")
    return fig


def _comparativo(d, pref, titulo):
    cols = [c for c in d.columns if c.startswith(pref + ": ")]
    nuc = d["Núcleo setorial"].eq("Sim"); sf = d["Categoria"].eq(C.CATS[3])
    a = d.loc[nuc, cols].sum(); b = a + d.loc[sf, cols].sum()
    t = pd.DataFrame({"Núcleo setorial": a, "Núcleo + MA geral": b}); t.index = [c[3:] for c in t.index]
    t = t.sort_values("Núcleo + MA geral")
    fig, ax = plt.subplots(figsize=(8, 0.5 * len(t) + 1.5))
    t.plot(kind="barh", ax=ax, color=[AZUL, CINZA], width=0.8)
    ax.set_xlabel("Registros que mencionam"); ax.legend(frameon=False, loc="lower right"); ax.set_title(titulo, loc="left", fontweight="bold")
    return fig


def pecas(d): return _comparativo(d, "P", "Peças/equipamentos mencionados")
def materiais(d): return _comparativo(d, "M", "Materiais mencionados")
def tecnologias(d): return _comparativo(d, "T", "Tecnologias de MA mencionadas")


def fontes(d):
    return _barh(d.loc[d["Núcleo setorial"].eq("Sim"), "Source title"].fillna("—").value_counts().head(10), "Fontes mais frequentes (núcleo setorial)", CINZA)


def comparacao_buscas(d):
    """Barras empilhadas por busca (um registro com várias buscas conta em cada uma)."""
    x = d.assign(b=d["Busca"].str.split("; ")).explode("b").reset_index(drop=True)
    t = pd.crosstab(x["b"], x["Categoria"]).reindex(columns=C.CATS, fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(t) + 1.8))
    cores = [LARANJA, "#F4B183", AZUL, "#8FAADC", "#BFBFBF", "#D9D9D9", "#EDEDED"]
    t.plot(kind="barh", stacked=True, ax=ax, color=cores, width=0.7)
    ax.set_xlabel("Registros"); ax.set_ylabel(""); ax.set_title("Composição de cada busca", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
    return fig


def tabela_buscas(d):
    x = d.assign(b=d["Busca"].str.split("; ")).explode("b").reset_index(drop=True)
    g = x.groupby("b")
    t = pd.DataFrame({"Registros": g.size(),
                      "Núcleo setorial": g["Núcleo setorial"].apply(lambda s: (s == "Sim").sum()),
                      "Casos concretos": g["Categoria"].apply(lambda s: (s == C.CATS[0]).sum()),
                      "Fora do tema": g["Categoria"].apply(lambda s: (s == C.CATS[5]).sum()),
                      "Exclusivos (só nesta busca)": g.apply(lambda z: (~z["Busca"].str.contains(";")).sum())})
    t["% núcleo"] = (t["Núcleo setorial"] / t["Registros"] * 100).round(1)
    t["% fora do tema"] = (t["Fora do tema"] / t["Registros"] * 100).round(1)
    return t


def _rank_chart(d, col, titulo, n=15):
    nuc = d["Núcleo setorial"].eq("Sim")
    r = autoria.ranking(d, col, n)
    return _barh(r, titulo + f" (todos os registros, n={len(d)})", AZUL)


def paises(d): return _rank_chart(d, "Países", "Países")
def instituicoes(d): return _rank_chart(d, "Instituições", "Instituições")
def autores(d): return _rank_chart(d, "Autores (lista)", "Autores")


def todos(d):
    d_ = {"01_relevancia": relevancia, "02_open_access": open_access, "03_publicacoes_por_ano": por_ano,
          "04_tipo_caso": tipo_caso, "05_segmento": segmento, "06_pecas": pecas, "07_materiais": materiais,
          "08_tecnologias": tecnologias, "09_fontes": fontes}
    if "Países" in d.columns: d_["11_paises"] = paises; d_["12_instituicoes"] = instituicoes
    if "Autores (lista)" in d.columns: d_["13_autores"] = autores
    if d["Busca"].nunique() > 1 or d["Busca"].str.contains(";").any(): d_["10_comparacao_buscas"] = comparacao_buscas
    return d_
