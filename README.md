# Dashboard bibliométrico – Aplicações de MA no setor O&G

Recebe CSVs do Scopus (de várias strings de busca), junta, remove duplicatas, classifica
e gera dashboard + planilha Excel + gráficos. Gratuito: sem IA, sem API, tudo roda no seu computador.

## Instalação (uma vez)
1. Instale o Python 3.10+ (python.org). No Windows, marque "Add Python to PATH".
2. Nesta pasta: Windows = duplo clique em `rodar.bat` | Linux/Mac = `bash rodar.sh`.
   (ou manualmente: `pip install -r requirements.txt` e `streamlit run app.py`)
3. O navegador abre em https://og-dashboard-lip.streamlit.app/

## Campos a marcar na exportação do Scopus
Em **Export → CSV**:
- **Citation information**: marque tudo (Author(s), Document title, Year, EID, Source title, Volume/issues/pages, Citation count, Source & document type, Publication stage, DOI, Open access).
- **Bibliographical information**: marque **Affiliations** (necessário para países e instituições).
- **Abstract & keywords**: marque **Abstract**, **Author keywords** e **Indexed keywords** (necessários para a classificação).
- Não precisa: Funding details, Other information, *Include references* (deixam o arquivo pesado). *Truncate to optimize for Excel* pode ficar ligado.
- Se o Scopus limitar o tamanho, exporte em partes (por ano, por exemplo) e envie todos os arquivos juntos: o app une e remove as duplicatas.
- Sem **Abstract**, a classificação fica muito pior (só pelo título). Sem **Affiliations**, a aba de países não funciona. O app avisa o que faltou.

## Web of Science
O WoS não exporta CSV. Em **Export**, escolha **Tab delimited file** (gera .txt; é o formato mais simples e não precisa de nada extra) ou **Excel**, com **Record Content: Full Record**. Envie no campo "Web of Science" da barra lateral.
- Aceita .txt (UTF-8 ou UTF-16), .xlsx e .xls (o .xls antigo precisa do pacote `xlrd`, já listado no requirements).
- O WoS costuma limitar cada exportação a cerca de 1.000 registros: exporte em partes e envie todos os arquivos.
- Pode misturar Scopus e WoS na mesma análise. Duplicatas (mesmo DOI ou mesmo título) viram um registro só, marcado com as duas bases.
- Diferenças: o WoS abrevia nomes de instituições ("Univ", "Inst"), então a mesma instituição pode aparecer duas vezes no ranking se você misturar bases. Os tipos de documento do WoS são convertidos para os equivalentes do Scopus.

## Como usar
1. No Scopus, exporte em CSV incluindo **Title, Year, Source title, Cited by, DOI, Link, Abstract, Author Keywords, Index Keywords, Document Type, Open Access**.
   (Se o limite de tamanho estourar, exporte em partes: o app une e remove duplicatas.)
2. Arraste um ou mais CSVs. Dê um nome para cada busca.
3. Use os filtros (ano, busca, categoria, segmento, OA, país) e as abas.
   **Clique em uma barra** de qualquer gráfico para listar abaixo os artigos daquela barra (Shift+clique seleciona várias; clique fora limpa). Cada seleção tem botão para baixar CSV.
   Requer Streamlit >= 1.35 e plotly; se o clique não estiver disponível, o app mostra uma lista de escolha embaixo de cada gráfico.
4. Em "Tabela e downloads": Excel, ZIP de gráficos e CSV classificado.

## Como a classificação funciona
Regras de texto (regex) sobre título + resumo + palavras-chave. Arquivo `regras.py`:
- **AM / SETOR / BIO / PERIF**: o que é manufatura aditiva, o contexto do setor, o que está fora do tema.
- **PARTES / MATERIAIS / TECNOLOGIAS / SEGMENTOS**: dicionários de termos (rótulo -> regex).
Para outro tema (ex.: nuclear, aeroespacial), edite `SETOR` e `SEGMENTOS` (ou use "Regras avançadas" na barra lateral).

## Limitações (importante)
- É **triagem automática**: nos testes com a base de 1.199 artigos, concordou ~66% com a classificação manual/semiautomática feita antes.
- A categoria mais difícil é **Caso concreto de peça**. Os marcados "Média (revisar)" precisam de conferência.
  A planilha tem listas suspensas para corrigir Categoria, Tipo de caso e Segmento, e o Resumo recalcula.
- Peças, materiais e tecnologias são **menções** no texto, não necessariamente o objeto do estudo.
- O tipo de caso (nova/protótipo/reposição/reparo) usa palavras-chave e tende a marcar "Nova" por padrão.

## Países, instituições e autores
Aba própria, com base de contagem à escolha (todos, só núcleo setorial ou só casos concretos): ranking de países, países × categoria, instituições, autores, % de colaboração internacional e pares de países que mais colaboram.
- Cada artigo conta uma vez por país/instituição/autor.
- A instituição é estimada pelo texto da afiliação (procura palavras como University, Institute, GmbH...). Variações de nome da mesma instituição podem aparecer separadas.
- Autores são contados pelo nome: homônimos se misturam e variações de grafia se separam (o Scopus tem o ID do autor, que poderia ser usado numa versão futura).

## Arquivos
app.py (interface) · classificador.py (lógica) · regras.py (dicionários editáveis) · dados.py (leitura, união, duplicatas)
autoria.py (países/instituições/autores) · interativo.py (gráficos clicáveis) · graficos.py · exportador.py (Excel) · exportar_graficos.py (ZIP)
