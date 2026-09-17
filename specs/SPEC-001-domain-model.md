# SPEC-001 — Define pure domain entities for pasture management

## Context

This is the first code file of a rotational-grazing decision system. It defines the pure
data structures that every other module will pass around: farms, fenced paddocks, cattle
groups, grass varieties, movement records, and an immutable event log entry.

This file is data only. It holds no calculations, no persistence, no validation of
agronomic rules, and no I/O. Later modules compute forage mass, decide when cattle must
move, and store events in a database; none of that belongs here. The value of this file is
that it makes the domain vocabulary unambiguous and type-checked before any logic exists.

The system is event-sourced: every real-world occurrence is appended to an immutable event
log and current state is *derived* from that log, never edited in place. That is why every
entity here is an immutable (frozen) dataclass.

## Domain vocabulary

These Portuguese domain nouns are the canonical names. **Keep them in Portuguese in code**
— translating them creates ambiguity (e.g. *paddock* vs *plot* vs *field*). Docstrings and
comments are in English.

- `fazenda` — a farm; the top-level owner of everything else.
- `piquete` — a fenced paddock subdivision where one `lote` grazes for a period. The
  spatial unit of the system.
- `lote` — a group of cattle managed as a single unit. Animals are never moved
  individually, only as a `lote`.
- `cultivar` — a specific grass variety (e.g. Mombaça, Marandu). Management parameters
  differ *within* the same botanical species, which is why the cultivar, not the species,
  is modelled.
- `manejo` — one movement of a `lote` between paddocks (take it out of one, put it into
  another). It is the unit of farm labour.
- `massa_forragem` — available forage dry matter, in kg DM per hectare.
- `altura_entrada_cm` / `altura_saida_cm` — canopy height at which cattle should enter /
  leave a paddock, in centimetres.
- `densidade_kg_ha_por_cm` — kg of dry matter per hectare contained in each centimetre of
  canopy height; converts a measured height into forage mass.
- `categoria` — animal category (calf / yearling / adult), which determines average live
  weight.
- `evento` — an immutable record that something happened.

## Files to create or modify

The agent must not touch any file outside this list.

- CREATE `seugado/__init__.py` (empty)
- CREATE `seugado/core/__init__.py` (empty — do NOT add re-exports)
- CREATE `seugado/core/models.py`
- CREATE `tests/__init__.py` (empty)
- CREATE `tests/core/__init__.py` (empty)
- CREATE `tests/core/test_models.py`

## Requirements

### R1 — Module header and imports

`seugado/core/models.py` must import **only** from the Python standard library:
`dataclasses`, `datetime`, `enum`, `typing`, `uuid`. Any other import is a failure.

All entities in this file use:

```python
@dataclass(frozen=True, slots=True)
```

Rationale to state in a module-level docstring: entities are immutable because current
state is derived from an append-only event log, never mutated in place.

### R2 — Enumerations

Define exactly these six enums, all subclassing `enum.StrEnum` (Python 3.12), with exactly
these members and these string values. Do not add members, aliases or helper methods.

```python
class CategoriaAnimal(StrEnum):
    BEZERRO = "bezerro"
    NOVILHO = "novilho"
    ADULTO = "adulto"


class QualidadeBase(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class Confianca(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class StatusManejo(StrEnum):
    RECOMENDADO = "recomendado"
    CONFIRMADO = "confirmado"
    RECUSADO = "recusado"
    DIVERGENTE = "divergente"


class OrigemEvento(StrEnum):
    PRODUTOR = "produtor"
    SISTEMA = "sistema"
    SATELITE = "satelite"
    SAR_INFERIDO = "sar_inferido"


class TipoEvento(StrEnum):
    PIQUETE_CRIADO = "piquete_criado"
    PIQUETE_ALTERADO = "piquete_alterado"
    LOTE_CRIADO = "lote_criado"
    LOTE_ALTERADO = "lote_alterado"
    LOTE_DISSOLVIDO = "lote_dissolvido"
    MANEJO_RECOMENDADO = "manejo_recomendado"
    MANEJO_CONFIRMADO = "manejo_confirmado"
    MANEJO_RECUSADO = "manejo_recusado"
    MANEJO_DIVERGENTE = "manejo_divergente"
    LEITURA_SATELITE = "leitura_satelite"
    FOTO_VALIDACAO = "foto_validacao"
    PARAMETRO_ALTERADO = "parametro_alterado"
```

`Confianca` and `QualidadeBase` have identical members on purpose — they are different
concepts (estimate reliability vs. nutritional quality tier) and must stay separate types.

### R3 — `Fazenda`

```python
@dataclass(frozen=True, slots=True)
class Fazenda:
    id: UUID
    nome: str
    timezone: str                                  # IANA name, e.g. "America/Fortaleza"
    funcionarios_disponiveis: int
    manejos_por_funcionario_dia: int
    dias_preferenciais_manejo: tuple[int, ...]     # weekday numbers, Monday=0 .. Sunday=6
    ativo: bool = True
```

`dias_preferenciais_manejo` is a `tuple`, not a `list`, because frozen dataclasses must
hold immutable collections. Apply the same rule everywhere in this file.

### R4 — `Cultivar`

Every management parameter is an **explicit typed field with no default value**. Do not
invent numbers and do not provide fallbacks — the caller must supply every value.

```python
@dataclass(frozen=True, slots=True)
class Cultivar:
    id: UUID
    slug: str                          # stable machine key, e.g. "mombaca"
    nome: str                          # display name, e.g. "Mombaça"
    altura_entrada_cm: float
    altura_saida_cm: float
    densidade_kg_ha_por_cm: float
    temperatura_base_c: float
    rue_max_g_por_mj: float
    qualidade_base: QualidadeBase
```

### R5 — `Piquete`

```python
@dataclass(frozen=True, slots=True)
class Piquete:
    id: UUID
    fazenda_id: UUID
    nome: str
    area_ha: float
    cultivar_id: UUID
    geometria_geojson: dict[str, Any] | None = None
    ativo: bool = True
```

`geometria_geojson` is an **opaque payload**. This module must not parse it, validate it,
compute area from it, or import any geometry library. Area is carried separately in
`area_ha` because that is the only spatial value the pure calculation layer consumes.

Because the field holds a `dict`, `Piquete` instances are compared by value but must not
be used as dictionary keys or placed in sets. Do not write a custom `__hash__`.

### R6 — `ComposicaoLote` and `Lote`

A `lote` is described by how many animals of each category it contains. Do not model
individual animals — the system never tracks them.

```python
@dataclass(frozen=True, slots=True)
class ComposicaoLote:
    categoria: CategoriaAnimal
    n_animais: int
    peso_medio_kg: float


@dataclass(frozen=True, slots=True)
class Lote:
    id: UUID
    fazenda_id: UUID
    nome: str
    composicao: tuple[ComposicaoLote, ...]
    indissoluvel: bool = False
    ativo: bool = True
```

`indissoluvel` marks a `lote` that must never be split up between other groups.

Do **not** add a total-live-weight property, an animal-unit conversion, or any other
derived value to `Lote`. Those calculations belong to a different module.

### R7 — `Manejo`

`Manejo` is a **read model**: a convenience projection of what the event log already
contains. Nothing in this module writes it and nothing treats it as the source of truth.
State that in its docstring.

```python
@dataclass(frozen=True, slots=True)
class Manejo:
    id: UUID
    fazenda_id: UUID
    lote_id: UUID
    piquete_destino_id: UUID
    data_prevista: date
    dias_previstos: int
    motivo: str                      # human-readable text in Portuguese, shown to the farmer
    confianca: Confianca
    status: StatusManejo
    origem: OrigemEvento
    piquete_origem_id: UUID | None = None
    data_execucao: date | None = None
```

`piquete_origem_id` is `None` when a `lote` enters the rotation for the first time.
`data_execucao` is `None` until the movement is confirmed as done.

### R8 — `Evento`

Mirrors the append-only event log row exactly.

```python
@dataclass(frozen=True, slots=True)
class Evento:
    id: UUID
    fazenda_id: UUID
    tipo: TipoEvento
    ocorrido_em: datetime            # when it happened in the real world
    registrado_em: datetime          # when the system learned about it
    payload: dict[str, Any]
    origem: OrigemEvento
```

`payload` is an opaque dictionary. Do not validate its shape per event type, do not define
per-type payload classes, and do not write serialisation code.

### R9 — Declaration order

Declare in this order so the file reads top-down with no forward references: enums (R2),
`Fazenda`, `Cultivar`, `Piquete`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento`.

## Constants and parameters

**This spec defines no constants.** No numeric literal may appear in
`seugado/core/models.py` except the default values `True` / `False` / `None` shown above.
No field may have a numeric default. Agronomic values live outside this file and are
supplied by the caller.

## Validation rules

**None.** This module performs no validation whatsoever.

Specifically: do not raise on a negative `area_ha`, on an empty `composicao`, on
`altura_saida_cm` greater than `altura_entrada_cm`, or on any other inconsistency. Do not
add `__post_init__` to any class. Business-rule validation is a separate, later module,
and duplicating it here would create two places where a rule can disagree with itself.

## Acceptance criteria

- [ ] `seugado/core/models.py` exists and imports only from `dataclasses`, `datetime`,
      `enum`, `typing`, `uuid`
- [ ] The module defines exactly these names: `CategoriaAnimal`, `QualidadeBase`,
      `Confianca`, `StatusManejo`, `OrigemEvento`, `TipoEvento`, `Fazenda`, `Cultivar`,
      `Piquete`, `ComposicaoLote`, `Lote`, `Manejo`, `Evento` — and nothing else
- [ ] All six enums subclass `enum.StrEnum` and have exactly the members listed in R2
- [ ] `TipoEvento` has exactly 12 members
- [ ] Every one of the seven dataclasses is declared `@dataclass(frozen=True, slots=True)`
- [ ] Every field on every dataclass has a type hint
- [ ] No class defines `__post_init__`, `__hash__`, or any method other than what
      `@dataclass` generates
- [ ] No numeric literal appears anywhere in the module
- [ ] No field of any dataclass is typed `list` or `set`
- [ ] Assigning to any field of any instance raises `dataclasses.FrozenInstanceError`
- [ ] `pytest tests/core/test_models.py` passes with zero failures
- [ ] No dependency is added to `pyproject.toml`
- [ ] `seugado/core/__init__.py` is empty

## Test data

Every number below is an **arbitrary fixture value chosen to make the test readable**. It
is not agronomic data and must never be copied into the module as a default, a constant or
a docstring example.

```python
import uuid
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone

import pytest

from seugado.core.models import (
    CategoriaAnimal, Confianca, ComposicaoLote, Cultivar, Evento, Fazenda,
    Lote, Manejo, OrigemEvento, Piquete, QualidadeBase, StatusManejo, TipoEvento,
)

FAZENDA_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CULTIVAR_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PIQUETE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
LOTE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def test_cultivar_carries_every_parameter_explicitly():
    c = Cultivar(
        id=CULTIVAR_ID,
        slug="fixture-grass",
        nome="Fixture Grass",
        altura_entrada_cm=1.0,
        altura_saida_cm=1.0,
        densidade_kg_ha_por_cm=1.0,
        temperatura_base_c=1.0,
        rue_max_g_por_mj=1.0,
        qualidade_base=QualidadeBase.ALTA,
    )
    assert c.slug == "fixture-grass"
    assert c.qualidade_base == "alta"          # StrEnum compares equal to its value


def test_entities_are_frozen():
    p = Piquete(
        id=PIQUETE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Piquete 7",
        area_ha=1.0,
        cultivar_id=CULTIVAR_ID,
    )
    with pytest.raises(FrozenInstanceError):
        p.area_ha = 2.0


def test_piquete_geometry_is_opaque_and_optional():
    p = Piquete(
        id=PIQUETE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Piquete 7",
        area_ha=1.0,
        cultivar_id=CULTIVAR_ID,
        geometria_geojson={"type": "Polygon", "coordinates": []},
    )
    assert p.geometria_geojson["type"] == "Polygon"
    assert Piquete(
        id=PIQUETE_ID, fazenda_id=FAZENDA_ID, nome="x",
        area_ha=1.0, cultivar_id=CULTIVAR_ID,
    ).geometria_geojson is None


def test_lote_holds_composition_as_tuple():
    lote = Lote(
        id=LOTE_ID,
        fazenda_id=FAZENDA_ID,
        nome="Lote A",
        composicao=(
            ComposicaoLote(categoria=CategoriaAnimal.BEZERRO, n_animais=3, peso_medio_kg=1.0),
            ComposicaoLote(categoria=CategoriaAnimal.ADULTO, n_animais=20, peso_medio_kg=1.0),
        ),
    )
    assert isinstance(lote.composicao, tuple)
    assert len(lote.composicao) == 2
    assert lote.indissoluvel is False
    assert not hasattr(lote, "peso_vivo_total_kg")     # derived values live elsewhere


def test_manejo_allows_first_entry_and_pending_execution():
    m = Manejo(
        id=uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        lote_id=LOTE_ID,
        piquete_destino_id=PIQUETE_ID,
        data_prevista=date(2026, 3, 12),
        dias_previstos=2,
        motivo="Piquete 7 atingiu a altura de entrada.",
        confianca=Confianca.ALTA,
        status=StatusManejo.RECOMENDADO,
        origem=OrigemEvento.SISTEMA,
    )
    assert m.piquete_origem_id is None
    assert m.data_execucao is None


def test_evento_payload_is_opaque():
    e = Evento(
        id=uuid.uuid4(),
        fazenda_id=FAZENDA_ID,
        tipo=TipoEvento.LEITURA_SATELITE,
        ocorrido_em=datetime(2026, 3, 12, 9, 0, tzinfo=timezone.utc),
        registrado_em=datetime(2026, 3, 12, 9, 5, tzinfo=timezone.utc),
        payload={"anything": [1, 2, 3]},
        origem=OrigemEvento.SATELITE,
    )
    assert e.payload["anything"] == [1, 2, 3]
    assert e.ocorrido_em < e.registrado_em


def test_tipo_evento_has_twelve_members():
    assert len(list(TipoEvento)) == 12


def test_fazenda_preferred_days_are_immutable():
    f = Fazenda(
        id=FAZENDA_ID,
        nome="Fazenda Fixture",
        timezone="America/Fortaleza",
        funcionarios_disponiveis=1,
        manejos_por_funcionario_dia=1,
        dias_preferenciais_manejo=(0, 2, 4),
    )
    assert isinstance(f.dias_preferenciais_manejo, tuple)
```

## Out of scope

- Do NOT add any calculation: no live-weight totals, no animal-unit conversion, no
  height-to-mass conversion, no stocking rate, no occupation days
- Do NOT add validation, `__post_init__`, or any raised exception
- Do NOT add database access, ORM models, migrations, or table definitions
- Do NOT add Pydantic models, JSON encoders/decoders, `to_dict`/`from_dict`, or any
  serialisation helper
- Do NOT import or use `shapely`, `geopandas`, or any geometry library; do NOT parse,
  validate or transform `geometria_geojson`
- Do NOT add HTTP endpoints, CLI entry points or configuration loading
- Do NOT add logging, caching, dependency injection, decorators or metaclasses
- Do NOT define abstract base classes, protocols, mixins or inheritance between entities
- Do NOT add default values beyond the `True` / `False` / `None` defaults shown above
- Do NOT add convenience constructors, factory functions or builders
- Do NOT add a `Modulo` entity (a group of paddocks one lote rotates through); it is
  deliberately not modelled
- Do NOT re-export anything from `seugado/core/__init__.py`

## Style constraints

- Python 3.12, type hints on every field and every public function
- Pure data only: no I/O, no global state, no side effects
- Variable and field names carry their unit: `massa_kg_ms_ha`, not `massa`; `area_ha`,
  not `area`
- Domain nouns stay in Portuguese: `piquete`, `lote`, `cultivar`, `manejo`, `fazenda`
- Docstrings and comments in English
- Prefer functions over classes; no abstraction without a second use case
- Maximum 300 lines for `seugado/core/models.py`
