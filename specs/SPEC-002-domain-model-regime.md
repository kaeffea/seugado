# SPEC-002 — Apply regime-specific grazing parameters to the domain model

## Context

This is an edit to an already-approved module, not a new module. `src/seugado/core/models.py`
defines pure, immutable domain entities (dataclasses and enums) for a pasture-management
system. It currently has 6 enums and 7 dataclasses, and every one of its 157 existing tests
passes. Two of its entities need a schema change because the domain rule changed: grazing
height used to be a property of a grass variety (`Cultivar`) alone; it is now a property of
the pair (grass variety, grazing method), because the same variety is managed at different
heights depending on whether the paddock is grazed continuously or in rotation, and most
combinations still have no documented height at all.

Most of the module is not affected. Only `Cultivar` changes shape, `Piquete` gains one field,
and two new type definitions are added. Everything else — 5 of the 6 existing enums, and 5 of
the 7 existing dataclasses (`Fazenda`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento`) — must
come out of this edit byte-for-byte identical to how they are today.

## Domain vocabulary

- `piquete` — a fenced paddock subdivision; the spatial unit. Keep this name in code.
- `lote` — a group of cattle managed as one unit. Keep this name in code.
- `cultivar` — a grass variety.
- `metodo_pastejo` — grazing method: continuous stocking (animals stay, stocking rate is
  adjusted) or rotational grazing (animals move between paddocks on a cycle).
- `altura_entrada_cm` / `altura_saida_cm` — in rotational grazing, the canopy height (cm) at
  which animals enter a paddock, and the residual height (cm) at which they leave it.
- `altura_maxima_cm` / `altura_minima_cm` — in continuous grazing, the canopy height (cm)
  thresholds that trigger raising or lowering the stocking rate.
- `confianca` — reliability tier of a value: high, medium, or low.
- `fonte` — the citation backing a specific value.

## Reading scope — read this file only

This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify

- MODIFY `src/seugado/core/models.py`
- MODIFY `tests/core/test_models.py`
- (never touch `__init__.py`: packages stay empty — see `06` §7 rule 10)

## Requirements

### R1 — Add the `MetodoPastejo` enum

A new `StrEnum` with exactly two members:

```python
class MetodoPastejo(StrEnum):
    """Grazing method: continuous stocking or rotational grazing."""

    CONTINUO = "continuo"
    ROTACIONADO = "rotacionado"
```

Declare it as the **third** enum in the file, immediately after `QualidadeBase` and before
`Confianca`. The file's declaration order becomes, top to bottom: `CategoriaAnimal`,
`QualidadeBase`, `MetodoPastejo`, `Confianca`, `StatusManejo`, `OrigemEvento`, `TipoEvento`.
No other enum changes.

### R2 — Add the `ParametrosRegime` dataclass

A new frozen, slotted dataclass holding the height parameters for one cultivar under one
grazing method. A cultivar will carry a tuple of these — one entry per grazing method it has
a documented source for. When a cultivar has no source for a given method, there is simply no
`ParametrosRegime` for that method in its tuple; this dataclass itself never represents an
empty or missing entry.

```python
@dataclass(frozen=True, slots=True)
class ParametrosRegime:
    """Height parameters for a cultivar under one grazing method.

    A cultivar carries one of these per grazing method it has a documented
    source for. The absence of a block for a given method means the source
    is missing, not that the height is null.
    """

    metodo: MetodoPastejo
    altura_entrada_cm: float | None
    altura_saida_cm: float | None
    altura_maxima_cm: float | None
    altura_minima_cm: float | None
    confianca: Confianca
    fonte: str
```

Field order is exactly as shown. All seven fields are required — **none has a default value**,
including the four `float | None` height fields: the caller always states explicitly which
heights apply (a real number) and which do not apply to this method (`None`). For example, a
`rotacionado` block always passes a real number for `altura_entrada_cm` and `altura_saida_cm`,
and `None` for `altura_maxima_cm` and `altura_minima_cm` — never the other way round, but
nothing in this dataclass enforces that pairing; it is a convention for callers, not a rule
this module checks. Declare it as the **second** dataclass in the file, immediately after
`Fazenda` and before `Cultivar` (it must be declared before `Cultivar` because `Cultivar`
references it in a type annotation).

### R3 — Change `Cultivar`: replace flat height fields with `parametros_por_regime`

Remove the two existing fields `altura_entrada_cm: float` and `altura_saida_cm: float`.
Add one new field, `parametros_por_regime: tuple[ParametrosRegime, ...]`, in the position
where the two removed fields used to be (immediately after `nome`, before
`densidade_kg_ha_por_cm`). The four fields that do not depend on grazing method —
`densidade_kg_ha_por_cm`, `temperatura_base_c`, `rue_max_g_por_mj`, `qualidade_base` — are
untouched and keep their exact position relative to each other.

Resulting field list, in order:

```python
@dataclass(frozen=True, slots=True)
class Cultivar:
    """Grass variety with its regime-specific management parameters."""

    id: UUID
    slug: str
    nome: str
    parametros_por_regime: tuple[ParametrosRegime, ...]
    densidade_kg_ha_por_cm: float
    temperatura_base_c: float
    rue_max_g_por_mj: float
    qualidade_base: QualidadeBase
```

Keep the existing one-line comments on `slug` and `nome` (`# stable machine key`,
`# display name`) exactly as they are today. `parametros_por_regime` has no default value —
`Cultivar` must continue to have zero default values on any field, exactly as it does today.

### R4 — Change `Piquete`: add `metodo_pastejo`

Add one new field, `metodo_pastejo: MetodoPastejo`, to `Piquete`. This field belongs to the
paddock, not the farm, because a single farm can have some paddocks under continuous grazing
and others under rotational grazing. It has no default value, so it must be placed **before**
the two fields that do have defaults (`geometria_geojson`, `ativo`) — Python does not allow a
required field after one with a default in the same dataclass.

Resulting field list, in order:

```python
@dataclass(frozen=True, slots=True)
class Piquete:
    """Fenced paddock where one lote grazes for a period."""

    id: UUID
    fazenda_id: UUID
    nome: str
    area_ha: float
    cultivar_id: UUID
    metodo_pastejo: MetodoPastejo
    geometria_geojson: dict[str, Any] | None = None
    ativo: bool = True
```

Nothing else about `Piquete` changes.

### R5 — Everything else in the file is untouched

`Fazenda`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento`, and the enums `CategoriaAnimal`,
`Confianca`, `StatusManejo`, `OrigemEvento`, `TipoEvento` keep their exact current field
lists, order, types, defaults, docstrings and comments. Do not reformat, reorder or "clean up"
anything you were not asked to change. The full resulting class declaration order, top to
bottom, is: `CategoriaAnimal`, `QualidadeBase`, `MetodoPastejo`, `Confianca`, `StatusManejo`,
`OrigemEvento`, `TipoEvento`, `Fazenda`, `ParametrosRegime`, `Cultivar`, `Piquete`,
`ComposicaoLote`, `Lote`, `Manejo`, `Evento`.

### R6 — Update the existing smoke tests that this change breaks

`tests/core/test_models.py` already exists and already constructs `Cultivar` and `Piquete`
instances. Three of its existing tests will fail to even construct their fixtures once R3 and
R4 land, because they use the old `Cultivar` fields and omit the new required `Piquete` field:

- `test_cultivar_carries_every_parameter_explicitly` — currently passes
  `altura_entrada_cm=1.0, altura_saida_cm=1.0` to `Cultivar`. Update it to pass
  `parametros_por_regime` instead, with at least one `ParametrosRegime` instance in the tuple.
- `test_entities_are_frozen` — currently constructs a `Piquete` without `metodo_pastejo`.
  Add it.
- `test_piquete_geometry_is_opaque_and_optional` — constructs two `Piquete` instances,
  neither with `metodo_pastejo`. Add it to both.

Do not delete or weaken what these tests check today (frozen-ness, optional geometry,
explicit-parameter requirement) — only add the new field and update the changed one. You may
also add new smoke tests of your own for `MetodoPastejo` and `ParametrosRegime`, kept short,
as this spec's Testing section describes.

## Constants and parameters

None. This change introduces no agronomic or numeric constant. `models.py` contains **zero
numeric literals today and must contain zero after this change** — see Style constraints.

## Validation rules

None. This module has no `__post_init__`, no `raise` statements and no runtime validation
anywhere today, and that must remain true. Do not add any — including inside
`ParametrosRegime`. An "empty" or contradictory `ParametrosRegime` (for example, all four
height fields `None`) is not this module's concern to reject.

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

- [ ] `MetodoPastejo` exists as a `StrEnum` with exactly two members: `CONTINUO = "continuo"`,
      `ROTACIONADO = "rotacionado"`
- [ ] `ParametrosRegime` exists as `@dataclass(frozen=True, slots=True)` with exactly the seven
      fields of R2, in that order, none with a default value
- [ ] `Cultivar` no longer has `altura_entrada_cm` or `altura_saida_cm`
- [ ] `Cultivar` has `parametros_por_regime: tuple[ParametrosRegime, ...]` in the position
      given in R3, with no default value
- [ ] `Cultivar` still has zero default values on any field
- [ ] `Piquete` has `metodo_pastejo: MetodoPastejo` in the position given in R4, with no
      default value
- [ ] `Fazenda`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento` are unchanged
- [ ] The five pre-existing enums other than the new one are unchanged
- [ ] Class declaration order in the file matches R5 exactly
- [ ] `models.py` still contains zero numeric literals and zero digit characters in any
      string (docstrings included)
- [ ] `models.py` is still under 300 lines
- [ ] `tests/core/test_models.py` updated per R6; `pytest tests/core/test_models.py` passes
      with zero failures
- [ ] No new dependency added to `pyproject.toml`
- [ ] No import added to `models.py` beyond what it already imports

## Worked example

Two illustrative `ParametrosRegime` blocks for the same cultivar, showing why the tuple can
hold more than one entry — a cultivar documented for both grazing methods:

```python
rotacionado = ParametrosRegime(
    metodo=MetodoPastejo.ROTACIONADO,
    altura_entrada_cm=80.0,
    altura_saida_cm=40.0,
    altura_maxima_cm=None,
    altura_minima_cm=None,
    confianca=Confianca.MEDIA,
    fonte="Embrapa Gado de Corte, CT-135",
)
continuo = ParametrosRegime(
    metodo=MetodoPastejo.CONTINUO,
    altura_entrada_cm=None,
    altura_saida_cm=None,
    altura_maxima_cm=75.0,
    altura_minima_cm=50.0,
    confianca=Confianca.MEDIA,
    fonte="Kill-Silveira (2020)",
)
# cultivar.parametros_por_regime == (rotacionado, continuo)
```

A `Piquete` of that cultivar under rotational grazing now states its method explicitly:
`Piquete(id=..., fazenda_id=..., nome="Piquete 7", area_ha=5.81, cultivar_id=...,
metodo_pastejo=MetodoPastejo.ROTACIONADO)`.

## Acceptance kit (tester only — NEVER paste into the coding agent)

Lives in `revisoes/KIT-ACEITE-002.md`, not in this spec.

## Out of scope

- Do NOT implement `resolver_parametros`, `ResolucaoParametros`, or anything in
  `core/regras.py` — that is a separate, later fatia (F-003)
- Do NOT add any validation, `__post_init__`, or logic that inspects or rejects a
  `ParametrosRegime` or a `Cultivar`'s tuple contents
- Do NOT add a default value to `parametros_por_regime` or to `metodo_pastejo`
- Do NOT add `metodo_pastejo` to `Fazenda` — it belongs to `Piquete`
- Do NOT touch `docs/`, `revisoes/`, `specs/`, or `tests/conformance/`
- Do NOT add database access, ORM models, migrations, or HTTP endpoints
- Do NOT add logging frameworks, DI containers, or decorators
- Do NOT refactor, reorder, or reformat any part of the file this spec did not ask you to
  change
- Do NOT create abstract base classes, interfaces, or helper methods on any class
- Do NOT add caching
- Do NOT rename any existing field, class, or module

## Style constraints

- Python 3.12, type hints on every public field
- Pure data only: no I/O, no global state, no side effects, no methods, no `__post_init__`
- Variable names carry their unit: `altura_entrada_cm`, not `altura_entrada`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `cultivar`, `metodo_pastejo`,
  `parametros_por_regime`
- Docstrings and comments in English
- **No numeric literal anywhere in the file, and no digit character inside any string
  literal (including docstrings).** This is an existing, deliberate property of this module —
  keep it true after your edit. Regular `#` comments may contain digits if truly needed, but
  prefer avoiding them; no digit may appear inside triple-quoted or single/double-quoted
  string content.
- Maximum 300 lines for `models.py`
