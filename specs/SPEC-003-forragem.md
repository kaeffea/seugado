# SPEC-003 — Implement forage mass, height, and occupation-time calculations

## Context

This is the second production module of SeuGado's calculation core. `core/forragem.py`
implements the pure arithmetic that connects satellite-estimated forage mass (`kg MS/ha`) to
the canopy height a producer reads in the field (`cm`), turns a herd's live weight into daily
forage demand, and computes how many days a herd can graze one paddock before reaching the
residual height — accounting for forage growth during that same period. Two agronomic
parameters this module depends on, canopy density and grazing efficiency, have no production
default yet (open research items `B1`/`B7`), so every function that needs them receives the
value as an argument instead of assuming one; this makes the module fully implementable and
testable today without inventing a plausible-looking number.

## Domain vocabulary

- `massa_forragem` — standing dry-matter forage mass, in `kg MS/ha`. The stock.
- `altura_cm` — canopy height in centimeters; what a producer reads with a measuring stick.
- `densidade_kg_ha_por_cm` — the linear density that converts between the two, specific to
  each cultivar. Not yet known for any cultivar (`TODO-PARAM`; see `05`, blocker `B1`).
- `piquete` — a fenced paddock; the spatial unit these masses are per hectare of.
- `lote` — a group of cattle grazing together; the unit of daily forage demand.
- `eficiencia_pastejo` — the fraction of the forage mass **above the residual height** that
  the herd actually ingests. It is **not** the observed utilization rate (see
  `taxa_utilizacao`, below) — conflating the two double-counts the same loss. Not yet known
  (`TODO-PARAM`; see `05`, blocker `B7`).
- `taxa_acumulo_kg_ms_ha_dia` — the daily forage growth rate. Produced elsewhere (the sensing
  module); this module only consumes it as a number.
- `taxa_utilizacao` — removed mass over pre-grazing mass. A descriptive, reporting-only
  figure; it never feeds back into a calculation.
- `dias_ocupacao` — the number of days a lote can graze one piquete before the residual mass
  is reached.
- `consumo_pct_pv` — daily intake expressed as a percentage of live weight (e.g. `2.42`, not
  the fraction `0.0242`).

## Reading scope — read this file only

This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify

- CREATE `src/seugado/core/forragem.py`
- CREATE `tests/core/test_forragem.py`
- (never touch `__init__.py`: packages stay empty — see `06` §7 rule 10)

## Requirements

### R1 — `massa_para_altura`

Convert standing forage mass to canopy height using a linear density.

```python
def massa_para_altura(
    massa_kg_ms_ha: float,
    densidade_kg_ha_por_cm: float,
) -> float:
    """Convert standing forage mass to canopy height via a linear density."""
```

Formula: `altura_cm = massa_kg_ms_ha / densidade_kg_ha_por_cm`.

### R2 — `altura_para_massa`

The exact inverse of R1.

```python
def altura_para_massa(
    altura_cm: float,
    densidade_kg_ha_por_cm: float,
) -> float:
    """Convert canopy height to standing forage mass via a linear density."""
```

Formula: `massa_kg_ms_ha = altura_cm * densidade_kg_ha_por_cm`.

`densidade_kg_ha_por_cm` is cultivar-specific and currently `TODO-PARAM` for every cultivar
(`05`, blocker `B1`). Neither function may declare a default value for it, hardcode a number
for it anywhere in the module, or fall back silently when it is not supplied — the caller
always states it explicitly, exactly like `eficiencia_pastejo` in R4.

### R3 — `consumo_lote_kg_ms_dia`

Total daily dry-matter intake of a lote, summed across category groups (`03` §6.1: what
consumes pasture is total live weight, not head count).

```python
from collections.abc import Sequence

def consumo_lote_kg_ms_dia(
    composicao: Sequence[tuple[int, float, float]],
) -> float:
    """Total daily dry-matter intake of a lote, summed across category groups.

    Each item of `composicao` is `(n_animais, peso_medio_kg, fracao_consumo_pv)`:
    the head count, mean live weight in kg, and daily intake as a fraction of
    live weight (e.g. 0.022 for 2.2%) for one category group within the lote.
    """
```

Formula: `Σ (n_animais * peso_medio_kg * fracao_consumo_pv)` over every item in `composicao`.
An empty `composicao` is a lote with no animals in it and returns `0.0` — this is not an
error case.

### R4 — `dias_ocupacao`

This is an existing contract (`06` §3) — the signature below must not change.

```python
def dias_ocupacao(
    massa_atual_kg_ms_ha: float,
    massa_residuo_kg_ms_ha: float,
    taxa_acumulo_kg_ms_ha_dia: float,
    area_ha: float,
    eficiencia_pastejo: float,
    consumo_lote_kg_ms_dia: float,
) -> float:
    """Return the number of days a lote can graze a piquete."""
```

The forage pool available for consumption grows while the herd is grazing (`03` §6.3), so the
naive `(massa_atual - massa_residuo) * area_ha * eficiencia_pastejo / consumo_lote_kg_ms_dia`
undercounts whenever `taxa_acumulo_kg_ms_ha_dia > 0`. Solve for the exact `dias_ocupacao` (call
it `D`) that makes total consumption equal total available mass over the same `D` days:

```
((massa_atual_kg_ms_ha - massa_residuo_kg_ms_ha) + taxa_acumulo_kg_ms_ha_dia * D)
    * area_ha * eficiencia_pastejo
  == consumo_lote_kg_ms_dia * D
```

This is linear in `D` and has a closed-form solution — do not iterate:

```
numerador   = (massa_atual_kg_ms_ha - massa_residuo_kg_ms_ha) * area_ha * eficiencia_pastejo
denominador = consumo_lote_kg_ms_dia - (taxa_acumulo_kg_ms_ha_dia * area_ha * eficiencia_pastejo)
D           = numerador / denominador
```

When `taxa_acumulo_kg_ms_ha_dia == 0`, this reduces exactly to the naive formula above.

If `denominador <= 0`, growth replenishes the pool at least as fast as the herd consumes it,
so the piquete never reaches the residual mass under these inputs: return `float("inf")`.

### R5 — `taxa_utilizacao`

Descriptive only — reporting, never a calculation input (`02`, `taxa_utilizacao`; ADR-010).

```python
def taxa_utilizacao(
    massa_pre_pastejo_kg_ms_ha: float,
    massa_pos_pastejo_kg_ms_ha: float,
) -> float:
    """Fraction of pre-grazing forage mass that disappeared during grazing."""
```

Formula: `(massa_pre_pastejo_kg_ms_ha - massa_pos_pastejo_kg_ms_ha) / massa_pre_pastejo_kg_ms_ha`.
Returns a fraction in `[0.0, 1.0]` (e.g. `0.44`, not `44`).

### R6 — `consumo_individual_kg_ms_dia`

Descriptive: back-calculates the per-animal daily intake implied by an observed mass loss,
independent of and not fed by R3–R4. Used for calibration and reporting (`03` §6.4).

```python
def consumo_individual_kg_ms_dia(
    consumo_total_kg_ms_ha: float,
    area_ha: float,
    dias_ocupacao: float,
    n_animais: int,
) -> float:
    """Descriptive per-animal daily intake, back-calculated from an observed mass loss."""
```

Formula: `consumo_total_kg_ms_ha * area_ha / dias_ocupacao / n_animais`.

### R7 — `consumo_pct_pv`

```python
def consumo_pct_pv(
    consumo_individual_kg_ms_dia: float,
    peso_medio_kg: float,
) -> float:
    """Descriptive daily intake as a percentage of live weight (e.g. 2.42, not 0.0242)."""
```

Formula: `consumo_individual_kg_ms_dia / peso_medio_kg * 100`.

## Constants and parameters

Every number below that is a real agronomic or zootechnic figure comes from
`05-PARAMETROS-CULTIVARES.md`, with the exact source noted. `densidade_kg_ha_por_cm` is
deliberately **absent** from this table: R1/R2 never receive a concrete value from this spec
because none is sourced yet (`TODO-PARAM`, `05` blocker `B1`) — their worked example below
uses an arbitrary round number solely to demonstrate the arithmetic, and that number is not an
agronomic claim.

| Name | Value | Unit | Source |
|---|---|---|---|
| `eficiencia_pastejo` (test value) | 1.0 | — | Neutralized value from `05`'s canonical regression case; production default remains `TODO-PARAM` (ADR-010, blocker `B7`) |
| `taxa_acumulo_kg_ms_ha_dia` (test value) | 0.0 | kg MS/ha/dia | Neutralized value from `05`'s canonical regression case |
| `massa_pre_pastejo_kg_ms_ha` | 4000 | kg MS/ha | `05`, Caso de regressão canônico (fazenda comercial real) |
| `massa_pos_pastejo_kg_ms_ha` | 2240 | kg MS/ha | idem |
| `area_piquete_ha` | 5.81 | ha | idem |
| `n_animais` | 220 | cabeças | idem |
| `peso_medio_kg` | 479 | kg | idem |
| `dias_ocupacao` (observado na fazenda) | 4 | dias | idem |
| `consumo_individual_kg_ms_dia` (esperado) | 11.62 | kg MS/animal/dia | idem, tolerância ±0.05 |
| `consumo_pct_pv` (esperado) | 2.42 | % do PV | idem, tolerância ±0.02 |
| `taxa_utilizacao` (esperado) | 0.44 | — | idem, tolerância ±0.01 |
| `peso_medio_kg` (recria, exemplo de literatura) | 300 | kg | `05`, Parâmetros zootécnicos (categoria novilho) |
| `fracao_consumo_pv` (recria, exemplo de literatura) | 0.022 | fração do PV | `03` §6.1 / `05`, Parâmetros zootécnicos (faixa 2,0–3,0%) |
| `consumo_lote_kg_ms_dia` (recria, esperado) | 6.6 | kg MS/dia | `03` §6.1, exemplo da literatura |

## Validation rules

- `massa_para_altura`: raise `ValueError` if `densidade_kg_ha_por_cm <= 0`; raise `ValueError`
  if `massa_kg_ms_ha < 0`
- `altura_para_massa`: raise `ValueError` if `densidade_kg_ha_por_cm <= 0`; raise `ValueError`
  if `altura_cm < 0`
- `consumo_lote_kg_ms_dia`: for every item in `composicao`, raise `ValueError` if
  `n_animais < 0`, if `peso_medio_kg <= 0`, or if `fracao_consumo_pv` is outside `(0.0, 1.0]`
- `dias_ocupacao`: raise `ValueError` if `eficiencia_pastejo` is outside `[0.0, 1.0]`; raise
  `ValueError` if `area_ha <= 0`; raise `ValueError` if `consumo_lote_kg_ms_dia <= 0`; return
  `0.0` (not negative) if `massa_atual_kg_ms_ha <= massa_residuo_kg_ms_ha`; return
  `float("inf")` if the growth-adjusted denominator (R4) is `<= 0`
- `taxa_utilizacao`: raise `ValueError` if `massa_pre_pastejo_kg_ms_ha <= 0`; raise
  `ValueError` if `massa_pos_pastejo_kg_ms_ha < 0` or if
  `massa_pos_pastejo_kg_ms_ha > massa_pre_pastejo_kg_ms_ha`
- `consumo_individual_kg_ms_dia`: raise `ValueError` if `area_ha <= 0`, if
  `dias_ocupacao <= 0`, or if `n_animais <= 0`
- `consumo_pct_pv`: raise `ValueError` if `peso_medio_kg <= 0`

## Testing — who does what

Write your own tests in `tests/core/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria

- [ ] `massa_para_altura`, `altura_para_massa`, `consumo_lote_kg_ms_dia`, `dias_ocupacao`,
      `taxa_utilizacao`, `consumo_individual_kg_ms_dia`, and `consumo_pct_pv` all exist with
      the exact signatures given above
- [ ] `massa_para_altura` and `altura_para_massa` are exact inverses of one another for any
      positive `densidade_kg_ha_por_cm`
- [ ] Canonical regression case (`05`) reproduces `consumo_individual_kg_ms_dia ≈ 11.62`
      (±0.05), `consumo_pct_pv ≈ 2.42` (±0.02), and `taxa_utilizacao ≈ 0.44` (±0.01) from its
      exact inputs
- [ ] `dias_ocupacao` reproduces ≈4.0 days (±0.05) from the canonical case's masses and area,
      with `consumo_lote_kg_ms_dia = 2556.4` (= 220 × 11.62), `eficiencia_pastejo = 1.0`, and
      `taxa_acumulo_kg_ms_ha_dia = 0.0`
- [ ] `consumo_lote_kg_ms_dia` reproduces `6.6` for the single-category literature example
      (`[(1, 300.0, 0.022)]`)
- [ ] `dias_ocupacao` returns `float("inf")` when the growth-adjusted denominator is `<= 0`
- [ ] `consumo_lote_kg_ms_dia` returns `0.0` for an empty `composicao`, without raising
- [ ] Every validation rule above raises `ValueError` under its stated condition
- [ ] All public functions have type hints
- [ ] Module imports nothing from `sensing/`, `planner/`, `api/`, `core.models`, or any DB
      library
- [ ] `pytest tests/core/test_forragem.py` passes with zero failures
- [ ] No new dependency added to `pyproject.toml`

## Worked example

Bridge (R1/R2) — arithmetic check only, **not** an agronomic claim (`densidade_kg_ha_por_cm`
stays `TODO-PARAM`, `05` blocker `B1`): with an arbitrary `densidade_kg_ha_por_cm = 100.0`,
`altura_para_massa(40.0, 100.0) == 4000.0`, and `massa_para_altura(4000.0, 100.0) == 40.0`.

`consumo_lote_kg_ms_dia` — literature example (`03` §6.1): a single category of one animal at
300 kg consuming 2.2% of live weight gives `consumo_lote_kg_ms_dia([(1, 300.0, 0.022)]) == 6.6`.

Canonical commercial-farm case (`05`), with `eficiencia_pastejo = 1.0` and
`taxa_acumulo_kg_ms_ha_dia = 0.0` (this source reports all disappearance as intake; see
ADR-010):

- `taxa_utilizacao(4000.0, 2240.0) == 0.44`
- `consumo_individual_kg_ms_dia(1760.0, 5.81, 4.0, 220) ≈ 11.62`
  (`consumo_total_kg_ms_ha = massa_pre - massa_pos = 4000 - 2240 = 1760`)
- `consumo_pct_pv(11.62, 479.0) ≈ 2.42`
- `dias_ocupacao(4000.0, 2240.0, 0.0, 5.81, 1.0, 2556.4) ≈ 4.0`
  (`consumo_lote_kg_ms_dia = 220 × 11.62 = 2556.4`, the herd's total daily intake)

## Acceptance kit (tester only — NEVER paste into the coding agent)

Lives in `revisoes/KIT-ACEITE-003.md`, not in this spec.

## Out of scope

- Do NOT add a production default for `densidade_kg_ha_por_cm` or `eficiencia_pastejo` —
  both stay `TODO-PARAM` until `[PESQUISA]` resolves them (`05`, blockers `B1` and `B7`)
- Do NOT import `Cultivar`, `Piquete`, `Lote`, or anything else from `core/models.py` —
  this module receives only floats, ints, and plain tuples (`06` §3; `11`, "Correção de
  17/09/2026")
- Do NOT implement `resolver_parametros`, `apto_para_entrada?`, `precisa_sair?`, `urgencia`,
  or any other part of `core/regras.py` — that is F-003, a separate fatia
- Do NOT implement SAFER, NDVI ingestion, or any function of `sensing/`
- Do NOT model `senescencia` (natural leaf death) — out of scope for this fatia
- Do NOT add database access, ORM models, or migrations
- Do NOT add HTTP endpoints
- Do NOT implement the optimizer or any scheduling logic
- Do NOT add logging frameworks, DI containers, or decorators
- Do NOT refactor or reorganise existing files
- Do NOT create abstract base classes or interfaces
- Do NOT add caching

## Style constraints

- Python 3.12, type hints on every public function
- Pure functions only: no I/O, no global state, no side effects
- Variable names carry their unit: `massa_kg_ms_ha`, not `massa`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `massa_forragem`, `cultivar` (in
  docstrings/comments only — no domain entity is imported or constructed here)
- Docstrings and comments in English
- Prefer functions over classes; no abstraction without a second use case
- Maximum 300 lines per file
