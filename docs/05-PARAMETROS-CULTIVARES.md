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
resolve** o `TODO-PARAM` de altura de entrada rotacional para Marandu/Xaraés — o documento
simplesmente não modela essas cultivares nesse regime. O TODO-PARAM permanece, mas muda de
natureza: não é mais "falta dado", é "falta decidir se braquiária no SeuGado roda em
contínuo (dado existe, alta confiança) ou em rotacionado (dado não existe nesta fonte)".
Essa é uma decisão de arquitetura — fica registrada aqui para um chat `[ARQUITETURA]`
futuro, não decidida neste `[PESQUISA]`.

#### Tabela A — Pastejo rotacionado (coloniões / *Panicum* spp.)

| Cultivar | Entrada (cm) | Saída (cm) | Confiança | Notas |
|---|---|---|---|---|
| Mombaça | 85 | 45 | media | Diverge um pouco de fonte anterior (90/40) — ver nota abaixo |
| Zuri | 80 | 40 | alta | Entrada já registrada antes já batia com o CT-135; saída resolve TODO-PARAM |
| Tanzânia | 70 | 35 | media | Saída diverge um pouco de fonte anterior (30) — ver nota abaixo |
| Massai | 55 | 30 | alta | Resolve TODO-PARAM de saída |
| Tamani | 50 | 25 | alta | Resolve TODO-PARAM de saída |
| Quênia | 65 | 35 | alta | Fora do escopo atual do projeto (não é uma das 8 cultivares-alvo). Registrado porque veio de graça na mesma fonte — sem TODO-PARAM associado hoje |

#### Tabela B — Pastejo contínuo (braquiárias)

| Cultivar | Máxima (cm) | Mínima (cm) | Confiança | Notas |
|---|---|---|---|---|
| Xaraés | 40 | 20 | alta | Grandeza é contínua, não rotacional — não resolve `altura_entrada_cm` rotacional (TODO-PARAM mantido) |
| Piatã | 40 | 20 | alta | Cultivar nova nesta tabela |
| Marandu | 35 | 20 | alta | Grandeza é contínua — não resolve `altura_entrada_cm` rotacional (TODO-PARAM mantido). Prioridade do projeto (braquiária mais plantada do Brasil) |
| *B. decumbens* | 30 | 15 | alta | Cultivar nova nesta tabela |
| *B. humidicola* | TODO-PARAM | TODO-PARAM | ausente | **Não coberto pelo CT-135** — retirado da edição revisada. Segue sem fonte |
| Cameroon (capim-elefante) | 100 (entrada) | 45 (saída) | alta | **Não coberto pelo CT-135** (*Pennisetum*, fora de escopo do documento). Mantido o dado anterior — fonte experimental dedicada, melhor do que o CT-135 traria de qualquer forma |

### Notas por cultivar

**Mombaça.** CT-135: entrada 85 cm, saída 45 cm. Fonte anterior (podcast Embrapa "Primeiro
Pastejo") registrava ~90 cm para 90% de IL e 115 cm para 100% IL; saída aparecia como 30, 40
e 50 cm em fontes experimentais diferentes (resíduos testados). **Registrando a faixa, sem
escolher calado:** entrada 85–90 cm, saída 30–50 cm. Default recomendado: usar o valor do
CT-135 (85/45) por ser fonte institucional específica para esta decisão, mantendo a faixa
como `altura_entrada_faixa`/`altura_saida_faixa` configurável.

**Tanzânia.** CT-135: entrada 70 cm, saída 35 cm. Fonte anterior já convergia em 70 cm de
entrada; saída divergia (30 cm). Estudo de resíduos testou 30 e 50 cm, com resíduo de 50 cm
gerando IL pós-pastejo de 67% (vs. 40% com 30 cm) e mais ciclos de pastejo por período. →
Faixa de saída: 30–50 cm, default CT-135 (35).

**Massai / Zuri / Tamani.** Entrada já registrada antes batia exatamente com o CT-135 nos
três casos — bom sinal de que a fonte anterior (não documentada por nome) já vinha desta
mesma régua. Saída estava `TODO-PARAM` nos três; resolvida agora pelo CT-135 (30/40/25 cm
respectivamente).

**Xaraés / Marandu (contínuo).** CT-135 dá faixa 20–40 cm (Xaraés) e 20–35 cm (Marandu) para
pastejo **contínuo** — ajuste de lotação, não giro de piquete. O dado antigo de "saída
10–15 cm" para Marandu e "saída 15 cm" para Xaraés era para **rotacionado** e continua sem
fonte identificada; não foi descartado, só mantido separado por ser grandeza diferente.
Marandu é `TODO-PARAM` prioritário para entrada rotacional — ver achado estrutural acima.

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
| `altura_entrada_cm` rotacional — Marandu, Xaraés | regra de entrada | 🟠 alta | CT-135 (17/09/2026) não resolve: só cobre estas cultivares em contínuo. Ou se obtém fonte específica de rotacionado, ou vira decisão de regime (`[ARQUITETURA]`) |
| `altura_maxima/minima_cm` contínuo — *B. humidicola* | regra de contínuo | 🟡 média | CT-135 não cobre; cultivar retirada da edição revisada. Buscar fonte alternativa se a cultivar entrar em produção |
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

### Pesos médios por categoria — TODO-PARAM

| Categoria | Peso médio (kg) | Consumo (% PV) | Confiança |
|---|---|---|---|
| bezerro | TODO-PARAM | TODO-PARAM | ausente |
| novilho | ~300 | 2,2 % | média |
| adulto | ~450–480 | 2,4 % | média |

Referências ancoradas: recria de **300 kg a 2,2%** → 6,6 kg MS/dia.
Machos inteiros de **479 kg** consumindo **11,62 kg MS/dia** (2,42% PV).
→ Bezerro é lacuna real. Resolver em `[PESQUISA]`.

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

```yaml
mombaca:
  nome_exibicao: "Mombaça"
  especie: "Panicum maximum"
  via_fotossintetica: C4
  regime: rotacionado
  altura_entrada_cm: 85
  altura_entrada_faixa: [85, 90]
  altura_saida_cm: 45
  altura_saida_faixa: [30, 50]
  densidade_kg_ha_por_cm: null      # TODO-PARAM
  rue_max_g_por_mj: null            # TODO-PARAM (C4)
  temperatura_base_c: null          # TODO-PARAM
  descanso_min_dias: 21
  descanso_max_dias: 45
  qualidade_base: alta
  fontes:
    altura_entrada: "Embrapa Gado de Corte, CT-135, Costa & Queiroz (2013/ed. rev. 2017)"
    altura_saida: "idem"
  observacoes: >
    Fonte anterior (podcast Embrapa "Primeiro Pastejo") registrava ~90cm (90% IL) e
    115cm (100% IL) para entrada; saída documentada em 30/40/50cm em estudos de resíduo.
    Faixa mantida como configurável; default é o valor institucional do CT-135.
  confianca: media

marandu:
  nome_exibicao: "Marandu"
  especie: "Brachiaria brizantha"
  via_fotossintetica: C4
  regime: continuo
  altura_maxima_cm: 35
  altura_minima_cm: 20
  altura_entrada_cm: null            # TODO-PARAM — CT-135 não cobre rotacionado p/ Marandu
  altura_saida_cm: null              # TODO-PARAM — mesma razão; ver nota de 10-15cm sem fonte
  densidade_kg_ha_por_cm: null       # TODO-PARAM
  rue_max_g_por_mj: null             # TODO-PARAM (C4)
  temperatura_base_c: null           # TODO-PARAM
  descanso_min_dias: 21
  descanso_max_dias: 45
  qualidade_base: alta
  fontes:
    altura_maxima: "Embrapa Gado de Corte, CT-135, Costa & Queiroz (2013/ed. rev. 2017)"
    altura_minima: "idem"
  observacoes: >
    CT-135 só documenta esta cultivar em pastejo contínuo. Prioridade do projeto —
    braquiária mais plantada do Brasil — segue com TODO-PARAM para uso em rotacionado.
  confianca: alta
```

Todo parâmetro `null` com comentário `TODO-PARAM` faz o sistema **recusar-se a operar**
com aquela cultivar, exibindo mensagem clara — em vez de usar default silencioso.
