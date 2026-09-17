# Parâmetros de Cultivares — SeuGado

**REGRA INVIOLÁVEL DO PROJETO: nenhum número entra em código sem constar aqui, com fonte.**

Se uma spec precisa de um parâmetro ausente, marcar `TODO-PARAM: <nome>` e resolver
em chat `[PESQUISA]` antes de implementar. Valor plausível inventado é bug, não dado.

**Escopo desta regra.** Vale para número **empírico**: parâmetro agronômico, zootécnico e
constante de sensoriamento. Número que **nós escolhemos** — peso de função objetivo, limiar
de alerta, tolerância de teste — não é dado empírico: marcar `HIPOTESE-CALIBRAR` e nomear a
ADR que o calibrará (ex.: `07` §2, pesos `w1..w5`, antes do F-009).

**Escopo do bloqueio.** `TODO-PARAM` bloqueia **default de produção** e operação com a
cultivar afetada. Função pura que recebe o parâmetro como argumento pode ser implementada
e testada com valor neutro declarado.

Campo `confianca`:
- `alta` — fonte primária Embrapa/artigo revisado, valor consistente entre fontes
- `media` — fonte secundária confiável, ou divergência pequena entre fontes
- `baixa` — fonte única, ou extrapolado
- `ausente` — `TODO-PARAM`, bloqueia implementação

---

## Alturas de entrada e saída

### Fonte obtida — Régua de Manejo de Pastagens (Embrapa Gado de Corte)

> COSTA, J. A. A. da; QUEIROZ, H. P. de. **Régua de manejo de pastagens: edição revisada**.
> Campo Grande, MS: Embrapa Gado de Corte, 2017. (Embrapa Gado de Corte. Comunicado técnico, 135).
> 7 p. Acesso aberto — [registro no Infoteca-e](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/1077406) /
> [PDF](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1077406/1/Reguademanejodepastagens.pdf).
> A edição original é de 2013 e é o **Comunicado Técnico 125**; as tabelas abaixo vêm da
> **edição revisada de 2017, CT 135**, que é a que retirou os capins humidicola da régua.

✅ **Número da série resolvido (17/09/2026).** A dúvida 125 × 135 era real e tinha as duas
respostas certas: são duas edições. O registro do Infoteca-e da edição revisada
(`doc/1077406`, a que gerou estas tabelas) traz literalmente
*"(Embrapa Gado de Corte. Comunicado técnico, 135)"*, ano 2017. O CT 125 é a edição original
de 2013. A extração automatizada do rodapé estava correta; o que estava errado era presumir
uma edição só. Citar **CT 135 (2017)** para estes valores.

**Correção de premissa.** Ao abrir esta pesquisa, presumia-se que Zuri, Tamani e Cameroon
não fossem cobertos pelo documento. **Isso está parcialmente errado: Zuri e Tamani SÃO
cobertos** (Tabela 2 do documento, pastejo rotacionado). Só **Cameroon** fica de fora — é
capim-elefante (*Pennisetum purpureum*), gênero fora do escopo do documento, que trata
apenas de braquiárias e coloniões (panicuns). **B. humidicola também fica de fora**: a
edição revisada declara que os capins humidicola foram retirados da régua atual.

**Achado estrutural — leia antes de usar a tabela.** O documento usa duas grandezas, não
uma. Braquiárias (Xaraés, Piatã, Marandu, *B. decumbens*) são tratadas só sob **pastejo
contínuo**: altura **máxima/mínima** para decidir quando aumentar ou reduzir a lotação do
piquete — não é o mesmo conceito de "entrada/saída" de um giro rotacionado. Coloniões
(Mombaça, Zuri, Tanzânia, Quênia, Massai, Tamani) são tratados só sob **pastejo
rotacionado**: altura de **entrada e saída** por giro. Consequência prática: **o CT-135 não
resolve**, por si só, o `TODO-PARAM` de altura de entrada rotacional para Marandu/Xaraés — o
documento simplesmente não modela essas cultivares nesse regime.

✅ **Achado da pesquisa de regime na prática brasileira (17/09/2026 — `[PESQUISA] Regime de
pastejo na prática brasileira`, resolve P1 de `11`).** A régua do CT-135 documenta **uma**
grandeza por grupo de cultivar, mas isso é um limite do documento, não da prática: a
pesquisa localizou fontes técnicas mostrando braquiárias manejadas em **rotacionado**
(Marandu, Piatã) e panicuns manejados em **contínuo** (Tanzânia, Mombaça), cada grupo com
altura própria e divulgada. **A ambiguidade de regime por cultivar é a norma, não a
exceção** — nenhuma fonte consultada caracteriza o regime "fora" do CT-135 como raro,
proibido ou puramente experimental (a exceção parcial é a faixa de Marandu extraída de uma
dissertação de intensificação — ver nota abaixo). Consequência: **o `05` precisa de duas
faixas de altura por cultivar**, como a pergunta P1 antecipava — mas a cobertura de fonte é
desigual: Marandu, Piatã, Tanzânia e Mombaça ganharam a faixa que faltava nesta pesquisa;
Xaraés, *B. decumbens*, Massai, Zuri e Tamani continuam `TODO-PARAM` no regime que falta,
porque nenhuma fonte foi localizada para eles especificamente — regra 1 proíbe extrapolar de
uma cultivar próxima sem fonte própria.

✅ **Tensão de schema resolvida pela ADR-014 (17/09/2026).** O campo único `regime:` por
cultivar **acabou**. Cada cultivar carrega agora uma lista de blocos de altura, um por método
de pastejo em que ela tem fonte (`parametros_por_regime`), e a célula vazia é a **ausência do
bloco** — não um bloco cheio de `null`. Quem escolhe o bloco é o piquete, pelo seu
`metodo_pastejo`. Ver "Formato canônico no código", no fim deste arquivo, e a ADR-014 no `12`.

**O que o sistema faz na célula vazia (ADR-014).** Não inventa e não extrapola de cultivar
vizinha: o piquete fica `aguardando_parametro` — entra na projeção de estado, não entra em
prescrição — e o cadastro **pergunta ao produtor** a altura que ele usa, em cm. Essa resposta é
parâmetro **daquela fazenda**, gravada como evento com `origem: 'produtor'` e
`confianca: baixa`. **Ela nunca entra neste arquivo**: `05` só guarda valor com fonte pública
rastreável.

#### Tabela A — Pastejo rotacionado (coloniões / *Panicum* spp.)

| Cultivar | Entrada (cm) | Saída (cm) | Confiança | Notas |
|---|---|---|---|---|
| Mombaça | 85 | 45 | media | Diverge um pouco de fonte anterior (90/40) — ver nota abaixo |
| Zuri | 80 | 40 | alta | Entrada já registrada antes já batia com o CT-135; saída resolve TODO-PARAM |
| Tanzânia | 70 | 35 | media | Saída diverge um pouco de fonte anterior (30) — ver nota abaixo |
| Massai | 55 | 30 | alta | Resolve TODO-PARAM de saída |
| Tamani | 50 | 25 | alta | Resolve TODO-PARAM de saída |
| Quênia | 65 | 35 | alta | Fora do escopo atual do projeto (não é uma das 8 cultivares-alvo). Registrado porque veio de graça na mesma fonte — sem TODO-PARAM associado hoje |

#### Tabela A2 — Pastejo contínuo (coloniões / *Panicum* spp.) — achado novo (17/09/2026)

| Cultivar | Altura de manejo contínuo (cm) | Confiança | Notas |
|---|---|---|---|
| Tanzânia | 40–60 (carga variável) | media | Ver nota abaixo |
| Mombaça | 50–75 | media | Ver nota abaixo |
| Massai | TODO-PARAM | ausente | Nenhuma fonte de contínuo localizada nesta pesquisa |
| Zuri | TODO-PARAM | ausente | idem |
| Tamani | TODO-PARAM | ausente | idem |

#### Tabela B — Pastejo contínuo (braquiárias)

| Cultivar | Máxima (cm) | Mínima (cm) | Confiança | Notas |
|---|---|---|---|---|
| Xaraés | 40 | 20 | alta | Grandeza é contínua, não rotacional — não resolve `altura_entrada_cm` rotacional (TODO-PARAM mantido) |
| Piatã | 40 | 20 | alta | Cultivar nova nesta tabela |
| Marandu | 35 | 20 | alta | Grandeza é contínua — não resolve `altura_entrada_cm` rotacional isoladamente (ver Tabela B2). Prioridade do projeto (braquiária mais plantada do Brasil) |
| *B. decumbens* | 30 | 15 | alta | Cultivar nova nesta tabela |
| *B. humidicola* | TODO-PARAM | TODO-PARAM | ausente | **Não coberto pelo CT-135** — retirado da edição revisada. Segue sem fonte |
| Cameroon (capim-elefante) | 100 (entrada) | 45 (saída) | alta | **Não coberto pelo CT-135** (*Pennisetum*, fora de escopo do documento). Mantido o dado anterior — fonte experimental dedicada, melhor do que o CT-135 traria de qualquer forma |

#### Tabela B2 — Pastejo rotacionado (braquiárias) — achado novo (17/09/2026), confiança média/baixa

| Cultivar | Entrada (cm) | Saída (cm) | Confiança | Notas |
|---|---|---|---|---|
| Marandu | 19–30 (sem valor único; ver nota) | 15 | media | Três fontes convergem numa faixa, mas nenhuma é régua oficial tipo CT-135 |
| Piatã | ≈33 (pleno sol) | TODO-PARAM | baixa | Estudo em sistema de integração lavoura-pecuária-floresta (ILPF), não pasto aberto puro. Sem dado de saída |
| Xaraés | TODO-PARAM | TODO-PARAM | ausente | Nenhuma fonte localizada nesta pesquisa |
| *B. decumbens* | TODO-PARAM | TODO-PARAM | ausente | Nenhuma fonte localizada nesta pesquisa |

### Notas por cultivar

**Mombaça.** CT-135: entrada 85 cm, saída 45 cm. Fonte anterior (podcast Embrapa "Primeiro
Pastejo") registrava ~90 cm para 90% de IL e 115 cm para 100% IL; saída aparecia como 30, 40
e 50 cm em fontes experimentais diferentes (resíduos testados). **Registrando a faixa, sem
escolher calado:** entrada 85–90 cm, saída 30–50 cm. Default recomendado: usar o valor do
CT-135 (85/45) por ser fonte institucional específica para esta decisão, mantendo a faixa
como `altura_entrada_faixa`/`altura_saida_faixa` configurável.

**Mombaça (contínuo, achado novo).** KILL-SILVEIRA, R. **Manejo ecofisiológico das gramíneas
Megathyrsus maximus (Panicum maximum) cv. Tanzânia, Mombaça e Massai**. Revista de
Veterinária e Zootecnia, v. 27, 2020. DOI: [10.35172/rvz.2020.v27.421](https://doi.org/10.35172/rvz.2020.v27.421).
Cita: "para lotação contínua a altura ideal é de 50 a 75 cm" (Mombaça) e, para rotacionado,
"entrada dos animais deve ocorrer com altura aproximada de 80 cm e saída de 40 cm" — este
último número é compatível com o CT-135 (85/45), divergência pequena, mesma ordem de
grandeza. Reforça confiança média em ambas as tabelas.

**Tanzânia.** CT-135: entrada 70 cm, saída 35 cm. Fonte anterior já convergia em 70 cm de
entrada; saída divergia (30 cm). Estudo de resíduos testou 30 e 50 cm, com resíduo de 50 cm
gerando IL pós-pastejo de 67% (vs. 40% com 30 cm) e mais ciclos de pastejo por período. →
Faixa de saída: 30–50 cm, default CT-135 (35).

**Tanzânia (contínuo, achado novo).** Duas fontes concordam que a cultivar roda em contínuo
na prática, não só em rotacionado:
- Embrapa Gado de Corte, Comunicado Técnico 113, **"Panicum maximum cvs. Tanzânia e Mombaça
  para uso em pastejo: produção e custo"**
  ([PDF](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1063665/1/CT113Panicummaximum.pdf)):
  "Elevada flexibilidade para o manejo, suportando tanto o pastejo contínuo, quanto o
  rotacionado... Para lotação contínua deve-se procurar manter a vegetação com 50 cm de
  altura."
- Kill-Silveira (2020), citada acima: "para Megathyrsus maximus cv Tanzânia sob regime de
  lotação contínua e carga animal variável, recomenda-se a altura de pastejo entre 40 e 60
  cm" e, para rotacionado, "entrada com ±65 cm de dossel" (compatível com a faixa 70 cm do
  CT-135).
Ambas as fontes recomendam o rotacionado para sistemas intensivos (leite), mas nenhuma
desaconselha o contínuo — é opção documentada, com altura própria, não workaround sem
lastro.

**Massai / Zuri / Tamani.** Entrada já registrada antes batia exatamente com o CT-135 nos
três casos — bom sinal de que a fonte anterior (não documentada por nome) já vinha desta
mesma régua. Saída estava `TODO-PARAM` nos três; resolvida agora pelo CT-135 (30/40/25 cm
respectivamente). Regime contínuo dessas três: nenhuma fonte localizada nesta pesquisa —
`TODO-PARAM` mantido em Tabela A2, sem extrapolar de Tanzânia/Mombaça sem fonte própria.

**Xaraés / Marandu (contínuo).** CT-135 dá faixa 20–40 cm (Xaraés) e 20–35 cm (Marandu) para
pastejo **contínuo** — ajuste de lotação, não giro de piquete. O dado antigo de "saída
10–15 cm" para Marandu e "saída 15 cm" para Xaraés era para **rotacionado** e agora tem
lastro parcial (ver nota de Marandu rotacionado, abaixo) — o valor de saída bate com uma das
fontes novas (15 cm). Marandu segue prioritário; Xaraés segue `TODO-PARAM` para entrada
rotacional — ver Tabela B2.

**Marandu (rotacionado, achado novo — resolve parte de P1 de `11`).** Três fontes
independentes, nenhuma oficial-padrão tipo CT-135, convergindo numa faixa e não num valor
único:
- ANDRADE, C. M. S. **Pastejo Rotacionado: Tecnologia para Aumentar a Produtividade de Leite
  e a Longevidade das Pastagens**. Embrapa Acre, dez. 2008. Citado como: entrada 30 cm,
  saída 15 cm. **Fonte consultada indiretamente** — via citação em SOARES, M. G. et al.
  *Rotated grazing in Brachiaria brizantha cv. marandu to improve milk production*. Revista
  Científica Multidisciplinar Núcleo do Conhecimento, v. 7, n. 9, p. 104-118, set. 2021.
  DOI: 10.32749/nucleodoconhecimento.com.br. O documento primário da Embrapa Acre não foi
  localizado nesta pesquisa para verificação direta — por isso confiança **média**, não
  alta, apesar de ser instituição de peso.
- GOMES, C. M. (dissertação/tese, ESALQ/USP, orientação Prof. Dr. Sila Carneiro da Silva,
  2017–2018 — ver também *"Grazing management of Marandu palm grass: an opportunity for
  sustainable intensification?"*, teses.usp.br, tde-11092023-090137). Estudou alturas
  pré-pastejo de 25, 22, 19 e 16 cm e concluiu que é "possível flexibilizar as metas
  pré-pastejo do capim-marandu em sistemas rotativos com alturas de entrada variando de 19 a
  25 cm desde que a severidade de desfolhação seja moderada". É pesquisa de fronteira sobre
  intensificação, não levantamento de prática consolidada — não usar como default de
  "prática comum", mas como limite inferior plausível.
- Achado qualitativo (não numérico): nenhuma das fontes trata braquiária em rotacionado como
  incomum ou não recomendada — Andrade (2008) a apresenta como "tecnologia para aumentar
  produtividade", contrariando a suposição inicial de que braquiária ficaria restrita ao
  contínuo.
**Registro sem escolher calado:** faixa de entrada 19–30 cm, saída 15 cm (única fonte com
saída). `TODO-PARAM` tecnicamente resolvido por ter fonte, mas com confiança **média** e sem
valor único — a ADR-014 ou uma pesquisa futura dedicada pode reduzir a faixa.

**Piatã (rotacionado, achado novo).** CRESTANI, S.; GEREMIA, E. V.; MASCHERONI, J. D. C.;
CARNEVALLI, R. A.; SILVA, S. C. da. **Uso do critério de interceptação de luz para o manejo
do pastejo em área de integração lavoura-pecuária-floresta**. Cap. 26.
([PDF, Embrapa/Alice, doc/1118981](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1118981/1/Uso-do-criterio-de-interceptacao-de-luz-para-o-manejo-do-pastejo.pdf)).
Altura pré-pastejo a 95% de interceptação luminosa em pleno sol (sem sombreamento): **32,9
cm**. Sombreamento intermediário: 34,5 cm; sombreamento intenso: 50,5 cm (não usar estes
dois — contexto é ILPF, luz é a variável manipulada, não representa pasto aberto). Sem dado
de saída nesta fonte. Confiança **baixa**: é um único estudo, autores de peso (grupo Sila
Carneiro da Silva, ESALQ/USP — mesma linha de pesquisa que valida o critério de 95% IL
usado no restante do `05`), mas contexto experimental é ILPF, não pasto aberto puro.

**Cameroon.** Entrada a 100 cm (95% IL) superou 130 cm (100% IL): **−16%** leite/vaca/dia,
**−34%** leite/ha, **+911 kg/ha** de forragem perdida. Descanso fixo recomendado: **27 dias**.
Fora do escopo do CT-135 (gênero *Pennisetum*). Melhor evidência quantitativa disponível
entre todas as cultivares — usar como caso de validação do motor.

---

## Parâmetros ausentes — bloqueiam implementação

| Parâmetro | Onde é usado | Prioridade | Notas |
|---|---|---|---|
| `densidade_kg_ha_por_cm` (todas cultivares) | ponte massa↔altura | 🔴 crítica | Ver §"Como obter", abaixo |
| `rue_max_g_por_mj` para C4 tropical | eq. 11 do SAFER | 🔴 crítica | Paper usa 2,45 g/MJ **para C3**. C4 é maior |
| `temperatura_base_c` | graus-dia | 🟠 alta | Gramíneas tropicais param abaixo de ~15 °C |
| `altura_entrada_cm` rotacional — Xaraés, *B. decumbens* | regra de entrada | 🟠 alta | `[PESQUISA] Regime de pastejo` (17/09/2026) não encontrou fonte para estas duas — Marandu e Piatã já têm faixa (confiança média/baixa), ver Tabela B2. **Não bloqueia o produto desde a ADR-014**: piquete nessa combinação fica `aguardando_parametro` e o produtor informa a altura dele, com confiança baixa |
| `altura_maxima/minima_cm` contínuo — *B. humidicola* | regra de contínuo | 🟡 média | CT-135 não cobre; cultivar retirada da edição revisada. Buscar fonte alternativa se a cultivar entrar em produção |
| altura contínua — Massai, Zuri, Tamani | regra de contínuo | 🟡 média | `[PESQUISA] Regime de pastejo` (17/09/2026) resolveu Tanzânia e Mombaça (Tabela A2); estas três seguem sem fonte. Mesmo tratamento: `aguardando_parametro` + pergunta ao produtor (ADR-014) |
| `descanso_min/max_dias` por cultivar | limites de segurança | 🟡 média | Faixa geral 21–45 conhecida |
| `taxa_senescencia` | balanço de massa | 🟡 média | Aproximação declarada aceita no MVP |
| `eficiencia_pastejo` (ingestão ÷ massa acima do resíduo) | dias de ocupação | 🔴 crítica | ADR-010. A faixa 0,40–0,50 mede taxa de utilização |

### Como obter `densidade_kg_ha_por_cm` sem ir a campo

Buscar trabalhos que reportem **simultaneamente altura e massa de forragem** da mesma
cultivar. Teses de zootecnia fazem isso rotineiramente (amostram massa, composição
morfológica e altura no pré e pós-pastejo). Cada par (altura, massa) é um ponto de regressão.
15–20 pontos por cultivar dão curva utilizável.

⚠️ A relação não é perfeitamente linear — a densidade aumenta com a altura (o dossel adensa
na base). MVP: linear com intercepto. Se o erro for alto, evoluir para curva.

**Ponto de partida conhecido:** exemplo de fazenda comercial com massa pré-pastejo de
**4.000 kg MS/ha** e pós-pastejo de **2.240 kg MS/ha**. Se a cultivar e as alturas desse
caso forem identificadas, já são dois pontos reais.

---

## Parâmetros zootécnicos (independentes de cultivar)

| Parâmetro | Valor | Confiança | Fonte |
|---|---|---|---|
| `unidade_animal_kg` | 450 | alta | Padrão consolidado. Algumas fontes usam 454 |
| `consumo_pct_pv_min` | 2,0 % | alta | Faixa clássica |
| `consumo_pct_pv_max` | 3,0 % | alta | Faixa clássica |
| `consumo_pct_pv_default` | 2,4 % | média | Exemplo real: 11,62 kg MS/dia ÷ 479 kg = 2,42% |
| `taxa_utilizacao_min` | 0,40 | alta | Faixa real em fazenda (grandeza descritiva) |
| `taxa_utilizacao_max` | 0,50 | alta | Faixa real em fazenda (grandeza descritiva) |
| `taxa_utilizacao_caso_canonico` | 0,44 | alta | 1.760 ÷ 4.000 |
| `eficiencia_pastejo` | `TODO-PARAM` | ausente | Base distinta — ver ADR-010. Não usar 0,44 |
| `ocupacao_min_dias` | 1 | alta | Faixa usual rotacionado |
| `ocupacao_max_dias` | 3 | média | Faixa usual; casos reais usam até 4 |
| `descanso_min_dias` (geral) | 21 | alta | Faixa geral da literatura |
| `descanso_max_dias` (geral) | 45 | alta | Faixa geral da literatura |

### Tabela de Unidade Animal (UA) por categoria — achado novo (17/09/2026, resolve P3 de `11`)

> EMBRAPA GADO DE CORTE. **Como faço para calcular quantos UA's/ha? Ou lotação animal?**
> Perguntas Frequentes (SAC), 14/09/2012.
> [Link](https://cloud.cnpgc.embrapa.br/sac/2012/09/14/como-faco-para-calcular-quantos-ua%c2%b4sha-ou-lotacao-animal/).
> Base: 1 UA = 1 vaca seca de 450 kg de peso vivo.

| Categoria | Coeficiente (UA) | Confiança | Notas |
|---|---|---|---|
| Bezerro (0–1 ano) | 0,25 | media | FAQ institucional Embrapa Gado de Corte, sem citar paper de origem — por isso confiança média, não alta |
| Novilho (1–2 anos) | 0,50 | media | idem |
| Novilho (2–3 anos) | 0,75 | media | idem |
| Vaca / boi adulto | 1,00 | alta | Definição-base da própria UA |
| Touro | 1,25 | media | idem |

**Consistência cruzada.** Outra resposta do mesmo canal (Embrapa CNPGC SAC, 19/07/2012, "Como
é feita a conversão de cabeças de gado em Unidades Animal (UA)?") dá exemplos equivalentes a
uma conversão puramente linear por peso — "3 bezerros de 150 kg cada" = 1 UA (150×3=450) e
"2 novilhos de 225 kg cada" = 1 UA (225×2=450) — batendo com `UA = peso_vivo_kg ÷ 450`. A
tabela por categoria etária acima é uma simplificação de campo dessa mesma base; as duas
fontes não se contradizem, mas também não são a mesma coisa: a tabela por categoria assume um
peso médio típico por faixa etária, enquanto a fórmula linear usa o peso real do animal. Isto
✅ **Decidido pela ADR-014:** `peso_medio_kg` é a fonte canônica do consumo (`03` §6.1) e a
tabela por categoria é o **preenchimento** de quando o produtor não sabe o peso —
`peso_medio_kg = coeficiente_UA × 450`, gravado com `origem: 'ua_tabela'` e
`confianca: media`. A fórmula linear por peso real é o caso normal, não um refinamento
opcional: ela é simplesmente o `peso_medio_kg` informado.

**Uso, fixado pela ADR-014.** Dois papéis, e um não-papel:
1. **Preenchimento** do `peso_medio_kg` ausente (ver acima). Não é fórmula paralela de consumo.
2. **Escala de ordem das categorias**, que define compatibilidade de fusão — DT11 fechada:
   `compativel[a,b] = 1 ⟺ |ordem(a) − ordem(b)| ≤ 1`. Ver `07` §2 R10 e `03` §9.4. O limiar
   `≤ 1` é `HIPOTESE-CALIBRAR` (ADR de fusão de lotes, antes do F-022).
3. **Não** substitui a cadeia do `03` §6.1. Consumo continua sendo
   Σ(`n_animais` × `peso_medio_kg` × `pct_consumo`).

⚠️ **Direção do erro, registrada na ADR-014.** Bezerro por esta tabela dá 0,25 × 450 =
**112,5 kg**, abaixo do peso de desmama registrado adiante (180–210 kg, confiança baixa).
Subestimar peso subestima consumo e **superestima** dias de ocupação — erro na direção do
super-pastejo, que é o caro (`07` §2, `w4=5,0`). Daí a confiança média obrigatória no valor
derivado.

### Pesos médios por categoria — TODO-PARAM (parcialmente informado por achado novo)

| Categoria | Peso médio (kg) | Consumo (% PV) | Confiança |
|---|---|---|---|
| bezerro | TODO-PARAM (ver nota) | TODO-PARAM | ausente |
| novilho | ~300 | 2,2 % | média |
| adulto | ~450–480 | 2,4 % | média |

Referências ancoradas: recria de **300 kg a 2,2%** → 6,6 kg MS/dia.
Machos inteiros de **479 kg** consumindo **11,62 kg MS/dia** (2,42% PV).

**Status na ADR-014: B5 rebaixado de bloqueio a refinamento.** O `peso_medio_kg` faltante é
preenchido pela tabela de UA acima, com confiança média — F-002 não fica mais parado por este
número. Buscar o peso médio real por categoria continua valendo, como precisão, não como
fundação.

**Achado novo, não substitui o TODO-PARAM.** iRancho, *"Desmama de bezerros de corte: idade,
peso ideal e estratégias de manejo"* (blog, 2026): peso de desmama tipicamente entre **180 e
210 kg**, aos **6–8 meses**. É um bom número para o peso **na desmama**, mas não para o "peso
médio de bezerro" ao longo de toda a fase de cria (que vai de ~30–35 kg ao nascer até esse
valor) — a média da fase inteira seria mais baixa e depende da distribuição etária do lote.
Fonte é blog comercial (iRancho, ERP concorrente citado na ADR-001/ADR-004), não
institucional — confiança **baixa** mesmo para o número de desmama isolado. `TODO-PARAM`
mantido para "peso médio"; o número de desmama fica registrado como candidato caso a
arquitetura decida modelar por evento (nascimento → desmama → recria) em vez de por média.

---

## Constantes do SAFER (fixas, não configuráveis)

| Símbolo | Valor | Equação |
|---|---|---|
| `a`, `b`, `c` (albedo) | 0,08 / 0,41 / 0,14 | 2 |
| `a_A`, `b_A` (emiss. atm.) | 0,94 / 0,11 | 4 |
| `a₀`, `b₀` (emiss. sup.) | 0,06 / 1,00 | 5 |
| `σ` (Stefan-Boltzmann) | 5,67×10⁻⁸ W m⁻² K⁻⁴ | 6 |
| `a_sf`, `b_sf` (ETf) | 1,80 / −0,008 | 7 |
| `a_R` (RFA) | 0,44 | 8 |
| `a_F`, `b_F` (fRFA) | 1,257 / −0,161 | 9 |
| fator de conversão | 0,864 | 11 |
| `ET₀` de referência (denominador) | 5 mm/dia | 7 |

---

## Faixas de sanidade (validação de implementação)

| Grandeza | Faixa aceitável | Ação se fora |
|---|---|---|
| NDVI | −1 a 1; pasto vivo: 0,2 a 0,9 | Investigar máscara de nuvem |
| ETf | 0,05 a 1,3 | Falhar alto e logar |
| BIO | 0 a 150 kg/ha/dia | Falhar alto e logar |
| Massa de forragem | 500 a 12.000 kg MS/ha | Alerta, não falha |
| Consumo individual | 1 a 20 kg MS/animal/dia | Falhar alto |

Referências de BIO anual por bioma: Caatinga 15,0 · Cerrado 26,5 · Pantanal 28,9 ·
Amazônia 32,6 · Mata Atlântica 38,2 · Pampa 39,2 (t/ha/ano).
ETf observado: 0,14 (Caatinga seca) a 1,15 (Pampa úmido).

---

## Caso de regressão canônico

Este caso **deve** ser reproduzido pelo motor de cálculo. Se não reproduzir, há bug.

```yaml
entrada:
  area_total_ha: 46.5
  n_piquetes: 8
  area_piquete_ha: 5.81
  massa_pre_pastejo_kg_ms_ha: 4000
  massa_pos_pastejo_kg_ms_ha: 2240
  n_animais: 220
  peso_medio_kg: 479
  dias_ocupacao: 4
  dias_descanso: 28
  eficiencia_pastejo: 1.0                 # neutralizado: a fonte relata desaparecimento
                                          # como ingestão (ADR-010)
  taxa_acumulo_kg_ms_ha_dia: 0.0          # neutralizado: caso sem crescimento

saida_esperada:
  consumo_total_kg_ms_ha: 1760
  consumo_individual_kg_ms_dia: 11.62   # tolerância ±0.05
  consumo_pct_pv: 2.42                  # tolerância ±0.02
  taxa_utilizacao: 0.44                 # tolerância ±0.01
```

---

## Formato canônico no código

**Schema da ADR-014 (17/09/2026).** O campo `regime:` único acabou. Cada cultivar carrega um
bloco de altura **por método de pastejo em que tem fonte**. A célula vazia é a **ausência do
bloco**, não um bloco cheio de `null` — é assim que a matriz esparsa cultivar × regime se
representa sem inventar valor.

```yaml
mombaca:
  nome_exibicao: "Mombaça"
  especie: "Panicum maximum"
  via_fotossintetica: C4
  por_regime:
    - metodo: rotacionado
      altura_entrada_cm: 85
      altura_entrada_faixa: [85, 90]
      altura_saida_cm: 45
      altura_saida_faixa: [30, 50]
      confianca: media
      fonte: "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"
    - metodo: continuo
      altura_maxima_cm: 75
      altura_minima_cm: 50
      confianca: media
      fonte: "Kill-Silveira (2020), Rev. Vet. Zootec. 27, DOI 10.35172/rvz.2020.v27.421"
  densidade_kg_ha_por_cm: null      # TODO-PARAM — não é por regime
  rue_max_g_por_mj: null            # TODO-PARAM (C4) — não é por regime
  temperatura_base_c: null          # TODO-PARAM — não é por regime
  descanso_min_dias: 21
  descanso_max_dias: 45
  qualidade_base: alta
  observacoes: >
    Fonte anterior (podcast Embrapa "Primeiro Pastejo") registrava ~90cm (90% IL) e
    115cm (100% IL) para entrada; saída documentada em 30/40/50cm em estudos de resíduo.
    Faixa mantida como configurável; default é o valor institucional do CT-135.

marandu:
  nome_exibicao: "Marandu"
  especie: "Brachiaria brizantha"
  via_fotossintetica: C4
  por_regime:
    - metodo: continuo
      altura_maxima_cm: 35
      altura_minima_cm: 20
      confianca: alta
      fonte: "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"
    - metodo: rotacionado
      altura_entrada_cm: null         # sem valor único
      altura_entrada_faixa: [19, 30]
      altura_saida_cm: 15
      confianca: media
      fonte: >
        Andrade (2008, Embrapa Acre, via citação secundária em Soares et al. 2021);
        Gomes (ESALQ/USP, orient. Sila C. da Silva) — ver Tabela B2
  densidade_kg_ha_por_cm: null       # TODO-PARAM
  rue_max_g_por_mj: null             # TODO-PARAM (C4)
  temperatura_base_c: null           # TODO-PARAM
  descanso_min_dias: 21
  descanso_max_dias: 45
  qualidade_base: alta
  observacoes: >
    Prioridade do projeto — braquiária mais plantada do Brasil. O CT-135 só a documenta em
    pastejo contínuo; o bloco rotacionado vem de três fontes convergentes numa faixa,
    nenhuma delas régua oficial equivalente ao CT-135.

xaraes:
  nome_exibicao: "Xaraés"
  especie: "Brachiaria brizantha"
  via_fotossintetica: C4
  por_regime:
    - metodo: continuo
      altura_maxima_cm: 40
      altura_minima_cm: 20
      confianca: alta
      fonte: "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"
    # sem bloco `rotacionado`: nenhuma fonte localizada. Piquete de Xaraés em rotacionado
    # fica `aguardando_parametro` e o produtor informa a altura dele (ADR-014).
  ...
```

**Duas regras que saem deste formato (ADR-014):**

1. **Parâmetro que não depende de regime fica fora do bloco.** `densidade_kg_ha_por_cm`,
   `rue_max_g_por_mj`, `temperatura_base_c`, `descanso_*` e `qualidade_base` são da cultivar.
   Altura é do par cultivar × regime.
2. **Nada aqui é lido direto.** O acesso passa por `resolver_parametros(cultivar, metodo)`
   (`06` §3), que devolve o bloco **ou** a lista de `faltantes`. `null` com `TODO-PARAM` e bloco
   ausente fazem o sistema **recusar-se a prescrever** para aquele piquete, com mensagem clara —
   nunca default silencioso.
