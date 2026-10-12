# SPEC-019 — Replace the mock planner with the daily greedy engine and its alert catalog

## Context
Every day the system turns a projected farm state (forage height of each paddock today, its
forecast growth, where each herd is) into a 7-day grazing plan: which herd moves to which
paddock on which day, plus alerts. Today `planner/otimizador.py` is a demo mock. This spec
replaces it with a deterministic greedy engine that simulates the 7 days one by one, respects
the herd's group of paddocks (`modulo`) and the walking distance through feeding squares, and
emits a fixed catalog of alerts, each carrying a recommended action in Portuguese. The public
entry point keeps its signature, so the caller (`jobs/ciclo.py`) does not change.

## Domain vocabulary
- `piquete` — a fenced paddock. Keep this name in code.
- `lote` — a herd managed as one unit; never split. Keep this name in code.
- `modulo` — a group of paddocks; a `lote` with a `modulo_id` may only go to paddocks of that group.
- `praca` — feeding square where cattle drink; distance between paddocks goes through it.
- `altura_entrada_cm` / `altura_saida_cm` — entry height (paddock ready to be grazed) and exit
  height (herd must leave) of a rotational paddock.
- `descanso` — rest: days since the last herd left the paddock.
- `dia de manejo` — a weekday on which the farm accepts herd moves (`dias_preferenciais_manejo`).
- `massa` — forage dry matter, kg DM/ha. `altura = massa / densidade_kg_ha_por_cm`.
- `oferta` / `demanda` — daily forage growth available to a group vs. daily intake of its herds.

## Reading scope — read this file only

This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may **import** (not modify) these existing functions; their behaviour is described here:
- `seugado.planner.estrutura.distancia_manejo_m(origem: PiqueteProjetado, destino: PiqueteProjetado) -> float` — walking distance in metres via feeding squares; 0.0 for the same paddock.
- `seugado.planner.estrutura.piquetes_candidatos(estado, lote) -> tuple[PiqueteProjetado, ...]` — all paddocks if `lote.modulo_id is None`, else the paddocks with that `modulo_id`.
- `seugado.planner.estado.avancar_massa_um_dia(massa_kg_ms_ha, taxa_acumulo_kg_ms_ha_dia, consumo_lote_kg_ms_dia, area_ha, eficiencia_pastejo) -> float` — stock at the start of the next day.
- `seugado.core.forragem.dias_ocupacao(massa_atual_kg_ms_ha, massa_residuo_kg_ms_ha, taxa_acumulo_kg_ms_ha_dia, area_ha, eficiencia_pastejo, consumo_lote_kg_ms_dia) -> float` — may return `float("inf")`.
- `seugado.core.regras.combinar_confianca(*fatores: Confianca) -> Confianca` — weakest of the factors.

## Files to create or modify
- MODIFY `src/seugado/contratos.py` — only `TipoAlerta` and `Alerta` (R1)
- REWRITE `src/seugado/planner/otimizador.py` (R2–R7)
- CREATE `src/seugado/planner/alertas.py` (R8–R9)
- DELETE `tests/planner/test_otimizador_mock.py`
- CREATE `tests/planner/test_otimizador.py`
- CREATE `tests/planner/test_alertas.py`

## Requirements

### R1 — Contract additions (`contratos.py`)
Add four members to `TipoAlerta`, keeping every existing member and value:
```python
ABAIXO_DA_SAIDA = "abaixo_da_saida"
PRONTO_EM = "pronto_em"
SOBRA_DE_CAPIM = "sobra_de_capim"
FALTA_DE_CAPIM = "falta_de_capim"
```
Append two fields at the **end** of `Alerta`, with defaults, so plans serialized before this
spec still deserialize:
```python
acao: str = ""
modulo_id: UUID | None = None
```
Change nothing else in `contratos.py`. Every alert produced by this spec has a non-empty `acao`.

### R2 — Entry point (`otimizador.py`), signature unchanged
```python
def gerar_plano(
    estado: EstadoProjetado, fazenda: Fazenda, agora: datetime, plano_id: UUID
) -> PlanoManejo:
```
Returns `PlanoManejo(id=plano_id, fazenda_id=estado.fazenda_id, data_geracao=agora,
data_inicio=estado.data_base, horizonte_dias=HORIZONTE_DIAS, movimentacoes=..., alertas=...,
pedidos_validacao=(), piquetes=...)`. `piquetes` is one `ResumoPiquete` per paddock, sorted by
`nome`, built exactly as the current mock's `_resumos` does (keep that helper).
`movimentacoes` sorted by `(data, lote_nome)`; `alertas` sorted by `(data, tipo.value, texto)`.
Remove every `MOCK` constant and text. Pure function: no I/O, no clock, no randomness.

### R3 — Plannable paddocks
A paddock `p` is **plannable** when all hold: `metodo_pastejo == ROTACIONADO`, `faltantes == ()`,
`parametros` not None with both `altura_entrada_cm` and `altura_saida_cm` not None,
`massa_hoje_kg_ms_ha`, `densidade_kg_ha_por_cm` and `eficiencia_pastejo` not None, and
`taxa_acumulo_prevista_kg_ms_ha_dia` non-empty. Only plannable paddocks are simulated, used as
destinations, or counted in R9. Growth on day offset `i` is `taxa[i]`; if `i >= len(taxa)`, use
`taxa[-1]`.

A lote's position is `lote.piquete_atual_id`. A lote whose position is a non-plannable paddock
is ignored by the engine (never moved, no alert). A lote with `piquete_atual_id is None` is
**unplaced**.

### R4 — Day-by-day simulation
Simulate `HORIZONTE_DIAS` days, offset `d = 0..6`, `dia = estado.data_base + d`. State: `massa`
of each plannable paddock (starts at `massa_hoje_kg_ms_ha`), position of each lote, and `descanso`
of each plannable paddock (starts at `dias_descanso` if no lote is in it, else 0). A paddock is
**occupied** when any lote's position is it. Each day, in this order:
1. Record a `DiaSimulado` (R8) with the start-of-day state.
2. If `dia.weekday() in fazenda.dias_preferenciais_manejo`, run the moves of R5.
3. Advance each plannable paddock one day with `avancar_massa_um_dia`, using as intake the sum of
   `consumo_kg_ms_dia` of the lotes in it (0 if empty). Empty paddocks: `descanso += 1`.
   A paddock left by a lote on day `d` has `descanso = 0` on day `d` and 1 on `d + 1`.

If `dias_preferenciais_manejo` is empty, no move happens in the whole plan.

### R5 — Who must leave, in what order, within labour capacity
On a handling day, a lote in a plannable paddock **must leave** when the start-of-day height of its
paddock is `<= altura_saida_cm` on any of the days `dia + j`, `j = 0..k`, where `dia + k` is the
next handling day after `dia` (`1 <= k <= 7`). Project the days `j >= 1` from the current state
with `avancar_massa_um_dia` and the paddock's current occupants, without mutating the state.
Every unplaced lote also must leave (it needs a paddock).

Order: unplaced lotes first; then by `altura_saida_cm − altura_hoje_do_dia_cm` descending (higher
= more urgent); ties by `lote.nome`.

Capacity of the day, in animals: `fazenda.funcionarios_disponiveis * fazenda.animais_por_funcionario_dia`.
Lote size = sum of `n_animais` in `composicao`. Walk the ordered list keeping `usados`:
- if `usados + tamanho <= capacidade`: try to move it (R6);
- elif `usados == 0`: try to move it alone (a lote is never split). If it moves, the day's moves
  end: the following lotes fall in the `else` branch below. If it finds no destination (R6), it
  spends no capacity and the walk continues with the next lote;
- else: do not move it; emit `capacidade_excedida` (R7). It is retried next handling day.
`usados` grows only when a move actually happens.

### R6 — Choosing the destination
Candidates: `piquetes_candidatos(estado, lote)` filtered to plannable paddocks that are not
occupied and were not chosen as a destination earlier the same day. **Apt** = height of the day
`>= altura_entrada_cm` and `descanso >= descanso_min_dias`. Pick among apt candidates the one with
the largest `altura − altura_entrada_cm`; ties by smaller `distancia_manejo_m(origem, candidate)`
(skip this key when the lote is unplaced); then by `nome`.
If no apt candidate: **fallback** — candidates with `altura >= FATOR_FALLBACK_ENTRADA *
altura_entrada_cm` and rest met, same ordering. If still none: the lote stays, emit
`sem_piquete_apto` (R7); it does not consume capacity.

A move creates a `Movimentacao`:
- `id = uuid5(plano_id, f"{lote_id}:{dia.isoformat()}")`; `data = dia`.
- `altura_destino_cm`, `altura_origem_cm`: start-of-day heights, `round(x, 1)`; origem fields
  `None` when unplaced. `altura_entrada_alvo_cm` from the destination, `altura_saida_alvo_cm`
  from the origin (None when unplaced).
- `dias_previstos`: `x = dias_ocupacao(massa_destino, altura_saida_destino * densidade_destino,
  taxa_destino_do_dia, area_destino, eficiencia_destino, consumo_lote)`; if `x` is infinite use
  `HORIZONTE_DIAS`, else `min(HORIZONTE_DIAS, max(1, floor(x)))`.
- `motivo` (PT-BR, heights formatted `:.0f`):
  - placed: `"{origem} chega à altura de saída ({saida} cm). {destino} está com {h} cm, acima da entrada ({entrada} cm)."`
  - fallback destination: replace the second sentence with `"{destino} está com {h} cm, o mais perto da entrada ({entrada} cm) entre os disponíveis."`
  - unplaced: first sentence becomes `"{lote} está sem pasto registrado."`
- `confianca = combinar_confianca(destino.confianca, origem.confianca (if any), lote.confianca_peso)`;
  `motivo_confianca` = the motivo of the first factor, in that same order, whose confianca equals the result.

### R7 — Alerts decided inside the greedy loop
At most one alert per `(tipo, lote_id)`, dated on its first occurrence. `modulo_id = lote.modulo_id`.
`confianca`/`motivo_confianca`: from the lote's current paddock if placed, else `ALTA` /
`"Lote sem pasto registrado."`, except `capacidade_excedida`: `ALTA` / `"Mão de obra cadastrada da fazenda."`.

| tipo | texto | acao |
|---|---|---|
| `sem_piquete_apto` | `"Nenhum pasto pronto para o lote {lote} em {dd/mm}."` | `"Manter o lote {lote} onde está e conferir as alturas dos pastos do módulo com /alturas."` |
| `capacidade_excedida` | `"A equipe não dá conta de mover o lote {lote} em {dd/mm}."` | `"Reforçar a equipe nesse dia ou mover o lote {lote} no próximo dia de manejo."` |

When `dias_preferenciais_manejo` is empty, emit one farm alert: `sem_dia_de_manejo`, `data = data_base`,
texto `"Nenhum dia de manejo cadastrado na fazenda."`, acao `"Cadastrar os dias da semana em que a fazenda troca o gado de pasto."`,
`ALTA` / `"Configuração da fazenda."`, ids None.

### R8 — Trace type and catalog entry (`alertas.py`)
```python
@dataclass(frozen=True, slots=True)
class DiaSimulado:
    data: date
    dia_de_manejo: bool
    altura_cm: Mapping[UUID, float]        # plannable piquete_id -> start-of-day height
    descanso_dias: Mapping[UUID, int]      # plannable piquete_id -> rest at start of day
    posicao_lote: Mapping[UUID, UUID | None]  # lote_id -> piquete_id at start of day

def alertas_do_catalogo(
    estado: EstadoProjetado,
    plannable: Sequence[PiqueteProjetado],
    dias: Sequence[DiaSimulado],
    movimentacoes: Sequence[Movimentacao],
) -> tuple[Alerta, ...]:
```
`otimizador.py` imports `DiaSimulado` and `alertas_do_catalogo` from `alertas.py`; `alertas.py`
never imports `otimizador.py`. A paddock's **group** is its `modulo_id` (None = implicit
"farm group"); a lote belongs to group `lote.modulo_id`. "Destination in the plan" = its id is
some `piquete_destino_id` in `movimentacoes`. Dates in text are `dd/mm`; heights `:.0f`.
Paddock alerts carry the paddock's `confianca`/`motivo_confianca`, `piquete_id`, `modulo_id`.
At most one alert per `(tipo, piquete_id)` or `(tipo, lote_id)`, first date.

| tipo | fires when | texto | acao |
|---|---|---|---|
| `abaixo_da_saida` | day 0 only: occupied paddock with height `<= saida` | `"{P} está com {h} cm, no limite de saída ({saida} cm)."` | with a move of that lote dated day 0: `"Retirar o lote {L} hoje e levar para o {destino}."`; else `"Retirar o lote {L} hoje. Nenhum pasto do módulo está pronto no plano: conferir as alturas com /alturas."` (`L` = first lote in it by nome; `lote_id` set) |
| `sem_dia_de_manejo` | a day that is not a handling day where a lote's paddock height `<= saida` | `"O lote {L} passa da altura de saída no {P} em {dd/mm}, antes do próximo dia de manejo."` | `"Antecipar a troca do lote {L} para {dd/mm}."` (`lote_id` set) |
| `passando_do_ponto` | empty paddock, height `>= FATOR_PASSANDO_DO_PONTO * entrada`, not a destination in the plan | `"{P} está passando do ponto: {h} cm em {dd/mm} (entrada {entrada} cm)."` | `"Entrar com um lote do módulo no {P} até {dd/mm}; se nenhum puder, ver o alerta de sobra de capim."` |
| `pronto_em` | empty paddock, apt (R6 definition), not a destination in the plan; only the earliest per group (ties by `nome`) | `"{P} fica pronto para pastejo em {dd/mm}."` | `"Programar um lote do módulo para entrar no {P} em {dd/mm}."` |

### R9 — Offer vs. demand per group (`alertas.py`)
For each group that has at least one plannable paddock and at least one lote:
`oferta_d = Σ taxa(d) × area_ha × eficiencia_pastejo` over its plannable paddocks, `d = 0..6`
(R3 rule for `taxa`); `oferta = mean(oferta_d)`; `demanda = Σ consumo_kg_ms_dia` of its lotes.
Skip if `demanda == 0`. `razao = oferta / demanda`. Date = `data_base`; `piquete_id = lote_id =
None`; `modulo_id` = the group. `rotulo` = `"módulo de " + ", ".join(sorted paddock names)` or
`"pastos sem módulo"` for the farm group. `confianca` = weakest of the group's paddocks' and lotes'
(`confianca_peso`) confidences; `motivo_confianca` = the motivo of the first one with that level,
paddocks by `nome` before lotes by `nome`.
- `razao >= RAZAO_SOBRA` → `sobra_de_capim`, texto `"Sobra capim no {rotulo}: o pasto cresce {pct}% do que os animais comem."`, acao `"Trazer mais animais para o módulo ou tirar piquetes do rodízio."`
- `razao <= RAZAO_FALTA` → `falta_de_capim`, same texto pattern with `"Falta capim no {rotulo}: ..."`, acao `"Reduzir os animais do módulo ou juntar mais piquetes a ele."`
`pct = round(razao * 100)`. No alert ever states a number of animals.

## Constants and parameters

| Name | Value | Unit | Source |
|---|---|---|---|
| `HORIZONTE_DIAS` | 7 | days | Project decision: 7-day rolling horizon |
| `FATOR_FALLBACK_ENTRADA` | 0.9 | — | `HIPOTESE-CALIBRAR` (threshold calibration ADR) |
| `FATOR_PASSANDO_DO_PONTO` | 1.2 | — | `HIPOTESE-CALIBRAR` (threshold calibration ADR) |
| `RAZAO_SOBRA` | 1.2 | — | `HIPOTESE-CALIBRAR` (threshold calibration ADR) |
| `RAZAO_FALTA` | 0.8 | — | `HIPOTESE-CALIBRAR` (threshold calibration ADR) |

Each `HIPOTESE-CALIBRAR` constant carries that marker in a code comment. All agronomic values
(heights, density, efficiency, rest) come from `estado`; none is hard-coded.
`HORIZONTE_DIAS` and `FATOR_FALLBACK_ENTRADA` live in `otimizador.py`; the other three in `alertas.py`.

## Validation rules
- `fazenda.funcionarios_disponiveis * fazenda.animais_por_funcionario_dia <= 0` → `ValueError`.
- No exception for missing data: non-plannable paddocks are simply left out (R3).

## Testing — who does what

Write your own tests in `tests/planner/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `gerar_plano` keeps its exact signature; `jobs/ciclo.py` runs unchanged
- [ ] `TipoAlerta` has the 4 new members with the exact values; old members unchanged
- [ ] `Alerta` ends with `acao: str = ""` and `modulo_id: UUID | None = None`; a plan JSON without these keys deserializes with `plano_de_dict`
- [ ] Every alert in a generated plan has non-empty `acao`
- [ ] A lote with `modulo_id` never receives a destination outside its `modulo`
- [ ] No move is dated on a day outside `dias_preferenciais_manejo`
- [ ] Moved animals per day ≤ capacity, except a single lote larger than capacity moved alone
- [ ] A lote larger than capacity with no destination does not stop the other lotes from moving
- [ ] No destination is non-plannable, occupied, or below the fallback height, and none has rest unmet
- [ ] Same inputs → identical `PlanoManejo` (call twice and compare)
- [ ] Worked example reproduced
- [ ] No text contains `MOCK`, `demonstração`, or a number of animals
- [ ] `otimizador.py` and `alertas.py` each ≤ 300 lines; no import from `api/`, `persistencia/`, `delivery/`, `jobs/`, `sensing/` or any DB library
- [ ] `pytest`, `ruff check` and `mypy` pass on the whole repository
- [ ] No new dependency in `pyproject.toml`

## Worked example
Monday 2026-10-12, all 7 days are handling days, 1 worker × 100 animals/day. Every paddock:
Marandu rotational, entry 30 cm, exit 15 cm, density 110 kg DM/ha/cm, grazing efficiency 0.72,
minimum rest 21 days, forecast growth 50 kg DM/ha/day for 14 days. Group M1: P1 (2.0 ha, 17 cm,
holds lote L1), P2 (1.0 ha, 33 cm, rest 25), P3 (1.5 ha, 36 cm, rest 30), P4 (1.0 ha, 40 cm,
rest 10). Group M2: P5 (2.0 ha, 45 cm, rest 40). L1: `modulo_id = M1`, 50 animals, intake
405 kg DM/day.

Day 0: P1 tomorrow = 1870 + 50 − 405/(0.72×2) = 1638.75 kg → 14.9 cm ≤ 15 → L1 must leave today.
P4 fails rest, P5 is another group; P3 (36 − 30 = 6) beats P2 (3) → move L1: P1 → P3, day 0,
`dias_previstos = floor(2494.8 / 351) = 7`. Alerts: `pronto_em` P2 on 12/10 (M1), `pronto_em`
P5 on 12/10 (M2), `passando_do_ponto` P4 and P5 on 12/10 (40 and 45 ≥ 36; P4 is empty and
never a destination even though its rest is unmet), and `falta_de_capim` for M1
(oferta 50 × 5.5 × 0.72 = 198; razão 198/405 → 49%). M2 has no lote → no offer/demand alert.

## Out of scope
- Do NOT change `jobs/ciclo.py`, the bot, `delivery/` messages, persistence or the API
- Do NOT freeze or reuse moves already sent today; the caller handles that
- Do NOT implement lote merging, lookahead/"wait k days", local search or CP-SAT
- Do NOT emit `aguardando_parametro`, `estimativa_indisponivel`, `lote_sem_piquete`, `continuo_*` alerts
- Do NOT produce `pedidos_validacao` (always `()`)
- Do NOT change `EstadoProjetado`, `Movimentacao`, `PlanoManejo` or any other contract besides R1
- Do NOT read module or square names from the database; labels come from paddock names
- Do NOT add logging, caching, classes beyond `DiaSimulado`, or new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions only: no I/O, no global state, no side effects
- Variable names carry their unit: `altura_cm`, `massa_kg_ms_ha`, `distancia_m`
- Domain nouns stay in Portuguese; docstrings and comments in English; farmer-facing text in PT-BR
- Never use an entity as a dict key: key by its `id`
- Never compare members of different enums
- `__init__.py` files stay empty
- Maximum 300 lines per file
