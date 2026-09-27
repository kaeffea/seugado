# SPEC-015 — Admin-only operation, farm schedule, labour in animals and sex-aware categories

## Context
In the first product version the farmer never uses the web app: the team (admins) registers
clients, farms, paddocks and cattle groups, and the farmer only talks to a Telegram bot. The
farm also stores how many animals each worker can move per day (not how many groups) and on
which weekday and hour the farmer wants to receive the weekly plan. Animal categories now
distinguish sex. Plans get a status, because a newer "candidate" plan can be offered to the
farmer and accepted or rejected. This spec changes the schema, the domain model, the event
payload, the planner constants, the API authorisation and the shared contracts accordingly.

## Domain vocabulary
- `cliente` — the farmer (a person). `fazenda` — farm. `lote` — cattle group.
- `animais_por_funcionario_dia` — how many animals one worker can move in one day.
- `envio_plano_dia` / `envio_plano_hora` — weekday (0 = Monday … 6 = Sunday) and hour (0–23,
  farm's local time) when the weekly plan is sent.
- `plano` status: `vigente` (the plan the farmer is following), `candidato` (a newer plan
  offered to the farmer), `substituido` (a former `vigente`), `descartado` (a rejected or
  superseded `candidato`).
- Categories: `bezerro` (male calf), `bezerra` (female calf), `novilho` (young male),
  `novilha` (young female), `vaca` (cow), `boi` (steer/ox), `touro` (bull).

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- CREATE `db/migrations/0003_admin_agenda.sql`
- MODIFY `src/seugado/core/models.py`
- MODIFY `src/seugado/persistencia/eventos.py`
- MODIFY `src/seugado/planner/estado.py`
- MODIFY `src/seugado/api/auth.py`
- MODIFY `src/seugado/contratos.py`
- MODIFY tests under `tests/core/`, `tests/persistencia/`, `tests/planner/`, `tests/api/` that
  use the changed names (only where these requirements change their behaviour)

## Requirements

### R1 — `db/migrations/0003_admin_agenda.sql` (one transaction)
```sql
BEGIN;

CREATE TABLE cliente (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    telefone    TEXT,
    observacoes TEXT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE cliente ENABLE ROW LEVEL SECURITY;

ALTER TABLE fazenda ADD COLUMN cliente_id UUID REFERENCES cliente(id);
ALTER TABLE fazenda RENAME COLUMN manejos_por_funcionario_dia TO animais_por_funcionario_dia;
ALTER TABLE fazenda
    ADD COLUMN envio_plano_dia SMALLINT NOT NULL DEFAULT 0
        CHECK (envio_plano_dia BETWEEN 0 AND 6),
    ADD COLUMN envio_plano_hora SMALLINT NOT NULL DEFAULT 6
        CHECK (envio_plano_hora BETWEEN 0 AND 23),
    ADD COLUMN ultimo_envio_semanal DATE,
    ADD COLUMN ultima_rotina_diaria DATE;
CREATE UNIQUE INDEX fazenda_telegram_chat_idx
    ON fazenda (telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

ALTER TABLE plano ADD COLUMN status TEXT NOT NULL DEFAULT 'vigente'
    CHECK (status IN ('vigente', 'candidato', 'substituido', 'descartado'));
CREATE INDEX plano_fazenda_status_idx ON plano (fazenda_id, status, gerado_em DESC);

COMMIT;
```

### R2 — `models.py`
1. `CategoriaAnimal` has exactly these members, in this order:
   `BEZERRO="bezerro"`, `BEZERRA="bezerra"`, `NOVILHO="novilho"`, `NOVILHA="novilha"`,
   `VACA="vaca"`, `BOI="boi"`, `TOURO="touro"` (`ADULTO` is removed).
2. `Fazenda` fields, in this order: `id: UUID`, `nome: str`, `timezone: str`,
   `funcionarios_disponiveis: int`, `animais_por_funcionario_dia: int`,
   `dias_preferenciais_manejo: tuple[int, ...]`, `envio_plano_dia: int`,
   `envio_plano_hora: int`, `ativo: bool = True`. (`manejos_por_funcionario_dia` is removed.)

### R3 — `eventos.py`
`ComposicaoPayload.categoria` becomes
`Literal["bezerro", "bezerra", "novilho", "novilha", "vaca", "boi", "touro"]`. Nothing else
changes.

### R4 — `planner/estado.py` constants (functions unchanged)
```python
CONSUMO_FRACAO_PV = {BEZERRO: 0.024, BEZERRA: 0.024, NOVILHO: 0.022, NOVILHA: 0.022,
                     VACA: 0.024, BOI: 0.024, TOURO: 0.024}
UA_POR_CATEGORIA  = {BEZERRO: 0.25, BEZERRA: 0.25, NOVILHO: 0.75, NOVILHA: 0.75,
                     VACA: 1.00, BOI: 1.00, TOURO: 1.25}
```
(keys are `CategoriaAnimal` members.)

### R5 — `api/auth.py`: every logged-in user is an admin
`exigir_fazenda(fazenda_id, usuario, conn)` no longer compares with `fazenda_usuario`: it runs
`SELECT 1 FROM fazenda WHERE id = %s` and raises `HTTPException(404, "Fazenda não encontrada")`
when there is no row; otherwise returns `fazenda_id`. `usuario` stays a required dependency
(so anonymous calls still get 401). `fazenda_do_usuario` stays unchanged (unused).

### R6 — `contratos.py` additions
```python
class TipoAlerta(StrEnum):
    ...                                   # the 8 existing members, unchanged
    PASSANDO_DO_PONTO = "passando_do_ponto"

@dataclass(frozen=True, slots=True)
class PassoPlano:
    data: date
    piquete_destino_nome: str

@dataclass(frozen=True, slots=True)
class DiferencaLote:
    lote_id: UUID
    lote_nome: str
    antes: tuple[PassoPlano, ...]
    depois: tuple[PassoPlano, ...]
```
No serialisation functions are needed for the two new dataclasses. The existing JSON functions
must keep working (the new `TipoAlerta` value simply round-trips).

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Intake: calves / young / adults | 2.4 % / 2.2 % / 2.4 % of live weight | `05` (default 2.4 %; young stock 2.2 %; adult 2.4 %) |
| UA: calves / young / cow-steer / bull | 0.25 / 0.75 / 1.00 / 1.25 | `05`, UA table (Embrapa); young stock uses the 2–3-year row (ADR-024) |

Sex does not change the fallback weight (no source by sex); it only matters when the farmer
types the real weight (ADR-025).

## Validation rules
- `ComposicaoPayload` with `categoria="adulto"` now raises `ValidationError`.
- `exigir_fazenda` with an unknown farm id → 404; without a token → 401 (unchanged).

## Testing — who does what
Update your own tests in `tests/core/`, `tests/persistencia/`, `tests/planner/`, `tests/api/`
where the renamed field, the new categories or the new authorisation change behaviour. Keep
them short. Do not create, modify or delete anything under `tests/conformance/` (the tester
updates the conformance suites for the intentional changes).

## Acceptance criteria
- [ ] `0003_admin_agenda.sql` applies cleanly after `0002` on Supabase
- [ ] `CategoriaAnimal` has exactly the 7 members above; `Fazenda` has the exact field order
- [ ] `peso_por_ua_kg(CategoriaAnimal.TOURO) == 562.5`; `peso_por_ua_kg(NOVILHA) == 337.5`
- [ ] `exigir_fazenda` returns 404 for an unknown farm and the id for any existing farm
- [ ] `TipoAlerta` has 9 members; `PassoPlano` and `DiferencaLote` are frozen/slotted
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run --env-file .env pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
A lote of 30 `touro` without typed weight gets `peso_medio_kg = 1.25 × 450 = 562.5` and
intake `30 × 562.5 × 0.024 = 405.0` kg DM/day. A farm row created before this migration keeps
its old value under the new column name `animais_por_funcionario_dia`, and gets
`envio_plano_dia = 0` (Monday) and `envio_plano_hora = 6`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-015.md`.

## Out of scope
- Do NOT drop `fazenda_usuario` or any column other than the rename above
- Do NOT add endpoints (other owners write them)
- Do NOT change `projetar`, `registrar_evento`, `reconstruir_projecao` or the catalog
- Do NOT add admin roles or permission tables (every authenticated user is an admin in the MVP)
- Do NOT add new dependencies

## Style constraints
- Python 3.12, type hints on every public function; SQL with `%s` parameters
- Domain nouns stay in Portuguese; docstrings in English; `__init__.py` files stay empty
