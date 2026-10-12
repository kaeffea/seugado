# SPEC-017 — Grazing modules and feeding squares: schema, registration and API

## Context
On real farms, paddocks are grouped into grazing modules, and each cattle group rotates only
inside its module. The cattle walk to a shared feeding square (water trough and feed bunk) and
back. The admin team must be able to register modules and feeding squares, say which module and
which feeding square each paddock belongs to, bind each cattle group to a module, and see the
stocking rate of each module. This is farm configuration, edited in place with `UPDATE`; it is
NOT recorded in the append-only event log, and nothing in the event log changes.

## Domain vocabulary
- `fazenda` — farm. `piquete` — fenced paddock. `lote` — cattle group managed as one unit.
- `modulo` — grazing module: a named group of paddocks inside one farm.
- `praca` — feeding square: a named point of the farm where cattle drink and eat from a bunk.
- `piquete_estrutura` — for one paddock: its module (optional) and its feeding square (optional).
- `lote_modulo` — the module a cattle group is bound to. No row = group has no module.
- `UA` (unidade animal) — animal unit = 450 kg of live weight.
- `lotacao_ua_ha` — stocking rate: animal units per hectare.
- `estado_piquete`, `estado_lote` — existing derived tables holding the current paddocks and
  cattle groups of each farm (read only in this spec).

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read, without modifying, `src/seugado/cadastro/clientes.py`,
`src/seugado/api/rotas_fazenda.py` and `src/seugado/api/rotas_piquetes.py` as style references
for a registration module and its routes.

## Files to create or modify
- CREATE `db/migrations/0004_modulo_praca.sql`
- CREATE `src/seugado/cadastro/estrutura.py`
- CREATE `src/seugado/api/rotas_estrutura.py`
- MODIFY `src/seugado/api/main.py` — import `rotas_estrutura` and add
  `app.include_router(rotas_estrutura.router)`; nothing else changes
- CREATE `tests/cadastro/test_estrutura.py`
- CREATE `tests/api/test_rotas_estrutura.py`

## Requirements

### R1 — `db/migrations/0004_modulo_praca.sql` (one transaction)
```sql
BEGIN;

CREATE TABLE modulo (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    nome       TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fazenda_id, nome)
);

CREATE TABLE praca (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    nome       TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    ponto      geometry(Point, 4326) NOT NULL,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fazenda_id, nome)
);

CREATE TABLE piquete_estrutura (
    piquete_id UUID PRIMARY KEY,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    modulo_id  UUID REFERENCES modulo(id) ON DELETE RESTRICT,
    praca_id   UUID REFERENCES praca(id) ON DELETE RESTRICT,
    CHECK (modulo_id IS NOT NULL OR praca_id IS NOT NULL)
);
CREATE INDEX piquete_estrutura_fazenda_idx ON piquete_estrutura (fazenda_id);

CREATE TABLE lote_modulo (
    lote_id    UUID PRIMARY KEY,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    modulo_id  UUID NOT NULL REFERENCES modulo(id) ON DELETE RESTRICT
);
CREATE INDEX lote_modulo_fazenda_idx ON lote_modulo (fazenda_id);

ALTER TABLE modulo ENABLE ROW LEVEL SECURITY;
ALTER TABLE praca ENABLE ROW LEVEL SECURITY;
ALTER TABLE piquete_estrutura ENABLE ROW LEVEL SECURITY;
ALTER TABLE lote_modulo ENABLE ROW LEVEL SECURITY;

COMMIT;
```
`piquete_id` and `lote_id` have no foreign key on purpose: paddocks and cattle groups live in
the event log, and their current rows live in derived tables that are rebuilt by
`DELETE` + `INSERT`. Ownership is checked in Python (R4, R5).

### R2 — Pydantic models in `cadastro/estrutura.py`
```python
class ModuloIn(BaseModel):
    nome: str = Field(..., min_length=1)

class ModuloOut(BaseModel):
    id: UUID
    nome: str
    piquete_ids: list[UUID]        # active paddocks of the module, ordered by paddock name
    lote_ids: list[UUID]           # cattle groups bound to the module, ordered by group name
    area_ha: float                 # sum of area_ha of the active paddocks of the module
    ua_total: float                # sum of peso_vivo_total_kg of its groups / UNIDADE_ANIMAL_KG
    lotacao_ua_ha: float | None    # ua_total / area_ha; None when area_ha == 0

class PracaIn(BaseModel):
    nome: str = Field(..., min_length=1)
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class PracaOut(PracaIn):
    id: UUID

class EstruturaPiqueteIn(BaseModel):
    modulo_id: UUID | None = None
    praca_id: UUID | None = None

class EstruturaPiqueteOut(BaseModel):
    piquete_id: UUID
    modulo_id: UUID | None
    praca_id: UUID | None

class LoteModuloIn(BaseModel):
    modulo_id: UUID | None = None

class LoteModuloOut(BaseModel):
    lote_id: UUID
    modulo_id: UUID | None

class EstruturaFazendaOut(BaseModel):
    piquetes: list[EstruturaPiqueteOut]   # one entry per ACTIVE paddock, ordered by name;
                                          # paddocks without a row get None, None
    lotes: list[LoteModuloOut]            # one entry per cattle group in estado_lote, by name
```
`UNIDADE_ANIMAL_KG` is imported from `seugado.planner.estado`; do not define a second copy.
`lat`/`lon` are stored as `ST_SetSRID(ST_MakePoint(lon, lat), 4326)` and read back with
`ST_Y(ponto)` / `ST_X(ponto)` (note the order: X is longitude).

### R3 — Module and feeding-square functions
Every function takes `conn: psycopg.Connection[Any]` first and `fazenda_id: UUID` second, never
commits, and only touches rows of that `fazenda_id`.

```python
def listar_modulos(conn, fazenda_id) -> list[ModuloOut]          # ordered by nome
def criar_modulo(conn, fazenda_id, dados: ModuloIn) -> ModuloOut
def renomear_modulo(conn, fazenda_id, modulo_id: UUID, dados: ModuloIn) -> ModuloOut
def excluir_modulo(conn, fazenda_id, modulo_id: UUID) -> None
def listar_pracas(conn, fazenda_id) -> list[PracaOut]            # ordered by nome
def criar_praca(conn, fazenda_id, dados: PracaIn) -> PracaOut
def editar_praca(conn, fazenda_id, praca_id: UUID, dados: PracaIn) -> PracaOut
def excluir_praca(conn, fazenda_id, praca_id: UUID) -> None
```
- Duplicate `nome` in the same farm → `ValueError("Já existe um módulo com esse nome")` /
  `ValueError("Já existe uma praça com esse nome")`. Check before inserting; do not rely on
  catching the database error.
- Unknown id, or id of another farm → `LookupError("Módulo não encontrado")` /
  `LookupError("Praça não encontrada")`.
- `excluir_modulo` when any `piquete_estrutura` or `lote_modulo` row points to it →
  `EmUsoError("Módulo em uso: desvincule piquetes e lotes antes")`. Same for `excluir_praca`
  with `piquete_estrutura` → `EmUsoError("Praça em uso: desvincule os piquetes antes")`.
  `EmUsoError` is a new `Exception` subclass defined in this module.
- `ModuloOut` counts only paddocks present in `estado_piquete` with `ativo = TRUE`, and only
  groups present in `estado_lote`.

### R4 — Paddock structure
```python
def definir_estrutura_piquete(
    conn, fazenda_id, piquete_id: UUID, dados: EstruturaPiqueteIn
) -> EstruturaPiqueteOut
def obter_estrutura(conn, fazenda_id) -> EstruturaFazendaOut
```
- Paddock not in `estado_piquete` for this farm with `ativo = TRUE` →
  `LookupError("Piquete não encontrado")`.
- `modulo_id` / `praca_id` not belonging to this farm → `ValueError("Módulo de outra fazenda ou
  inexistente")` / `ValueError("Praça de outra fazenda ou inexistente")`.
- Both `None` → delete the paddock's row (if any) and return `None, None`.
- Otherwise upsert (`INSERT ... ON CONFLICT (piquete_id) DO UPDATE`).

### R5 — Cattle group module
```python
def definir_modulo_lote(conn, fazenda_id, lote_id: UUID, dados: LoteModuloIn) -> LoteModuloOut
```
- Group not in `estado_lote` for this farm → `LookupError("Lote não encontrado")`.
- `modulo_id` of another farm or unknown → `ValueError("Módulo de outra fazenda ou inexistente")`.
- `modulo_id = None` → delete the row (if any). Otherwise upsert.
- Do NOT check where the group currently is: a group may be bound to a module while it still
  stands on a paddock of another module; the planner moves it later.

### R6 — Routes in `api/rotas_estrutura.py`
`router = APIRouter(tags=["estrutura"])`. Every route uses the existing `FazendaAutorizada`
(from `seugado.api.auth`) and `Conexao` (from `seugado.api.deps`) dependencies, commits on
success and rolls back on error. Error mapping: `LookupError` → 404, `ValueError` or
`pydantic.ValidationError` → 400, `EmUsoError` → 409, always with `detail=str(error)`.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/fazendas/{fazenda_id}/modulos` | — | `list[ModuloOut]` |
| POST | `/fazendas/{fazenda_id}/modulos` | `ModuloIn` | `ModuloOut`, 201 |
| PUT | `/fazendas/{fazenda_id}/modulos/{modulo_id}` | `ModuloIn` | `ModuloOut` |
| DELETE | `/fazendas/{fazenda_id}/modulos/{modulo_id}` | — | 204 |
| GET | `/fazendas/{fazenda_id}/pracas` | — | `list[PracaOut]` |
| POST | `/fazendas/{fazenda_id}/pracas` | `PracaIn` | `PracaOut`, 201 |
| PUT | `/fazendas/{fazenda_id}/pracas/{praca_id}` | `PracaIn` | `PracaOut` |
| DELETE | `/fazendas/{fazenda_id}/pracas/{praca_id}` | — | 204 |
| GET | `/fazendas/{fazenda_id}/estrutura` | — | `EstruturaFazendaOut` |
| PUT | `/fazendas/{fazenda_id}/piquetes/{piquete_id}/estrutura` | `EstruturaPiqueteIn` | `EstruturaPiqueteOut` |
| PUT | `/fazendas/{fazenda_id}/lotes/{lote_id}/modulo` | `LoteModuloIn` | `LoteModuloOut` |

## Constants and parameters

| Name | Value | Unit | Source |
|---|---|---|---|
| `UNIDADE_ANIMAL_KG` | 450 | kg | Existing constant in `seugado.planner.estado` (industry animal unit) |

## Validation rules
- Empty or whitespace-only `nome` → rejected (Pydantic `min_length`, plus the SQL `CHECK`).
- `lat` outside `[-90, 90]` or `lon` outside `[-180, 180]` → `ValidationError` (HTTP 422 from
  FastAPI body validation, or 400 when raised inside the route).
- Never return a row, module or feeding square that belongs to another farm.

## Testing — who does what
Write your own tests in `tests/cadastro/` and `tests/api/`, as a smoke check that your code runs
and behaves as described. Keep them short. Tests that need the database must use the same
skip mechanism the existing database tests in those folders use. You will NOT be given a test
file to copy, and you must not wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `0004_modulo_praca.sql` applies cleanly after `0003` and creates the four tables with RLS
- [ ] All functions of R3–R5 exist with the exact names and parameter order above
- [ ] `EmUsoError` exists and maps to HTTP 409
- [ ] The 11 routes of R6 exist with the listed methods, paths and status codes
- [ ] No module, feeding square or link of another farm is ever read or written
- [ ] `ModuloOut` of the worked example returns `area_ha = 15.0`, `ua_total = 36.0`,
      `lotacao_ua_ha = 2.4`
- [ ] No event is written to the `evento` table by any function of this spec
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run --env-file .env pytest` pass
- [ ] No new dependency in `pyproject.toml`; `cadastro/estrutura.py` ≤ 300 lines

## Worked example
Farm with active paddocks "P1" (10.0 ha) and "P2" (5.0 ha) and one cattle group "Engorda" of
30 `boi` at 540 kg (`peso_vivo_total_kg = 16200`). Create module "Módulo A", set the structure
of P1 and P2 to that module, bind "Engorda" to it. `listar_modulos` returns one module with
`piquete_ids = [P1, P2]`, `lote_ids = [Engorda]`, `area_ha = 15.0`,
`ua_total = 16200 / 450 = 36.0` and `lotacao_ua_ha = 36.0 / 15.0 = 2.4`. Deleting "Módulo A"
now raises `EmUsoError`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-017.md`.

## Out of scope
- Do NOT add event types, event payloads or anything in `persistencia/eventos.py` or `core/`
- Do NOT change `cadastro/piquetes.py`, `cadastro/lotes.py` or their routes
- Do NOT touch the planner, the optimizer, the bot or `contratos.py`
- Do NOT add corridors, paths between paddocks or any distance calculation
- Do NOT add frontend code
- Do NOT add a foreign key from `piquete_estrutura` / `lote_modulo` to derived tables
- Do NOT enforce that a cattle group stands on a paddock of its module
- Do NOT add soft delete (`ativo`) to modules or feeding squares

## Style constraints
- Python 3.12, type hints on every public function
- Variable names carry their unit: `area_ha`, `peso_vivo_total_kg`
- Domain nouns stay in Portuguese: `modulo`, `praca`, `piquete`, `lote`, `fazenda`
- Docstrings and comments in English; error messages shown to the admin in Portuguese
- Prefer functions over classes (Pydantic models and `EmUsoError` are the only classes)
- `__init__.py` files stay empty; import from the concrete module
- Maximum 300 lines per file
