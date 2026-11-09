"""Gera a planilha Excel (com fórmulas no Resumo) a partir do DataFrame classificado."""
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
import classificador as C
import regras as R0
import graficos as G

A = Font(name="Arial", size=10); AB = Font(name="Arial", size=10, bold=True)
HF = Font(name="Arial", size=10, bold=True, color="FFFFFF"); HP = PatternFill("solid", fgColor="1F3864")
SUB = PatternFill("solid", fgColor="D9E2F3")

COLS = [("ID", None), ("Título", "Title"), ("Ano", "Year"), ("Tipo de documento", "Document Type"), ("Fonte", "Source title"),
        ("Citações", "Cited by"), ("DOI", "DOI"), ("Link", "Link"), ("Open Access", "Open Access (sim/não)"),
        ("Tipo de OA", "Open Access"), ("Buscas", "Busca"), ("Base", "Base"), ("Categoria", "Categoria"), ("Núcleo setorial", None),
        ("Tipo de caso", "Tipo de caso"), ("Peça/componente", "Peça/componente"), ("Segmento", "Segmento"),
        ("Confiança", "Confiança"), ("Score setorial", "Score setorial"), ("Palavras-chave do autor", "Author Keywords"), ("Resumo", "Abstract")]
WID = {"ID": 6, "Título": 60, "Ano": 6, "Tipo de documento": 14, "Fonte": 30, "Citações": 9, "DOI": 22, "Link": 18, "Open Access": 9,
       "Tipo de OA": 22, "Buscas": 22, "Base": 14, "Categoria": 32, "Núcleo setorial": 9, "Tipo de caso": 11, "Peça/componente": 30,
       "Segmento": 18, "Confiança": 14, "Score setorial": 9, "Palavras-chave do autor": 30, "Resumo": 50, "Países": 24, "Instituições": 40, "Autores": 40}


def exportar_xlsx(d):
    d = d.reset_index(drop=True)
    extras = [(h, s) for h, s in (("Países", "Países"), ("Instituições", "Instituições"), ("Autores", "Autores (lista)")) if s in d.columns]
    COLS_ = COLS + extras
    P, M, T = ([c for c in d.columns if c.startswith(p + ": ")] for p in "PMT")
    wb = Workbook(); ws = wb.active; ws.title = "Resumo"
    wd = wb.create_sheet("Dados"); wb_buscas = wb.create_sheet("Comparação de buscas")
    wc = wb.create_sheet("Casos concretos"); wn = wb.create_sheet("Notas")
    hdr = [c for c, _ in COLS_] + P + M + T
    col = {h: L(j) for j, h in enumerate(hdr, 1)}
    N = len(d) + 1
    for j, h in enumerate(hdr, 1):
        x = wd.cell(1, j, h); x.font = HF; x.fill = HP; x.alignment = Alignment(wrap_text=True, vertical="center")
    cat_col = col["Categoria"]; cats = C.CATS
    for i in range(len(d)):
        r = d.iloc[i]
        for j, (h, src) in enumerate(COLS_, 1):
            if h == "ID": v = i + 1
            elif h == "Núcleo setorial":
                v = f'=IF(OR({cat_col}{i+2}="{cats[0]}",{cat_col}{i+2}="{cats[1]}",{cat_col}{i+2}="{cats[2]}"),"Sim","Não")'
            else:
                v = r.get(src, "")
                if pd.isna(v): v = ""
                if isinstance(v, str) and len(v) > 32000: v = v[:32000]
            wd.cell(i + 2, j, v).font = A
        for k, h in enumerate(P + M + T, len(COLS_) + 1):
            wd.cell(i + 2, k, int(r[h])).font = A
    for j, h in enumerate(hdr, 1): wd.column_dimensions[L(j)].width = WID.get(h, 10)
    wd.row_dimensions[1].height = 42; wd.freeze_panes = "C2"; wd.auto_filter.ref = f"A1:{L(len(hdr))}{N}"

    # listas de apoio + validação de dados
    for i, s in enumerate(cats, 1): wn.cell(40 + i, 1, s)
    for i, s in enumerate(C.TIPOS, 1): wn.cell(60 + i, 1, s)
    for i, s in enumerate(C.SEGS, 1): wn.cell(70 + i, 1, s)
    for ref, h in ((f"=Notas!$A$41:$A${40+len(cats)}", "Categoria"), (f"=Notas!$A$61:$A${60+len(C.TIPOS)}", "Tipo de caso"), (f"=Notas!$A$71:$A${70+len(C.SEGS)}", "Segmento")):
        dv = DataValidation(type="list", formula1=ref, allow_blank=True); wd.add_data_validation(dv); dv.add(f"{col[h]}2:{col[h]}{N}")

    rng = lambda h: f"Dados!${col[h]}$2:${col[h]}${N}"
    CT, OA, NUC = rng("Categoria"), rng("Open Access"), rng("Núcleo setorial")
    ws["A1"] = "Análise bibliométrica – Manufatura aditiva"; ws["A1"].font = Font(name="Arial", size=14, bold=True)
    ws["A2"] = "Contagens = fórmulas ligadas à aba Dados. Corrija Categoria/Tipo/Segmento lá e tudo se atualiza."; ws["A2"].font = Font(name="Arial", size=9, italic=True)
    r = [4]

    def bloco(titulo, labels, fn):
        ws.cell(r[0], 1, titulo).font = AB
        for k, t in enumerate(["Qtd", "% do total", "Open Access"], 2): ws.cell(r[0], k, t).font = AB
        for k in range(1, 5): ws.cell(r[0], k).fill = SUB
        r[0] += 1; ini = r[0]
        for lab in labels:
            ws.cell(r[0], 1, lab).font = A
            q, oa = fn(r[0])
            ws.cell(r[0], 2, q).font = A; ws.cell(r[0], 4, oa).font = A; r[0] += 1
        fim = r[0] - 1
        ws.cell(r[0], 1, "Total").font = AB; ws.cell(r[0], 2, f"=SUM(B{ini}:B{fim})").font = AB; ws.cell(r[0], 4, f"=SUM(D{ini}:D{fim})").font = AB
        for k in range(ini, r[0] + 1):
            ws.cell(k, 3, f"=IF(B${r[0]}=0,0,B{k}/B${r[0]})").number_format = "0.0%"; ws.cell(k, 3).font = A
        r[0] += 2

    bloco("Relevância", cats, lambda rr: (f"=COUNTIF({CT},A{rr})", f'=COUNTIFS({CT},A{rr},{OA},"Sim")'))
    bloco("Casos concretos – tipo", C.TIPOS, lambda rr: (f'=COUNTIFS({CT},"{cats[0]}",{rng("Tipo de caso")},A{rr})', f'=COUNTIFS({CT},"{cats[0]}",{rng("Tipo de caso")},A{rr},{OA},"Sim")'))
    bloco("Casos concretos – segmento", C.SEGS, lambda rr: (f'=COUNTIFS({CT},"{cats[0]}",{rng("Segmento")},A{rr})', f'=COUNTIFS({CT},"{cats[0]}",{rng("Segmento")},A{rr},{OA},"Sim")'))
    bloco("Segmento – núcleo setorial", C.SEGS, lambda rr: (f'=COUNTIFS({NUC},"Sim",{rng("Segmento")},A{rr})', f'=COUNTIFS({NUC},"Sim",{rng("Segmento")},A{rr},{OA},"Sim")'))

    def fbloco(titulo, lst):
        ws.cell(r[0], 1, titulo).font = AB
        for k, t in enumerate(["Núcleo setorial", "Núcleo + MA geral", "Só casos concretos"], 2): ws.cell(r[0], k, t).font = AB
        for k in range(1, 5): ws.cell(r[0], k).fill = SUB
        r[0] += 1
        for h in lst:
            ws.cell(r[0], 1, h[3:]).font = A
            ws.cell(r[0], 2, f'=SUMIFS({rng(h)},{NUC},"Sim")').font = A
            ws.cell(r[0], 3, f'=SUMIFS({rng(h)},{NUC},"Sim")+SUMIFS({rng(h)},{CT},"{cats[3]}")').font = A
            ws.cell(r[0], 4, f'=SUMIFS({rng(h)},{CT},"{cats[0]}")').font = A; r[0] += 1
        r[0] += 1
    fbloco("Peças mencionadas", P); fbloco("Materiais mencionados", M); fbloco("Tecnologias mencionadas", T)
    ws.cell(r[0], 1, "Total de registros").font = AB; ws.cell(r[0], 2, f'=COUNTA({rng("ID")})')
    ws.cell(r[0] + 1, 1, "Open Access (total)").font = AB; ws.cell(r[0] + 1, 2, f'=COUNTIF({OA},"Sim")')
    ws.cell(r[0] + 1, 3, f"=B{r[0]+1}/B{r[0]}").number_format = "0.0%"
    ws.column_dimensions["A"].width = 48
    for k in "BCD": ws.column_dimensions[k].width = 18

    # Comparação de buscas (estática)
    tb = G.tabela_buscas(d).reset_index().rename(columns={"b": "Busca"})
    for j, h in enumerate(tb.columns, 1):
        x = wb_buscas.cell(1, j, h); x.font = HF; x.fill = HP
    for i, row in enumerate(tb.itertuples(index=False), 2):
        for j, v in enumerate(row, 1): wb_buscas.cell(i, j, v).font = A
    wb_buscas.column_dimensions["A"].width = 40
    for j in range(2, 9): wb_buscas.column_dimensions[L(j)].width = 16

    # Países / Instituições / Autores (estáticas)
    import autoria
    nuc_m = d["Núcleo setorial"].eq("Sim"); con_m = d["Categoria"].eq(cats[0])
    for nome, c_ in (("Países", "Países"), ("Instituições", "Instituições"), ("Autores", "Autores (lista)")):
        if c_ not in d.columns: continue
        w = wb.create_sheet(nome)
        tab = pd.DataFrame({nome: autoria.ranking(d, c_, 0).index, "Todos": autoria.ranking(d, c_, 0).values})
        tab["Núcleo setorial"] = tab[nome].map(autoria.ranking(d, c_, 0, nuc_m)).fillna(0).astype(int)
        tab["Casos concretos"] = tab[nome].map(autoria.ranking(d, c_, 0, con_m)).fillna(0).astype(int)
        tab = tab.head(200)
        for j, h in enumerate(tab.columns, 1):
            x = w.cell(1, j, h); x.font = HF; x.fill = HP
        for i, row in enumerate(tab.itertuples(index=False), 2):
            for j, v in enumerate(row, 1): w.cell(i, j, v).font = A
        w.column_dimensions["A"].width = 50
        for j in (2, 3, 4): w.column_dimensions[L(j)].width = 16
        w.freeze_panes = "A2"

    # Casos concretos (estática)
    cc = d[d["Categoria"] == cats[0]].sort_values(["Segmento", "Tipo de caso"])
    h2 = [("ID", None), ("Título", "Title"), ("Ano", "Year"), ("Tipo de caso", "Tipo de caso"), ("Peça/componente", "Peça/componente"),
          ("Segmento", "Segmento"), ("Confiança", "Confiança"), ("Open Access", "Open Access (sim/não)"), ("DOI", "DOI"), ("Link", "Link")]
    for j, (h, _) in enumerate(h2, 1):
        x = wc.cell(1, j, h); x.font = HF; x.fill = HP
    for i, (idx, row) in enumerate(cc.iterrows(), 2):
        for j, (h, s) in enumerate(h2, 1):
            v = idx + 1 if h == "ID" else row.get(s, "")
            wc.cell(i, j, "" if pd.isna(v) else v).font = A
    for j, w in enumerate([6, 70, 6, 11, 40, 18, 14, 9, 24, 24], 1): wc.column_dimensions[L(j)].width = w
    wc.freeze_panes = "A2"

    notas = ["Metodologia e ressalvas", "",
             "Classificação automática por regras de texto (título + resumo + palavras-chave). Sem IA. As regras ficam em regras.py.",
             "É uma triagem: espere erros. Revise principalmente os casos concretos com Confiança 'Média (revisar)'.",
             "Núcleo setorial = Caso concreto + Geral/revisão + Material/processo c/ foco setorial.",
             "Peças/materiais/tecnologias são MENÇÕES no texto, não necessariamente o objeto do estudo.",
             "Colunas editáveis na aba Dados: Categoria, Tipo de caso, Segmento (listas suspensas). A aba Resumo recalcula.",
             "Abas 'Casos concretos' e 'Comparação de buscas' são fotos estáticas do momento da exportação.", "",
             "Listas de apoio (não apagar):"]
    for i, t in enumerate(notas, 1): wn.cell(i, 1, t).font = AB if i == 1 else A
    wn.column_dimensions["A"].width = 120
    bio = io.BytesIO(); wb.save(bio); return bio.getvalue()
