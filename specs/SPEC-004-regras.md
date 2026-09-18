# SPEC-004 — Grazing management rules and single parameter gateway

## Context
This module decides, from heights alone, whether a rotationally-grazed piquete (paddock) is
ready to receive a lote (herd group), whether the lote currently there must leave, and how
urgent that is — plus `resolver_parametros`, the single gateway (ADR-014) through which any
caller obtains a cultivar's height parameters for one grazing method. Everything here is a
pure function: no I/O, no database, no knowledge of the optimizer or the message text sent to
the farmer.

## Domain vocabulary
- `piquete` — fenced paddock; the spatial unit. Keep this name in code.
- `lote` — a group of cattle managed as one unit. Keep this name in code.
- `cultivar` — grass variety. Keep this name in code.
- `metodo_pastejo` — grazing method: `continuo` (continuous stocking) or `rotacionado`
  (rotational grazing).
- `altura_entrada_cm` / `altura_saida_cm` — rotational entry target height and exit
  (residue) target height.
- `altura_maxima_cm` / `altura_minima_cm` — continuous-stocking trigger heights (raise or
  lower stocking). Not used by this spec's functions — continuous stocking has no
  entry/exit/urgency concept; it gets its own weekly loop in a later slice (F-009B).
- `descanso` — the rest period a piquete needs between grazing cycles.
- `resolver_parametros` — the sole gateway function that resolves a cultivar's height block
  for a given method (ADR-014). Nobody reads cultivar parameters any other way.
- `faltantes` — names of the missing fields that block resolution.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- CREATE `src/seugado/core/regras.py`
- CREATE `tests/core/test_regras.py`
- Do NOT modify `src/seugado/core/models.py`
- Do NOT modify `src/seugado/core/forragem.py`
- (never list `__init__.py`: packages stay empty)

## Requirements

### R1 — `ResolucaoParametros` and `resolver_parametros`: the single parameter gateway

```python
from dataclasses import dataclass
from seugado.core.models import Cultivar, MetodoPastejo, ParametrosRegime


@dataclass(frozen=True, slots=True)
class ResolucaoParametros:
    """Outcome of resolving a cultivar's height parameters for one grazing method."""

    parametros: ParametrosRegime | None
    faltantes: tuple[str, ...]


def resolver_parametros(
    cultivar: Cultivar,
    metodo: MetodoPastejo,
) -> ResolucaoParametros:
    """Resolve the height parameter block a cultivar carries for one grazing method.

    This is the only function in the codebase allowed to read
    `cultivar.parametros_por_regime`. Everyone else calls this and acts on its result.
    """
```

Behavior:
- Search `cultivar.parametros_por_regime` for the single entry whose `.metodo == metodo`.
  If more than one entry matches, use the first one found (that duplication is a data
  problem for the catalog to fix, not something this function raises on).
- **No entry found for that method** (the cell is empty — ADR-014): return
  `parametros=None` and `faltantes` naming every required field for that method:
  - `metodo == MetodoPastejo.ROTACIONADO` → `("altura_entrada_cm", "altura_saida_cm")`
  - `metodo == MetodoPastejo.CONTINUO` → `("altura_maxima_cm", "altura_minima_cm")`
- **Entry found**: check the fields required for that method (same two per method, listed
  above). Any of them that is `None` on the entry goes into `faltantes`, in the order
  listed above. If none are missing, return `ResolucaoParametros(parametros=entry,
  faltantes=())`. If any is missing, return `ResolucaoParametros(parametros=None,
  faltantes=tuple(missing))` — a partially-filled block is never handed out; the contract
  is binary (parameters usable XOR named as missing).
- This function never raises for a missing or partial block. That is the expected,
  everyday shape of the catalog (ADR-014) — not an error.

### R2 — `apto_para_entrada`

```python
def apto_para_entrada(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
    descanso_cumprido: bool,
) -> bool:
    """Return whether a rotational piquete is ready to receive a lote."""
```

- Defined **only** for `parametros.metodo == MetodoPastejo.ROTACIONADO`. Raise `ValueError`
  otherwise.
- Raise `ValueError` if `parametros.altura_entrada_cm is None` — callers must pass a block
  that `resolver_parametros` already confirmed is complete; this function does not resolve
  parameters itself.
- Logic: `True` iff `altura_atual_cm >= parametros.altura_entrada_cm and descanso_cumprido`.
  (`descanso_cumprido` is the caller's own boolean result from R5, not recomputed here —
  keeps this function free of dates.)

### R3 — `precisa_sair`

```python
def precisa_sair(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
) -> bool:
    """Return whether the lote grazing a rotational piquete must leave now."""
```

- Defined **only** for `parametros.metodo == MetodoPastejo.ROTACIONADO`. Raise `ValueError`
  otherwise.
- Raise `ValueError` if `parametros.altura_saida_cm is None`.
- Logic: `True` iff `altura_atual_cm <= parametros.altura_saida_cm`.

### R4 — `urgencia`

```python
def urgencia(
    altura_atual_cm: float,
    parametros: ParametrosRegime,
) -> float:
    """Return a signed urgency score, in cm, for leaving a rotational piquete.

    Score = altura_saida_cm - altura_atual_cm. Zero or positive means the piquete has
    already reached (or passed) its exit target — `precisa_sair` would be True. More
    negative means more headroom above the exit target, i.e. less urgent. Sorting lotes by
    this score, descending, ranks "must leave now" above "at the point" above "can wait" —
    the ordering `07-MOTOR-DE-OTIMIZACAO.md` §5 (Estágio 1) needs for the greedy heuristic.
    """
```

- Defined **only** for `parametros.metodo == MetodoPastejo.ROTACIONADO`. Raise `ValueError`
  otherwise.
- Raise `ValueError` if `parametros.altura_saida_cm is None`.
- Logic: `parametros.altura_saida_cm - altura_atual_cm`.
- **`HIPOTESE-CALIBRAR`.** The scale (raw cm, not normalized by the entrada–saida range) is
  a design choice for this slice, not a sourced number. If a future slice needs urgency
  comparable across piquetes with very different entrada–saida ranges, revisit in an ADR
  named for that calibration. It does not block F-003: the greedy heuristic (F-009) only
  needs a consistent ordering, which raw cm already gives.

### R5 — `descanso_cumprido`

```python
def descanso_cumprido(
    dias_desde_ultima_saida: int,
    descanso_min_dias: float,
) -> bool:
    """Return whether the minimum rest period since the last exit has been met."""
```

- Raise `ValueError` if `dias_desde_ultima_saida < 0`.
- Raise `ValueError` if `descanso_min_dias <= 0`.
- Logic: `True` iff `dias_desde_ultima_saida >= descanso_min_dias`.
- `descanso_min_dias` is received as an argument, never hardcoded — same pattern
  `core/forragem.py` already uses for `eficiencia_pastejo` (ADR-010). The general fallback
  value (not yet split by cultivar) lives in the constants table below.

## Constants and parameters

| Name | Value | Unit | Source |
|---|---|---|---|
| `descanso_min_dias` (geral, usar como argumento nos testes) | 21 | dias | `05-PARAMETROS-CULTIVARES.md`, "Parâmetros zootécnicos", confiança alta |

No other numeric constant is used by this module — every other value in the functions above
is a caller-supplied height already sourced through `resolver_parametros` from
`ParametrosRegime`.

## Validation rules
- `resolver_parametros`: never raises. A missing or partial block is a normal result,
  reported through `faltantes`.
- `apto_para_entrada`, `precisa_sair`, `urgencia`: raise `ValueError` if
  `parametros.metodo != MetodoPastejo.ROTACIONADO`.
- `apto_para_entrada`: raise `ValueError` if `parametros.altura_entrada_cm is None`.
- `precisa_sair`, `urgencia`: raise `ValueError` if `parametros.altura_saida_cm is None`.
- `descanso_cumprido`: raise `ValueError` if `dias_desde_ultima_saida < 0` or
  `descanso_min_dias <= 0`.

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
- [ ] `ResolucaoParametros` exists as `frozen=True, slots=True` with exactly the two fields
      shown in R1
- [ ] `resolver_parametros`, `apto_para_entrada`, `precisa_sair`, `urgencia`,
      `descanso_cumprido` all exist with the exact signatures above
- [ ] Canonical worked-example case passes (see Worked example)
- [ ] All public functions and the dataclass have type hints
- [ ] Module imports only from `seugado.core.models` (plus the standard library) — nothing
      from `sensing/`, `planner/`, `delivery/`, `api/`, or any DB library
- [ ] `apto_para_entrada`, `precisa_sair`, `urgencia` raise `ValueError` on a `continuo`
      `ParametrosRegime`
- [ ] `resolver_parametros` never raises, for any combination of present/absent/partial
      blocks
- [ ] `pytest tests/core/test_regras.py` passes with zero failures
- [ ] No new dependency added to `pyproject.toml`
- [ ] File is at most 300 lines

## Worked example
A `Cultivar` carries one rotational block: `altura_entrada_cm=90.0`, `altura_saida_cm=40.0`,
`altura_maxima_cm=None`, `altura_minima_cm=None`, `confianca=Confianca.ALTA`,
`fonte="worked example"` — no continuous block.

- `resolver_parametros(cultivar, MetodoPastejo.ROTACIONADO)` → the block above, `faltantes=()`.
- `resolver_parametros(cultivar, MetodoPastejo.CONTINUO)` → `parametros=None`,
  `faltantes=("altura_maxima_cm", "altura_minima_cm")` (no continuous entry at all).
- At `altura_atual_cm=88.0` (below the 90 cm entry target): `apto_para_entrada` is `False`
  even if `descanso_cumprido=True`; `precisa_sair` is `False`; `urgencia` is
  `40.0 - 88.0 = -48.0`.
- At `altura_atual_cm=38.0` (below the 40 cm exit target, matching the Piquete 3 example in
  `07-MOTOR-DE-OTIMIZACAO.md` §6): `precisa_sair` is `True`; `urgencia` is
  `40.0 - 38.0 = 2.0`.
- `descanso_cumprido(dias_desde_ultima_saida=21, descanso_min_dias=21)` → `True`.
  `descanso_cumprido(20, 21)` → `False`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-004.md`. Must contain:
- Structural checks: forbidden imports, `frozen=True, slots=True` on `ResolucaoParametros`,
  absence of `__post_init__` / custom `__hash__` / `__all__`, no extra public functions,
  file length limit.
- The canonical worked-example case with its tolerance.
- **At least one numeric case the spec does not show** — the partial-block case (an entry
  present for the requested method but with one required field still `None`, e.g. a
  rotational block with `altura_saida_cm=None`) must resolve to `parametros=None,
  faltantes=("altura_saida_cm",)`, not to a partially-filled result.

## Out of scope
- Do NOT implement `massa ↔ altura` conversions or any forage-mass math — that is
  `core/forragem.py` (F-002), already done
- Do NOT implement the optimizer, the greedy heuristic, or any scheduling/assignment logic
  (F-009 and later)
- Do NOT implement continuous-stocking rules (`altura_maxima_cm` / `altura_minima_cm`
  triggers, stocking adjustment) — that is F-009B, a separate, later slice
- Do NOT generate the farmer-facing message text — that is `delivery/mensagem.py` (F-011)
- Do NOT add persistence, events, or any database access
- Do NOT modify `models.py` or `forragem.py`
- Do NOT add HTTP endpoints
- Do NOT add logging frameworks, DI containers, or decorators
- Do NOT add caching
- Do NOT refactor or reorganise existing files

## Style constraints
- Python 3.12, type hints on every public function and dataclass field
- Pure functions only: no I/O, no global state, no side effects
- Variable names carry their unit: `altura_atual_cm`, not `altura`; `descanso_min_dias`,
  not `descanso_min`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `cultivar`, `metodo_pastejo`,
  `descanso`
- Docstrings and comments in English
- Prefer functions over classes; the one dataclass here (`ResolucaoParametros`) is a plain
  data carrier, not behavior
- Maximum 300 lines
