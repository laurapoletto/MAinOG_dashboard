"""
Regras de classificação (editáveis).
Tudo aqui são expressões regulares (regex) aplicadas em minúsculas sobre título + resumo + palavras-chave.
Para adaptar a outro tema (ex.: MA na indústria nuclear), edite SETOR, SEGMENTOS e PARTES.
"""

# --- A pesquisa trata de manufatura aditiva? ---
AM = (r"additive manufactur|3d[- ]print|three-dimensional print|wire arc|waam|powder bed|directed energy|"
      r"laser cladding|laser metal deposition|cold spray|selective laser|fused (?:deposition|filament)|"
      r"stereolithograph|material extrusion|\bslm\b|\blpbf\b|\bded\b|laser engineered|binder jet|"
      r"rapid prototyping|additively manufactured|additive process")

# --- Contexto do setor-alvo (O&G / offshore / marítimo) ---
SETOR = (r"oil and gas|oil & gas|oil/gas|oil-and-gas|\bo&g\b|offshore|subsea|sub-sea|oilfield|oil field|oil industry|"
         r"downhole|wellbore|oil well|gas well|drilling|petroleum (?:industry|engineering|sector|equipment|field)|"
         r"refiner|petrochemical|gas pipeline|oil pipeline|wellhead|\blng\b|oil sands|upstream|midstream|downstream|"
         r"marine|maritime|\bships?\b|naval|shipbuilding|seawater|underwater|energy sector|energy industry")

# --- Fora do tema (bio, médico, alimentos, construção civil etc.) ---
BIO = (r"bio-?based|biodegrad|bioplastic|biopolymer|\bpla\b|polylact|lignin|cellulos|starch|food|packaging|"
       r"vegetable oil|soybean|seed oil|castor|tung oil|biomass|biocomposite|biomedical|medical|prosthe|tissue|drug|"
       r"mycelium|natural fib|hemp|itaconic|vitrimer|chitosan|protein|scaffold|renewable resource|hydrogel|"
       r"photopolymer|photocur|uv-curable|\bresin|acrylate|footwear|wound|aerogel|concrete|cement|geopolymer|mortar|asphalt")

# --- Periférico: MA só como ferramenta de laboratório / óleo-água / reservatório ---
PERIF = (r"rock|core plug|core flood|proppant|fractur(?:e|ing|es)\b|reservoir|microfluid|oil[- /]water|water.?flooding|"
         r"porous|permeab|petrophys|\bpore|sandstone|carbonate|vug|\beor\b|enhanced oil recovery|geomech|oil-in-water|"
         r"lost circulation|diverter|seepage|remaining oil|core holder|crude oil removal")

# --- Anais, capas, errata ---
SEM_CONTEUDO_TIPOS = ["Conference review", "Erratum", "Editorial", "Retracted", "Note"]
SEM_CONTEUDO_TITULO = (r"conference|symposium|proceedings|summit|exhibition|congress|workshop|^corrosion 20|"
                       r"international (?:exchange|workshop|scientific|symposium)")

# --- Revisão / artigo geral ---
REVISAO_TITULO = (r"review|state.of.the.art|overview|roadmap|perspective|challenges|opportunit|survey|bibliometric|"
                  r"systematic|outlook|trends|framework|prospects|status|future|introduction|potential of|"
                  r"digital inventory|digital warehous|supply chain")
REVISAO_RESUMO = r"this (?:paper|article|study|work|chapter) (?:reviews|discusses|presents an overview|summari[sz]es)|this review|we review|state-of-the-art review|literature review"

# --- Caso concreto: verbos de fabricação/projeto no resumo ---
FABRICACAO = (r"fabricat|manufactur(?:ed|ing of)|printed|produced|designed|developed|built|redesign|topology optimi|"
              r"case study|prototyp|tested|qualif|demonstrat|replac")

# --- Tipo de caso ---
REPARO = r"repair|refurbish|remanufactur|rework|life extension|life-extension|restor|overhaul"
REPOSICAO = r"spare part|replacement part|obsolesc|obsolete|legacy|on-demand|inventor|warehous|aftermarket|out-of-production|supply chain"
PROTOTIPO = r"prototyp|proof.of.concept|demonstrator|pilot|first.of.(?:its|a).kind|field (?:test|trial|deploy)|full-scale|mock-up|technology readiness"

# --- Peças / equipamentos (rótulo -> regex) ---
PARTES = {
    "Trocador de calor": r"heat exchanger|heat-exchanger|heat sink|recuperator|cooler|condenser",
    "Válvula": r"\bvalves?\b",
    "Bomba/impeller": r"\bpumps?\b|impeller",
    "Turbina/pá/propulsor": r"turbine|turbomachin|\bblades?\b|propeller|thruster",
    "Flange/duto/tê/riser": r"flange|\bpipes?\b|piping|pipeline|\btee\b|\briser|elbow|manifold",
    "Packer/bridge plug/completação": r"packer|bridge plug|completion",
    "Broca/PDC": r"drill bit|\bpdc\b|\bbits?\b",
    "Vedação/selo/o-ring": r"\bseals?\b|sealing|o-ring|gasket|backup ring",
    "Ferramenta downhole/MWD": r"downhole tool|logging tool|\bmwd\b|mud.pulse|wellbore|downhole",
    "Hidrociclone/filtro/separador": r"hydrocyclone|sand (?:filter|control|screen)|separator",
    "Mancal/engrenagem/eixo": r"bearing|\bgears?\b|\bshaft",
    "Molde/ferramental": r"\bmold|\bmould|tooling",
    "Bocal/injetor/queimador": r"nozzle|injector|burner|combustor",
    "Robô/veículo (ROV/AUV)": r"\brov\b|\bauv\b|robot|underwater vehicle|crawler",
    "Sensor/instrumento": r"\bsensors?\b|instrument",
    "Estrutura/componente estrutural": r"structural component|offshore structure|jacket|mooring|buoyancy",
}

# --- Materiais ---
MATERIAIS = {
    "Ligas de níquel": r"inconel|alloy 718|\b718\b|\b625\b|hastelloy|monel|nickel|superalloy|ni-based",
    "Aço inox": r"stainless|316l|duplex|17-4|\b2507\b",
    "Aço carbono/baixa liga/maraging": r"carbon steel|low.alloy|maraging|hsla|\bx80\b|high.strength steel|structural steel|mild steel|\ber70|\ber100|eh36|steel",
    "Titânio": r"titanium|ti-?6al|ti6al|\btc4\b",
    "Alumínio": r"alumin|alsi10mg|\b5356\b",
    "Cobre/bronze": r"copper|bronze|cu-?al",
    "Polímeros de engenharia": r"\bpeek\b|polyamide|\bpa12\b|polyethylene|polypropylene|\babs\b|polymer",
    "Compósitos/fibra": r"composite|carbon fib|glass fib",
    "Alta entropia": r"high.entropy",
    "Revestimento/cladding/WC": r"cladding|coating|tungsten carbide|\bwc\b",
    "Concreto/cimento": r"concrete|cement|mortar",
}

# --- Tecnologias de MA ---
TECNOLOGIAS = {
    "WAAM/arco": r"waam|wire.?arc|wire and arc|arc additive|arc-based|\bgmaw\b|\bgtaw\b|\bcmt\b|plasma arc|submerged arc|cold metal transfer|wire\s?\+\s?arc",
    "DED/LMD/laser cladding": r"directed energy|\bded\b|laser metal deposition|\blmd\b|laser cladding|\bdmd\b|laser engineered|\blens\b|laser-based direct",
    "LPBF/SLM/DMLS": r"powder bed|\bpbf\b|lpbf|l-pbf|selective laser melting|\bslm\b|\bdmls\b|laser sintering",
    "EBM": r"electron beam|\bebm\b",
    "Cold spray": r"cold spray|cold-spray|cold sprayed",
    "Extrusão polímero (FDM/FFF)": r"fdm|fff|fused deposition|fused filament|material extrusion|fused granular",
    "Fotopolimerização (SLA/DLP)": r"stereolithograph|\bsla\b|\bdlp\b|vat photopolym",
    "Binder jet/MJF/SLS": r"binder jet|multi.?jet|material jetting|\bsls\b",
    "Híbrida": r"hybrid (?:additive|manufactur)|additive.subtractive|hybrid directed",
}

# --- Segmento da cadeia (contagem de termos no texto) ---
SEGMENTOS = {
    "Upstream": r"upstream|drilling|downhole|wellbore|offshore|subsea|sub-sea|oilfield|oil field|wellhead|riser|oil well|gas well|exploration|production platform|deep.?water|mooring|completion",
    "Midstream": r"midstream|pipeline|\blng\b|gas transmission|storage tank|compressor station|oil transport",
    "Downstream": r"downstream|refiner|petrochemical|chemical plant|gas processing|\blng terminal|reactor",
}
MARITIMO = r"marine|maritime|\bships?\b|naval|shipboard|shipyard|seawater"
OG_GERAL = r"oil and gas|oil & gas|\bo&g\b|petroleum|hydrocarbon|oil industry"
