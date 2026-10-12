# SPEC-018 — Module and feeding square in the projected state, and walking distance via the square

## Context
The planner decides which cattle group moves to which paddock. On real farms each group rotates
only inside its grazing module, and cattle walk from a paddock to a shared feeding square and
from there to the next paddock — not in a straight line between paddock centres. This spec
(1) loads each paddock's module and feeding square, and each group's module, into the projected
state the planner receives, (2) adds a pure function for the walking distance through the
feeding squares, and (3) adds a pure function that lists the candidate destination paddocks of
a group. The module and feeding-square tables already exist in the database (see R3).

## Domain vocabulary
- `piquete` — fenced paddock. `lote` — cattle group managed as one unit.
- `modulo` — grazing module: a group of paddocks; a group bound to a module only moves inside it.
- `praca` — feeding square: the point where cattle drink and eat; each paddock may point to one.
- `centroide` — geometric centre of a paddock polygon (already in `PiqueteProjetado`).
- `EstadoProjetado`, `PiqueteProjetado`, `LoteProjetado` — existing contracts in
  `src/seugado/contratos.py` describing the farm the planner works on.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- MODIFY `src/seugado/contratos.py`
- CREATE `src/seugado/planner/estrutura.py`
- MODIFY `src/seugado/planner/carga.py`
- CREATE `tests/planner/test_estrutura.py`
- MODIFY or CREATE the existing contract tests only to add the cases of R1

## Requirements

### R1 — New contract fields, appended with defaults (`contratos.py`)
Append, **at the end** of the field list and in this order:

```python
@dataclass(frozen=True, slots=True)
class PiqueteProjetado:
    ...                                  # all existing fields unchanged, same order
    modulo_id: UUID | None = None
    praca_id: UUID | None = None
    praca_lat: float | None = None
    praca_lon: float | None = None

@dataclass(frozen=True, slots=True)
class LoteProjetado:
    ...                                  # all existing fields unchanged, same order
    modulo_id: UUID | None = None
```

Change `_deserialize` so that, for a dataclass, a key **missing** from the mapping is filled
with the field's default when the field has one (`field.default` or `field.default_factory`),
and still raises `ValueError("missing key: '<name>'")` when it has none. Serialization is
unchanged: new fields are always written. Effect: JSON written before this spec still loads.
No other field, class, enum or function in `contratos.py` changes.

### R2 — Pure functions in `planner/estrutura.py`
No I/O, no database, no network. Imports allowed: `math`, `uuid`, `seugado.contratos`.

```python
RAIO_TERRA_M = 6_371_008.8

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points given in degrees."""

def ponto_acesso(piquete: PiqueteProjetado) -> tuple[float, float]:
    """(lat, lon) where cattle leave/enter the paddock: its feeding square, else its centroid."""

def distancia_manejo_m(origem: PiqueteProjetado, destino: PiqueteProjetado) -> float:
    """Walking distance in metres from origem to destino through the feeding squares."""

def piquetes_candidatos(
    estado: EstadoProjetado, lote: LoteProjetado
) -> tuple[PiqueteProjetado, ...]:
    """Paddocks the lote may be sent to, in the order they appear in estado.piquetes."""
```

Formulas:
```
haversine: a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2);  d = 2·R·asin(√a)   (radians)

acesso(p) = (p.praca_lat, p.praca_lon) if p has a feeding square else (p.centroide_lat, p.centroide_lon)

distancia_manejo_m(o, d) = 0.0                                   if o.piquete_id == d.piquete_id
                         = hav(centroide_o, acesso_o)
                         + hav(acesso_o, acesso_d)
                         + hav(acesso_d, centroide_d)            otherwise
```
Consequences the code must reproduce: same feeding square → paddock→square + square→paddock;
different squares → the straight segment between the two squares is added; no squares at all →
exactly the straight distance between centroids.

`piquetes_candidatos`: if `lote.modulo_id is None`, return every paddock of `estado.piquetes`;
otherwise return only those whose `modulo_id == lote.modulo_id`. Do not filter by height,
rest, occupation or anything else — that is the optimizer's job.

### R3 — Load the structure in `planner/carga.py`
In `montar_estado_projetado`, after `projetar_estado(...)` returns, read the farm's structure and
return a copy of the state with the new fields filled using `dataclasses.replace`. Do not change
`planner/estado.py` and do not change the signature of `montar_estado_projetado`.

```sql
-- paddocks
SELECT pe.piquete_id, pe.modulo_id, pe.praca_id, ST_Y(pr.ponto), ST_X(pr.ponto)
FROM piquete_estrutura pe LEFT JOIN praca pr ON pr.id = pe.praca_id
WHERE pe.fazenda_id = %s
-- cattle groups
SELECT lote_id, modulo_id FROM lote_modulo WHERE fazenda_id = %s
```
Tables (already created by migration `0004`, do not create them):
`piquete_estrutura (piquete_id, fazenda_id, modulo_id NULL, praca_id NULL)`,
`praca (id, fazenda_id, nome, ponto geometry(Point,4326))`,
`lote_modulo (lote_id, fazenda_id, modulo_id NOT NULL)`.
`ST_Y` is latitude, `ST_X` is longitude. A paddock or group without a row keeps all new fields
`None`. Rows for paddocks or groups not present in the projected state are ignored. The empty
state (`_vazio`) is unchanged.

## Constants and parameters

| Name | Value | Unit | Source |
|---|---|---|---|
| `RAIO_TERRA_M` | 6 371 008.8 | m | IUGG mean Earth radius of GRS80 (Moritz 2000, *Journal of Geodesy* 74:128–133) |

## Validation rules
- `ponto_acesso` raises `ValueError` when exactly one of `praca_lat` / `praca_lon` is `None`.
- `haversine_m` raises `ValueError` when a latitude is outside `[-90, 90]` or a longitude is
  outside `[-180, 180]`.
- `distancia_manejo_m` never returns a negative number; it returns `0.0` for the same paddock.

## Testing — who does what
Write your own tests in `tests/planner/` (and the contract test file for R1), as a smoke check
that your code runs and behaves as described. Keep them short. You will NOT be given a test file
to copy, and you must not wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] The five new fields exist at the end of `PiqueteProjetado` / `LoteProjetado`, default `None`
- [ ] `plano_de_dict` / `estado_de_dict` load JSON that lacks the new keys
- [ ] A key missing for a field WITHOUT default still raises `ValueError("missing key: ...")`
- [ ] `planner/estrutura.py` exposes exactly `RAIO_TERRA_M`, `haversine_m`, `ponto_acesso`,
      `distancia_manejo_m`, `piquetes_candidatos`, and imports nothing outside R2's list
- [ ] Worked example returns 220.83 m (± 0.5 m) and 156.16 m (± 0.5 m) without the square
- [ ] `montar_estado_projetado` fills the new fields from the database; `estado.py` untouched
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run --env-file .env pytest` pass
- [ ] No new dependency in `pyproject.toml`

## Worked example
Feeding square P at lat −9.6000, lon −36.0000. Paddock A has centroid (−9.6010, −36.0000) and
paddock B has centroid (−9.6000, −36.0010); both point to P. Then
`distancia_manejo_m(A, B) = hav(A, P) + 0 + hav(P, B) ≈ 111.19 + 109.64 ≈ 220.83 m`.
If neither paddock had a feeding square, the result would be the straight centroid distance,
≈ 156.16 m. A group with `modulo_id = M1` gets as candidates only the paddocks with
`modulo_id = M1`; a group with `modulo_id = None` gets every paddock.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-018.md`.

## Out of scope
- Do NOT change `planner/otimizador.py`, `planner/estado.py` or `planner/estado_util.py`
- Do NOT create the database tables or any migration
- Do NOT add registration functions or API routes for modules or feeding squares
- Do NOT add corridors, gate graphs, shortest paths or PostGIS distance queries
- Do NOT add a `piquete_distancia` table or any cache
- Do NOT change `Alerta`, `Movimentacao`, `PlanoManejo` or `TipoAlerta`
- Do NOT reorder or rename any existing contract field
- Do NOT add frontend code

## Style constraints
- Python 3.12, type hints on every public function
- `planner/estrutura.py`: pure functions only, no I/O, no global state besides the constant
- Variable names carry their unit: `distancia_m`, `lat`, `lon` in degrees
- Domain nouns stay in Portuguese: `piquete`, `lote`, `modulo`, `praca`
- Docstrings and comments in English
- Never use an entity as a dictionary key; use its id
- `__init__.py` files stay empty; import from the concrete module
- Maximum 300 lines per file
