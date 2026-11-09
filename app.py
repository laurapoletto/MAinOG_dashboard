"""Dashboard bibliométrico (Streamlit). Rodar:  streamlit run app.py"""
import inspect
import io

import pandas as pd
import streamlit as st
try:
    import streamlit.components.v1 as components
except ImportError:          # sem isso o app funciona, só não limpa a seleção ao clicar fora
    components = None

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
# st.fragment (Streamlit >= 1.37): cada aba recarrega sozinha ao clicar numa barra, sem refazer a página inteira
fragmento = getattr(st, "fragment", None) or (lambda fn: fn)
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


CTX = [None]              # aba em desenho
ATIVA = [False]           # a aba em desenho tem alguma barra selecionada?


def K(key):
    """Chave do widget com 'versão' por gráfico: aumentar a versão de UM gráfico limpa só a seleção dele."""
    return f"{key}__{st.session_state.get('_v', {}).get(key, 0)}"


def rotulos_sel(key, horizontal=True):
    """Rótulos (str) selecionados em outro gráfico, lidos do estado do Streamlit (vale já na rodada do clique)."""
    if CLIQUE:
        return I.rotulos_clicados(st.session_state.get(K(key)), horizontal)
    v = st.session_state.get(K(key) + "_r")
    return set() if v in (None, "(nenhum)") else {str(v)}


def iniciar_aba(nome):
    """Começo de cada aba: trata o botão escondido 'Limpar seleção' (acionado ao clicar fora)."""
    CTX[0] = nome; ATIVA[0] = False
    if st.button(f"Limpar seleção · {nome}", key=f"btn_limpar_{nome}"):
        v = st.session_state.setdefault("_v", {})
        for k in st.session_state.get("_charts", {}).get(nome, []):
            if CLIQUE and I.tem_selecao(st.session_state.get(K(k))):
                v[k] = v.get(k, 0) + 1                      # só os gráficos com seleção são recriados


JS_LIMPAR = """
<script>
(function () {
  const w = window.parent, pdoc = w.document;
  w.__selAtivas = w.__selAtivas || {};
  w.__selAtivas["__ID__"] = {ativo: __ATIVO__, label: "__LABEL__", id: "__ID__"};
  if (!w.__limparV3) {
    w.__limparV3 = true;
    pdoc.addEventListener('click', function (ev) {
      const t = ev.target;
      if (!t || !t.closest) return;
      // não limpa ao clicar em: botões, campos, links, abas, menus, barras/legenda/menu do gráfico, tabelas, barra lateral
      const protegido = 'button, a, input, select, textarea, label, summary, [role="tab"], [role="button"], [role="option"], ' +
        '[role="listbox"], [data-baseweb], .modebar, .legend, g.point, [data-testid="stDataFrame"], ' +
        '[data-testid="stSidebar"], [data-testid="stFileUploader"], iframe';
      if (t.closest(protegido)) return;
      Object.values(w.__selAtivas).forEach(function (s) {
        if (!s.ativo) return;
        const b = pdoc.querySelector('.st-key-btn_limpar_' + s.id + ' button') ||
          Array.from(pdoc.querySelectorAll('button')).find(x => (x.innerText || '').trim() === s.label);
        if (b) { s.ativo = false; b.click(); }
      });
    }, true);
  }
})();
</script>
"""


def fim_aba(nome):
    """Fim de cada aba: avisa o navegador se há seleção para limpar ao clicar fora."""
    if components is None or not CLIQUE: return
    try:
        components.html(JS_LIMPAR.replace("__ID__", nome).replace("__LABEL__", f"Limpar seleção · {nome}")
                        .replace("__ATIVO__", "true" if ATIVA[0] else "false"), height=0)
    except Exception:
        pass


def grafico(tabela, titulo, filtro, destino, key, empilhar=False, horizontal=True, cores=None):
    """Desenha barras. Ao clicar numa barra, os artigos correspondentes entram em `destino`."""
    if tabela.empty or float(tabela.values.sum()) == 0:
        st.caption(f"{titulo}: sem dados nesse filtro."); return
    multi = tabela.shape[1] > 1
    sel = []
    reg = st.session_state.setdefault("_charts", {}).setdefault(CTX[0], [])
    if key not in reg: reg.append(key)
    if CLIQUE:
        ev = st.plotly_chart(I.barras(tabela, titulo, horizontal, empilhar, cores), use_container_width=True,
                             on_select="rerun", selection_mode="points", key=K(key))
        sel = I.ler_clique(ev, tabela, horizontal)
        if sel: ATIVA[0] = True
    else:
        if TEM_PLOTLY: st.plotly_chart(I.barras(tabela, titulo, horizontal, empilhar, cores), use_container_width=True, key=K(key))
        else:
            st.markdown(f"**{titulo}**"); st.bar_chart(tabela)
        rot = st.selectbox("Ver artigos de:", ["(nenhum)"] + [str(i) for i in tabela.index], key=K(key) + "_r")
        if rot != "(nenhum)":
            grp = st.selectbox("Grupo:", [str(c) for c in tabela.columns], key=K(key) + "_g") if multi else str(tabela.columns[0])
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
                   "Clique fora das barras para limpar." if CLIQUE else "Escolha um item na lista abaixo de um gráfico.")
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

st.markdown("<style>[class*='st-key-btn_limpar']{display:none;}</style>", unsafe_allow_html=True)

abas = st.tabs(["Visão geral", "Casos concretos", "Peças, materiais e tecnologias", "Países, instituições e autores",
                "Comparar buscas", "Tabela e downloads"])
CAT = f["Categoria"]; OA = f["Open Access (sim/não)"]; NUC = f["Núcleo setorial"] == "Sim"
VERDE, CINZA, AZUL, LARANJA = "#548235", "#A6A6A6", "#1F3864", "#ED7D31"

# ===== Visão geral =====
@fragmento
def aba_vg():
    iniciar_aba("vg")
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
    fim_aba("vg")


with abas[0]:
    aba_vg()

# ===== Casos concretos =====
@fragmento
def aba_cc():
    iniciar_aba("cc")
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
        a, b = st.columns(2)
        with a:
            t = base_tipo["Tipo de caso"].value_counts().reindex(C.TIPOS).fillna(0).astype(int).to_frame("Casos")
            grafico(t, f"Tipo de caso (n={len(base_tipo)})", None, None, "g_tipo", cores=[LARANJA])
        with b:
            t = pd.crosstab(cc["Segmento"], cc["Tipo de caso"]).reindex(columns=C.TIPOS, fill_value=0)
            grafico(t, "Segmento × tipo de caso", lambda l, g: cc[(cc["Segmento"] == l) & (cc["Tipo de caso"] == g)], dest, "g_segtipo", empilhar=True)
        pc = base_peca["Peça/componente"].replace("", "(não identificada)").value_counts().head(15)
        # mantém na lista as peças já selecionadas, mesmo que fora do top 15, para a seleção não "sumir"
        for p in sel_peca:
            if p not in pc.index: pc.loc[p] = int((PECA[base_peca.index] == p).sum())
        grafico(pc.to_frame("Casos"), f"Peça/componente (n={len(base_peca)})", None, None, "g_peca", cores=[AZUL])
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
    fim_aba("cc")


with abas[1]:
    aba_cc()

# ===== Peças, materiais, tecnologias =====
@fragmento
def aba_pmt():
    iniciar_aba("pmt")
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
    fim_aba("pmt")


with abas[2]:
    aba_pmt()

# ===== Países, instituições e autores =====
@fragmento
def aba_pia():
    iniciar_aba("pia")
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
    fim_aba("pia")


with abas[3]:
    aba_pia()

# ===== Comparar buscas =====
@fragmento
def aba_cb():
    iniciar_aba("cb")
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
    fim_aba("cb")


with abas[4]:
    aba_cb()

# ===== Tabela e downloads =====
@fragmento
def aba_tab():
    iniciar_aba("tab")
    tabela_artigos(f, "tabela")
    # Excel, gráficos e CSV são gerados só quando você clica (gerar a cada clique em barra deixava tudo lento)
    sig = (len(f), int(pd.util.hash_pandas_object(f[["Title", "Categoria"]].fillna(""), index=False).sum()))
    if st.button("Preparar downloads (Excel, gráficos e CSV)", key="btn_prep"):
        with st.spinner("Gerando arquivos..."):
            st.session_state["_dl"] = {
                "sig": sig, "xlsx": exportador.exportar_xlsx(f), "zip": exportar_graficos.zip_graficos(f),
                "csv": f.drop(columns=[c for c in f.columns if c.startswith("_")]).to_csv(index=False).encode("utf-8-sig")}
    dl = st.session_state.get("_dl")
    if dl and dl["sig"] == sig:
        x1, x2, x3 = st.columns(3)
        x1.download_button("Baixar planilha Excel", dl["xlsx"], "analise_MA.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
        x2.download_button("Baixar gráficos (ZIP de PNGs)", dl["zip"], "graficos.zip", "application/zip", key="dl_zip")
        x3.download_button("Baixar CSV classificado", dl["csv"], "classificado.csv", "text/csv", key="dl_csv")
    elif dl:
        st.caption("Os filtros mudaram desde a última preparação: clique de novo em 'Preparar downloads'.")
    fim_aba("tab")


with abas[5]:
    aba_tab()

