"""Dashboard bibliométrico (Streamlit). Rodar:  streamlit run app.py"""
import inspect
import io

import pandas as pd
import streamlit as st

import autoria
import classificador as C
import dados
import wos
import exportador
import exportar_graficos
import graficos as G

try:
    import interativo as I
    TEM_PLOTLY = True
except ImportError:
    TEM_PLOTLY = False
# clique em barras exige Streamlit >= 1.35 e plotly
CLIQUE = TEM_PLOTLY and "on_select" in inspect.signature(st.plotly_chart).parameters

st.set_page_config(page_title="Dashboard bibliométrico – Aplicações de MA no setor O&G", layout="wide")
st.title("Dashboard bibliométrico – Aplicações de MA no setor O&G")
st.caption("Envie exportações do Scopus (.csv) e/ou do Web of Science (.txt tab-delimited ou Excel). Classificação 100% por regras, sem IA e sem custo.")

# ---------------- Entrada ----------------
with st.sidebar:
    st.header("1. Dados")
    arq_sc = st.file_uploader("Scopus (.csv)", type=["csv"], accept_multiple_files=True, key="up_sc")
    with st.expander("Como exportar do Scopus (campos a marcar)"):
        st.markdown(
            "Em **Export → CSV**, marque:\n\n"
            "**Citation information**: marque tudo (Author(s), Document title, Year, EID, Source title, Volume/issues/pages, "
            "Citation count, Source & document type, Publication stage, DOI, Open access).\n\n"
            "**Bibliographical information**: marque **Affiliations** (necessário para países e instituições).\n\n"
            "**Abstract & keywords**: marque **Abstract**, **Author keywords** e **Indexed keywords** (necessários para a classificação).\n\n"
            "Não precisa marcar: Funding details, Other information e *Include references* (só deixam o arquivo pesado). "
            "*Truncate to optimize for Excel* pode ficar ligado. "
            "Se o Scopus limitar o tamanho, exporte em partes (por ano, por exemplo) e envie todos os arquivos juntos: "
            "o app une e remove as duplicatas.")
    arq_wos = st.file_uploader("Web of Science (.txt tab-delimited, .xls ou .xlsx)", type=["txt", "tsv", "xls", "xlsx"],
                               accept_multiple_files=True, key="up_wos")
    with st.expander("Como exportar do Web of Science"):
        st.markdown("No WoS: **Export → Tab delimited file** (ou Excel), em **Record Content: Full Record**. "
                    "O WoS não exporta CSV. O formato .txt tab-delimited é o mais simples (não precisa de nada extra). "
                    "O WoS costuma limitar cada exportação a cerca de 1.000 registros: exporte em partes e envie todos os arquivos. "
                    "Pode misturar Scopus e WoS: duplicatas (mesmo DOI ou título) viram um registro só.")
    arquivos = [(f_, "Scopus") for f_ in arq_sc or []] + [(f_, "Web of Science") for f_ in arq_wos or []]
    nomes = {}
    for f_, base_ in arquivos:
        nomes[(base_, f_.name)] = st.text_input(f"Nome da busca para {f_.name}", value=f_.name.rsplit(".", 1)[0][:40], key=f"n_{base_}_{f_.name}")
    with st.expander("Regras avançadas (regex)"):
        base = C.regras_padrao()
        r_am = st.text_area("Manufatura aditiva", base["AM"], height=90)
        r_setor = st.text_area("Contexto do setor", base["SETOR"], height=110)
        r_bio = st.text_area("Fora do tema (bio, médico, civil...)", base["BIO"], height=90)
        r_per = st.text_area("Periférico (lab/reservatório)", base["PERIF"], height=90)
        st.caption("Para mudar peças, materiais e tecnologias, edite regras.py.")


@st.cache_data(show_spinner="Lendo, juntando e classificando...")
def processar(conteudos, nomes_busca, regras):
    lista = []
    for (fn, b, base_), n in zip(conteudos, nomes_busca):
        df_ = dados.ler_csv(io.BytesIO(b), n) if base_ == "Scopus" else wos.ler(b, fn, n)
        lista.append((df_, n))
    m = dados.juntar(lista)
    dup = m.attrs.get("duplicatas_removidas", 0)
    m, faltando = dados.garantir_colunas(m)
    d = autoria.enriquecer(C.classificar(m, regras))
    return d, dup, d.attrs.get("tem_afiliacao", False), d.attrs.get("tem_autores", False), faltando


@st.cache_data(show_spinner="Gerando planilha...")
def gerar_xlsx(df):
    return exportador.exportar_xlsx(df)


@st.cache_data(show_spinner="Gerando gráficos...")
def gerar_zip(df):
    return exportar_graficos.zip_graficos(df)


if not arquivos:
    st.info("Envie um ou mais arquivos do Scopus (.csv) e/ou do Web of Science (.txt ou Excel) na barra lateral para começar.")
    st.stop()

conteudos = tuple((f_.name, f_.getvalue(), base_) for f_, base_ in arquivos)
try:
    d, dup, TEM_AFIL, TEM_AUT, FALTANDO = processar(conteudos, tuple(nomes[(base_, f_.name)] for f_, base_ in arquivos),
                                          {"AM": r_am, "SETOR": r_setor, "BIO": r_bio, "PERIF": r_per})
except Exception as e:
    st.error(f"Não consegui ler os arquivos: {e}")
    st.stop()

if FALTANDO:
    st.warning("Seus arquivos não têm: " + "; ".join(f"**{c}** (afeta: {dados.IMPORTANTES[c]})" for c in FALTANDO) +
               ". O app funciona, mas essas partes ficam vazias ou limitadas. Reexporte do Scopus marcando *Citation information* "
               "(ano, fonte, tipo, Open Access) e *Abstract & keywords*, ou envie também o outro arquivo da mesma busca: eles são unidos automaticamente.")

# ---------------- Filtros ----------------
with st.sidebar:
    st.header("2. Filtros")
    anos = pd.to_numeric(d["Year"], errors="coerce")
    if anos.notna().any():
        a0, a1 = int(anos.min()), int(anos.max())
        faixa = st.slider("Ano", a0, a1, (a0, a1)) if a0 < a1 else (a0, a1)
    else:
        faixa = None
    todas_buscas = sorted({b for s in d["Busca"] for b in s.split("; ")})
    f_oa = st.radio("Open Access", ["Todos", "Só OA", "Só fechados"], horizontal=True)
    so_nucleo = st.checkbox("Só núcleo setorial", value=False)
    with st.expander("Busca, categoria e segmento", expanded=False):
        f_busca = st.multiselect("Busca", todas_buscas, default=todas_buscas)
        f_cat = st.multiselect("Categoria", C.CATS, default=C.CATS)
        f_seg = st.multiselect("Segmento", C.SEGS, default=C.SEGS)

f = d.copy()
if faixa is not None:
    f = f[(anos.reindex(f.index) >= faixa[0]) & (anos.reindex(f.index) <= faixa[1])]
f = f[f["Busca"].apply(lambda s: any(b in f_busca for b in s.split("; ")))]
f = f[f["Categoria"].isin(f_cat) & f["Segmento"].isin(f_seg)]
if f_oa == "Só OA": f = f[f["Open Access (sim/não)"] == "Sim"]
if f_oa == "Só fechados": f = f[f["Open Access (sim/não)"] == "Não"]
if so_nucleo: f = f[f["Núcleo setorial"] == "Sim"]
if f.empty:
    st.warning("Nenhum registro com esses filtros.")
    st.stop()
f = f.reset_index(drop=True)

# ---------------- Helpers de gráfico clicável ----------------
COLS_ART = ["Title", "Year", "Source title", "Categoria", "Tipo de caso", "Peça/componente", "Segmento", "Busca",
            "Open Access (sim/não)", "Países", "Base", "DOI", "Link"]


def tabela_artigos(sub, chave):
    cols = [c for c in COLS_ART if c in sub.columns]
    st.dataframe(sub[cols], hide_index=True, use_container_width=True,
                 column_config={"Link": st.column_config.LinkColumn("Link")} if "Link" in cols else None)
    st.download_button("Baixar esta seleção (CSV)", sub.to_csv(index=False).encode("utf-8-sig"), "selecao.csv", "text/csv", key="dl_" + chave)


def rotulos_sel(key, horizontal=True):
    """Rótulos (str) selecionados em outro gráfico, lidos do estado do Streamlit (vale já na rodada do clique)."""
    if CLIQUE:
        return I.rotulos_clicados(st.session_state.get(key), horizontal)
    v = st.session_state.get(key + "_r")
    return set() if v in (None, "(nenhum)") else {str(v)}


def grafico(tabela, titulo, filtro, destino, key, empilhar=False, horizontal=True, cores=None):
    """Desenha barras. Ao clicar numa barra, os artigos correspondentes entram em `destino`."""
    if tabela.empty or float(tabela.values.sum()) == 0:
        st.caption(f"{titulo}: sem dados nesse filtro."); return
    multi = tabela.shape[1] > 1
    sel = []
    if CLIQUE:
        ev = st.plotly_chart(I.barras(tabela, titulo, horizontal, empilhar, cores), use_container_width=True,
                             on_select="rerun", selection_mode="points", key=key)
        sel = I.ler_clique(ev, tabela, horizontal)
    else:
        if TEM_PLOTLY: st.plotly_chart(I.barras(tabela, titulo, horizontal, empilhar, cores), use_container_width=True, key=key)
        else:
            st.markdown(f"**{titulo}**"); st.bar_chart(tabela)
        rot = st.selectbox("Ver artigos de:", ["(nenhum)"] + [str(i) for i in tabela.index], key=key + "_r")
        if rot != "(nenhum)":
            grp = st.selectbox("Grupo:", [str(c) for c in tabela.columns], key=key + "_g") if multi else str(tabela.columns[0])
            idx = [str(i) for i in tabela.index].index(rot); sel = [(tabela.index[idx], grp)]
    if destino is None:
        return sel
    for rot, grp in sel:
        sub = filtro(rot, grp)
        destino.append((f"{titulo} → {rot}" + (f" · {grp}" if multi else ""), sub))
    return sel


def mostrar_selecoes(destino, chave):
    st.divider(); st.subheader("Artigos selecionados")
    if not destino:
        st.caption("Clique em uma barra de qualquer gráfico desta aba para listar os artigos (Shift+clique seleciona várias). "
                   "Para desmarcar, clique de novo na mesma barra." if CLIQUE else "Escolha um item na lista abaixo de um gráfico.")
        return
    for i, (desc, sub) in enumerate(destino):
        st.markdown(f"**{desc}** — {len(sub)} artigo(s)")
        tabela_artigos(sub, f"{chave}_{i}")


def serie_df(s, nome):
    return s.to_frame(nome)


# ---------------- Indicadores ----------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Registros", len(f)); c2.metric("Duplicatas removidas", dup)
c3.metric("Núcleo setorial", int((f["Núcleo setorial"] == "Sim").sum()))
c4.metric("Casos concretos", int((f["Categoria"] == C.CATS[0]).sum()))
c5.metric("Open Access", "n/d" if "Open Access" in FALTANDO else f"{(f['Open Access (sim/não)'] == 'Sim').mean() * 100:.0f}%")
if not CLIQUE:
    st.warning("Clique nas barras indisponível: atualize com `pip install -U streamlit plotly`. Enquanto isso, use as listas abaixo dos gráficos.")

abas = st.tabs(["Visão geral", "Casos concretos", "Peças, materiais e tecnologias", "Países, instituições e autores",
                "Comparar buscas", "Tabela e downloads"])
CAT = f["Categoria"]; OA = f["Open Access (sim/não)"]; NUC = f["Núcleo setorial"] == "Sim"
VERDE, CINZA, AZUL, LARANJA = "#548235", "#A6A6A6", "#1F3864", "#ED7D31"

# ===== Visão geral =====
with abas[0]:
    dest = []
    a, b = st.columns(2)
    with a:
        t = CAT.value_counts().reindex(C.CATS).fillna(0).astype(int).to_frame("Registros")
        grafico(t, f"Relevância ({len(f)} registros)", lambda l, g: f[CAT == l], dest, "g_rel", cores=[AZUL])
    with b:
        t = pd.crosstab(CAT, OA).reindex(C.CATS).fillna(0).astype(int).rename(columns={"Sim": "Open Access", "Não": "Fechado"})
        for c in ("Open Access", "Fechado"):
            if c not in t: t[c] = 0
        grafico(t[["Open Access", "Fechado"]], "Open Access por categoria", lambda l, g: f[(CAT == l) & (OA == ("Sim" if g == "Open Access" else "Não"))],
                dest, "g_oa", empilhar=True, cores=[VERDE, CINZA])
    a, b = st.columns(2)
    with a:
        ano = pd.to_numeric(f["Year"], errors="coerce")
        g_ = pd.DataFrame({"a": ano, "g": NUC.map({True: "Núcleo setorial", False: "Demais"})}).dropna()
        t = pd.crosstab(g_["a"].astype(int), g_["g"])
        for c in ("Núcleo setorial", "Demais"):
            if c not in t: t[c] = 0
        grafico(t[["Núcleo setorial", "Demais"]], "Publicações por ano", lambda l, g: f[(ano == int(l)) & (NUC == (g == "Núcleo setorial"))],
                dest, "g_ano", empilhar=True, horizontal=False, cores=[AZUL, CINZA])
    with b:
        S = [s for s in C.SEGS if s != "Sem contexto setorial"]
        con = CAT == C.CATS[0]
        t = pd.DataFrame({"Casos concretos": f[con]["Segmento"].value_counts().reindex(S).fillna(0),
                          "Núcleo setorial": f[NUC]["Segmento"].value_counts().reindex(S).fillna(0)}).astype(int)
        grafico(t, "Segmento da cadeia", lambda l, g: f[(f["Segmento"] == l) & (con if g == "Casos concretos" else NUC)],
                dest, "g_seg", cores=[LARANJA, AZUL])
    mostrar_selecoes(dest, "vg")

# ===== Casos concretos =====
with abas[1]:
    dest = []
    cc = f[CAT == C.CATS[0]]
    if cc.empty:
        st.info("Sem casos concretos nesse filtro.")
    else:
        st.caption("Os gráficos 'Tipo de caso' e 'Peça/componente' se filtram entre si: ao selecionar um tipo, só aparecem as peças desse tipo "
                   "(e vice-versa). Confiança 'Média (revisar)': a regra achou uma peça, mas vale conferir o resumo.")
        PECA = cc["Peça/componente"].replace("", "(não identificada)")
        sel_tipo = rotulos_sel("g_tipo", True); sel_peca = rotulos_sel("g_peca", True)
        # tabela do gráfico de tipo respeita a peça selecionada; a de peça respeita o tipo selecionado
        base_tipo = cc[PECA.isin(sel_peca)] if sel_peca else cc
        base_peca = cc[cc["Tipo de caso"].isin(sel_tipo)] if sel_tipo else cc
        aviso_tipo = f"só peça {', '.join(sorted(sel_peca))}" if sel_peca else ""      # o gráfico de tipo está filtrado pela peça
        aviso_peca = f"só tipo {', '.join(sorted(sel_tipo))}" if sel_tipo else ""      # o gráfico de peça está filtrado pelo tipo
        sufixo = lambda av: f" — {av}" if av else ""
        a, b = st.columns(2)
        with a:
            if aviso_tipo: st.markdown(f":orange[**▶ Filtrado: {aviso_tipo}**] — clique de novo na barra selecionada para ver tudo.")
            t = base_tipo["Tipo de caso"].value_counts().reindex(C.TIPOS).fillna(0).astype(int).to_frame("Casos")
            grafico(t, f"Tipo de caso (n={len(base_tipo)})" + sufixo(aviso_tipo), None, None, "g_tipo", cores=[LARANJA])
        with b:
            t = pd.crosstab(cc["Segmento"], cc["Tipo de caso"]).reindex(columns=C.TIPOS, fill_value=0)
            grafico(t, "Segmento × tipo de caso", lambda l, g: cc[(cc["Segmento"] == l) & (cc["Tipo de caso"] == g)], dest, "g_segtipo", empilhar=True)
        pc = base_peca["Peça/componente"].replace("", "(não identificada)").value_counts().head(15)
        # mantém na lista as peças já selecionadas, mesmo que fora do top 15, para a seleção não "sumir"
        for p in sel_peca:
            if p not in pc.index: pc.loc[p] = int((PECA[base_peca.index] == p).sum())
        if aviso_peca: st.markdown(f":orange[**▶ Filtrado: {aviso_peca}**] — clique de novo na barra selecionada para ver tudo.")
        grafico(pc.to_frame("Casos"), f"Peça/componente (n={len(base_peca)})" + sufixo(aviso_peca), None, None, "g_peca", cores=[AZUL])
        # lista combinada: tipo(s) e/ou peça(s) selecionados
        if sel_tipo or sel_peca:
            sub = cc
            if sel_tipo: sub = sub[sub["Tipo de caso"].isin(sel_tipo)]
            if sel_peca: sub = sub[PECA[sub.index].isin(sel_peca)]
            desc = " + ".join(x for x in (("Tipo: " + ", ".join(sorted(sel_tipo))) if sel_tipo else "", ("Peça: " + ", ".join(sorted(sel_peca))) if sel_peca else "") if x)
            dest.insert(0, (desc, sub))
    mostrar_selecoes(dest, "cc")
    if not cc.empty:
        st.subheader("Todos os casos concretos"); tabela_artigos(cc, "cc_todos")

# ===== Peças, materiais, tecnologias =====
with abas[2]:
    dest = []
    SF = CAT == C.CATS[3]

    def bloco(pref, titulo, key):
        cols = [c for c in f.columns if c.startswith(pref + ": ")]
        a_ = f.loc[NUC, cols].sum(); b_ = a_ + f.loc[SF, cols].sum()
        t = pd.DataFrame({"Núcleo setorial": a_, "Núcleo + MA geral": b_}).astype(int); t.index = [c[3:] for c in t.index]
        t = t.sort_values("Núcleo + MA geral", ascending=False).head(15)
        if so_nucleo:                       # com "só núcleo setorial", a barra cinza (núcleo + MA geral) não faz sentido
            t = t[["Núcleo setorial"]]

        def filtro(l, g):
            base_ = NUC if g == "Núcleo setorial" else (NUC | SF)
            return f[(f[f"{pref}: {l}"] == 1) & base_]
        grafico(t, titulo, filtro, dest, key, cores=[AZUL] if so_nucleo else [AZUL, CINZA])

    a, b = st.columns(2)
    with a: bloco("P", "Peças/equipamentos mencionados", "g_P")
    with b: bloco("M", "Materiais mencionados", "g_M")
    a, b = st.columns(2)
    with a: bloco("T", "Tecnologias de MA mencionadas", "g_T")
    with b:
        t = f.loc[NUC, "Source title"].fillna("—").value_counts().head(12).to_frame("Registros")
        grafico(t, "Fontes mais frequentes (núcleo setorial)", lambda l, g: f[NUC & (f["Source title"].fillna("—") == l)], dest, "g_fonte", cores=[CINZA])
    mostrar_selecoes(dest, "pmt")

# ===== Países, instituições e autores =====
with abas[3]:
    if not (TEM_AFIL or TEM_AUT):
        st.info("Seus arquivos não têm as colunas de autoria. No Scopus, ao exportar, marque **Affiliations** (em *Bibliographical information*) e "
                "**Author(s)**; no Web of Science, use *Full Record*. Depois reenvie os arquivos.")
    else:
        dest = []
        escolha = st.radio("Base de contagem", ["Todos os registros filtrados", "Só núcleo setorial", "Só casos concretos"], horizontal=True)
        mb = {"Todos os registros filtrados": pd.Series(True, index=f.index), "Só núcleo setorial": NUC, "Só casos concretos": CAT == C.CATS[0]}[escolha]
        fb = f[mb]
        # o valor do filtro de país já está no estado do Streamlit no início da rodada (o campo é desenhado mais abaixo)
        sel_paises = [p for p in st.session_state.get("f_pais_tab", [])] if TEM_AFIL else []
        fp = autoria.com_paises(fb, sel_paises) if TEM_AFIL else fb
        st.caption(f"{len(fb)} registros nesta base" + (f"; {len(fp)} com {', '.join(sel_paises)}" if sel_paises else "")
                   + ". Cada artigo conta uma vez por país/instituição/autor.")
        if TEM_AFIL:
            m1, m2, m3 = st.columns(3)
            m1.metric("Países distintos", autoria.ranking(fb, "Países", 0).shape[0])
            m2.metric("Instituições distintas", autoria.ranking_instituicoes(fp, sel_paises, 0).shape[0])
            m3.metric("Colaboração internacional", f"{autoria.pct_colaboracao_internacional(fp):.0f}% dos artigos")
            a, b = st.columns(2)
            with a:
                r = autoria.ranking(fb, "Países", 15)
                grafico(r.to_frame("Artigos"), "Países (artigos)", lambda l, g: autoria.filtrar_item(fb, "Países", l), dest, "g_pais", cores=[AZUL])
            with b:
                top = list(autoria.ranking(fb, "Países", 12).index)
                rows = {p: autoria.filtrar_item(fb, "Países", p)["Categoria"].value_counts().reindex(C.CATS).fillna(0) for p in top}
                t = pd.DataFrame(rows).T.astype(int)
                grafico(t, "Países × categoria", lambda l, g: autoria.filtrar_item(fb, "Países", l).pipe(lambda x: x[x["Categoria"] == g]),
                        dest, "g_paiscat", empilhar=True)
            st.multiselect("Filtrar por país (digite para buscar) — atualiza os gráficos de instituições e autores abaixo",
                           list(autoria.ranking(d, "Países", 0).index), key="f_pais_tab")
        a, b = st.columns(2)
        sufixo = f" — {', '.join(sel_paises)}" if sel_paises else ""
        if TEM_AFIL:
            with a:
                r = autoria.ranking_instituicoes(fp, sel_paises, 15)
                grafico(r.to_frame("Artigos"), "Instituições (artigos)" + sufixo, lambda l, g: autoria.filtrar_item(fp, "Instituições", l),
                        dest, "g_inst", cores=[AZUL])
        if TEM_AUT:
            with (b if TEM_AFIL else a):
                r = autoria.ranking(fp, "Autores (lista)", 15)
                grafico(r.to_frame("Artigos"), "Autores (artigos)" + sufixo, lambda l, g: autoria.filtrar_item(fp, "Autores (lista)", l),
                        dest, "g_aut", cores=[AZUL])
        if sel_paises and TEM_AUT:
            st.caption("Autores: são os de todos os artigos que têm o(s) país(es) selecionado(s) — inclui coautores de outros países, "
                       "pois o export não liga cada autor ao seu país. Instituições: só as dos países selecionados.")
        if TEM_AFIL:
            st.subheader("Pares de países que mais colaboram" + (" (com o país selecionado)" if sel_paises else ""))
            tp, _ = st.columns([1, 2])
            tp.dataframe(autoria.pares_paises(fb, 15, incluir=sel_paises), hide_index=True, use_container_width=True,
                         column_config={"Par de países": st.column_config.TextColumn("Par de países", width="medium"),
                                        "Artigos": st.column_config.NumberColumn("Artigos", width="small")})
        mostrar_selecoes(dest, "pia")
        st.caption("Atenção: autores são contados pelo nome (homônimos e variações de grafia podem se misturar) e a instituição é "
                   "estimada pelo texto da afiliação. Use como indicação, não como contagem oficial.")

# ===== Comparar buscas =====
with abas[4]:
    dest = []
    if len(todas_buscas) < 2:
        st.info("Envie mais de um CSV (ou dê nomes diferentes) para comparar buscas.")
    else:
        x = f.assign(b=f["Busca"].str.split("; ")).explode("b").reset_index(drop=True)
        t = pd.crosstab(x["b"], x["Categoria"]).reindex(columns=C.CATS, fill_value=0)
        grafico(t, "Composição de cada busca", lambda l, g: f[f["Busca"].str.split("; ").map(lambda z: l in z) & (CAT == g)], dest, "g_busca", empilhar=True)
        st.dataframe(G.tabela_buscas(f), use_container_width=True)
        st.caption("'Exclusivos' = só apareceu nessa busca. '% fora do tema' alto indica string de busca com muito ruído.")
    mostrar_selecoes(dest, "cb")

# ===== Tabela e downloads =====
with abas[5]:
    tabela_artigos(f, "tabela")
    x1, x2, x3 = st.columns(3)
    x1.download_button("Baixar planilha Excel (registros filtrados)", gerar_xlsx(f), "analise_MA.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    x2.download_button("Baixar gráficos (ZIP de PNGs)", gerar_zip(f), "graficos.zip", "application/zip")
    x3.download_button("Baixar CSV classificado", f.drop(columns=[c for c in f.columns if c.startswith("_")]).to_csv(index=False).encode("utf-8-sig"), "classificado.csv", "text/csv")
