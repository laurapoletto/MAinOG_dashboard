"""Gráficos de barras clicáveis (Plotly) e leitura do clique."""
import plotly.graph_objects as go

AZUL, CINZA, LARANJA, VERDE, AZ2 = "#1F3864", "#A6A6A6", "#ED7D31", "#548235", "#8FAADC"
PALETA = [LARANJA, "#F4B183", AZUL, AZ2, "#BFBFBF", "#D9D9D9", "#EDEDED", VERDE]


def barras(tabela, titulo, horizontal=True, empilhar=False, cores=None):
    """tabela: DataFrame; índice = rótulos das barras, colunas = grupos (um traço por coluna)."""
    cores = cores or PALETA
    fig = go.Figure()
    rot = [str(i) for i in tabela.index]
    for k, g in enumerate(tabela.columns):
        v = [int(x) for x in tabela[g].values]
        kw = dict(x=v, y=rot) if horizontal else dict(x=rot, y=v)
        fig.add_trace(go.Bar(name=str(g), orientation="h" if horizontal else "v", marker_color=cores[k % len(cores)],
                             text=[x if x else "" for x in v], textposition="inside" if empilhar else "outside",
                             customdata=[[str(r), str(g)] for r in rot],
                             hovertemplate="%{customdata[0]}<br>" + str(g) + ": %{text}<extra></extra>", **kw))
    n = len(rot)
    altura = max(260, 34 * n * (1 if (empilhar or tabela.shape[1] == 1) else 1.6) + 110) if horizontal else 380
    fig.update_layout(title=dict(text=titulo, x=0), barmode="stack" if empilhar else "group", height=int(altura),
                      margin=dict(l=10, r=10, t=50, b=10), showlegend=tabela.shape[1] > 1, legend=dict(orientation="h", y=-0.12),
                      bargap=0.25, clickmode="event+select")
    if horizontal: fig.update_yaxes(autorange="reversed", title=None)
    else: fig.update_xaxes(type="category", title=None)
    return fig


def _pontos(evento):
    try:
        return list(evento["selection"]["points"])
    except Exception:
        return []


def _rotulo_ponto(p, horizontal):
    """Rótulo (texto) da barra clicada: eixo y nas barras horizontais, eixo x nas verticais."""
    r = p.get("y" if horizontal else "x")
    if r is None:
        cd = p.get("customdata")
        r = cd[0] if cd else None
    return None if r is None else str(r)


def rotulos_clicados(evento, horizontal=True):
    """Conjunto de rótulos (str) das barras clicadas, sem depender da tabela atual."""
    return {r for r in (_rotulo_ponto(p, horizontal) for p in _pontos(evento)) if r is not None}


def ler_clique(evento, tabela, horizontal=True):
    """Devolve [(rótulo, grupo), ...] das barras clicadas, com os tipos originais do índice/colunas da tabela.
    O rótulo vem do próprio ponto clicado (não da posição), então continua certo se a tabela mudou."""
    mapa = {str(i): i for i in tabela.index}
    saida = []
    for p in _pontos(evento):
        r = _rotulo_ponto(p, horizontal)
        c = p.get("curve_number", 0)
        try:
            grupo = tabela.columns[c]
        except Exception:
            grupo = tabela.columns[0]
        if r in mapa:
            saida.append((mapa[r], grupo))
        elif r is None:
            i = p.get("point_index", p.get("point_number"))
            if i is not None and 0 <= i < len(tabela.index): saida.append((tabela.index[i], grupo))
    return saida
