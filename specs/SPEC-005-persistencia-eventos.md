# SPEC-005 — Event log: SQL migration and validated write gateway

## Context
This system stores every fact as an immutable event in one append-only table; current state is
derived elsewhere (a different module folds the log into state — you do not need to know how).
This spec creates the database schema for the event log and the **only** function allowed to
write to it, with structural validation of the payload for every event type before it reaches
the database.

## Domain vocabulary
- `evento` — an immutable fact: something that happened, stored append-only.
- `piquete` — a fenced paddock subdivision.
- `lote` — a group of cattle managed as one unit.
- `fazenda` — a farm; the top-level tenant.
- `chave_idempotencia` — a caller-supplied string that makes re-sending the same fact a no-op.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- CREATE `db/migrations/0001_evento_e_derivadas.sql`
- CREATE `src/seugado/persistencia/eventos.py`
- CREATE `tests/core/test_eventos.py`
- (never list `__init__.py`: packages stay empty — `06` §7 rule 10. Create the empty
  `src/seugado/persistencia/__init__.py` file with zero content, but do not add anything to it.)

## Requirements

### R1 — Migration file
Write plain SQL (no migration framework — decided in ADR-020). One file, applied top to bottom.
Structure, in order:

```sql
-- 1. Domain lookup tables (referenced by evento, never edited by app code at runtime)
CREATE TABLE tipo_evento (tipo TEXT PRIMARY KEY);
INSERT INTO tipo_evento (tipo) VALUES
    ('piquete_criado'), ('piquete_alterado'),
    ('lote_criado'), ('lote_alterado'), ('lote_dissolvido'),
    ('manejo_recomendado'), ('manejo_confirmado'), ('manejo_recusado'), ('manejo_divergente'),
    ('leitura_satelite'), ('foto_validacao'), ('parametro_alterado');

CREATE TABLE origem_evento (origem TEXT PRIMARY KEY);
INSERT INTO origem_evento (origem) VALUES
    ('produtor'), ('sistema'), ('satelite'), ('sar_inferido');

-- 2. fazenda (minimal — full shape is a different spec; only what evento's FK needs)
CREATE TABLE IF NOT EXISTS fazenda (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

-- 3. evento — copy this table verbatim from ADR-018 in docs/12, including both indexes,
--    the REVOKE line and the trigger. Do not alter column names, types or order.

-- 4. Derived tables (all carry derivado_ate_sequencia BIGINT NOT NULL and
--    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(); no other table writes to these):
CREATE TABLE estado_piquete (
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    piquete_id UUID NOT NULL,
    situacao TEXT NOT NULL,
    lote_atual_id UUID,
    desde DATE NOT NULL,
    dias_descanso INTEGER NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)
);

CREATE TABLE estado_lote (
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    lote_id UUID NOT NULL,
    piquete_atual_id UUID,
    desde DATE,
    peso_vivo_total_kg DOUBLE PRECISION NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, lote_id)
);

CREATE TABLE leitura (
    id UUID NOT NULL,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    piquete_id UUID NOT NULL,
    data DATE NOT NULL,
    ndvi DOUBLE PRECISION NOT NULL,
    origem TEXT NOT NULL,
    pct_nuvem DOUBLE PRECISION NOT NULL,
    pixels_validos INTEGER NOT NULL,
    massa_kg_ms_ha DOUBLE PRECISION NOT NULL,
    taxa_acumulo DOUBLE PRECISION NOT NULL,
    confianca TEXT NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)     -- one row per piquete: latest reading only
);
```
`piquete_distancia` is NOT part of this migration — deferred (see Out of scope).

### R2 — Pydantic payload model per event type
In `persistencia/eventos.py`, one `pydantic.BaseModel` subclass per `TipoEvento` value, named
`Payload<CamelCaseDoTipo>` (e.g. `PayloadPiqueteCriado`). Every model requires `entidade_id: UUID`.
Field sets, beyond `entidade_id`:

| Tipo | Campos além de `entidade_id` |
|---|---|
| `piquete_criado` | `nome: str`, `area_ha: float`, `cultivar_id: UUID`, `metodo_pastejo: Literal["continuo","rotacionado"]`, `ativo: bool` |
| `piquete_alterado` | igual a `piquete_criado` |
| `lote_criado` | `nome: str`, `composicao: list[ComposicaoPayload]`, `indissoluvel: bool` |
| `lote_alterado` | igual a `lote_criado`, mais `ativo: bool` |
| `lote_dissolvido` | (nenhum além de `entidade_id`) |
| `manejo_recomendado` | `lote_id: UUID`, `piquete_origem_id: UUID \| None`, `piquete_destino_id: UUID`, `data_prevista: date`, `dias_previstos: int`, `motivo: str`, `confianca: Literal["alta","media","baixa"]`, `motivo_confianca: str` |
| `manejo_confirmado` | `lote_id: UUID`, `piquete_destino_id: UUID`, `data_execucao: date` |
| `manejo_recusado` | `motivo: str \| None` |
| `manejo_divergente` | `piquete_real_id: UUID`, `data_execucao: date`, `observacao: str \| None` |
| `leitura_satelite` | `piquete_id: UUID`, `data: date`, `ndvi: float`, `origem_ndvi: str`, `pct_nuvem: float`, `pixels_validos: int`, `massa_kg_ms_ha: float`, `taxa_acumulo_kg_ms_ha_dia: float`, `confianca: Literal["alta","media","baixa"]` |
| `foto_validacao` | `piquete_id: UUID`, `url_foto: str`, `altura_informada_cm: float \| None`, `data: date` |
| `parametro_alterado` | `cultivar_id: UUID`, `metodo_pastejo: Literal["continuo","rotacionado"]`, `campo: str`, `valor: float`, `origem: Literal["produtor"]`, `confianca: Literal["alta","media","baixa"]` |

`ComposicaoPayload`: `categoria: Literal["bezerro","novilho","adulto"]`, `n_animais: int` (`gt=0`),
`peso_medio_kg: float` (`gt=0`).

Numeric fields that represent an area, a count or a mass must reject zero and negative values
(`Field(gt=0)`): `area_ha`, `n_animais`, `peso_medio_kg`, `massa_kg_ms_ha`, `pixels_validos`.
`pct_nuvem` is `Field(ge=0, le=100)`.

### R3 — `registrar_evento`
```python
def registrar_evento(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    tipo: TipoEvento,
    origem: OrigemEvento,
    ocorrido_em: datetime,
    payload: dict[str, Any],
    ator: str | None = None,
    corrige_evento_id: UUID | None = None,
    chave_idempotencia: str | None = None,
) -> UUID:
    """Validate payload against tipo's schema, insert the event, return its id."""
```
1. Look up the Pydantic model for `tipo` (a `dict[TipoEvento, type[BaseModel]]` module-level
   constant — never an `if/elif` chain). Validate `payload` against it; a `pydantic.ValidationError`
   propagates unchanged (do not catch and re-wrap it).
2. Insert one row into `evento` with an `INSERT ... RETURNING id` statement, using a parameterized
   query (never string-format SQL values into the query).
3. Do not call `conn.commit()` — the caller owns the transaction boundary.
4. On a unique-violation on `(fazenda_id, chave_idempotencia)` (`psycopg.errors.UniqueViolation`),
   catch it and return the `id` of the existing row with that `(fazenda_id, chave_idempotencia)`
   instead of raising — that is what makes the pipeline's re-runs safe (ADR-018 part 3).

## Constants and parameters
None numeric from `05-PARAMETROS-CULTIVARES.md` — this spec has no agronomic calculation. The
twelve `tipo_evento` values and four `origem_evento` values come from `11-ESTADO-ATUAL.md`'s
`TipoEvento`/`OrigemEvento` enums (already in `core/models.py`) and ADR-018; copy them, don't
invent new ones.

## Validation rules
- Any payload failing its Pydantic model raises `pydantic.ValidationError` — do not add a
  try/except that turns it into something else.
- `registrar_evento` raises `ValueError` if `tipo` has no entry in the payload-model table
  (should be unreachable if `TipoEvento` and the table are kept in sync — but code the check).

## Testing — who does what
Write your own tests in `tests/core/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Every Pydantic model must be exercised by at least one valid and one invalid payload in your own
tests, with **no live database** — build the model directly (`PayloadPiqueteCriado(**dict)`), you
do not need `registrar_evento` or a connection for this. If you also want to test
`registrar_evento` end-to-end against a real Postgres, gate that test behind
`@pytest.mark.skipif(not os.environ.get("SEUGADO_TEST_DATABASE_URL"), reason=...)` — per ADR-020,
it must skip cleanly, never fail, when the variable is absent.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `db/migrations/0001_evento_e_derivadas.sql` creates `tipo_evento`, `origem_evento`, `fazenda`
      (if not exists), `evento` (matching ADR-018 verbatim, including `REVOKE` and trigger),
      `estado_piquete`, `estado_lote`, `leitura` — and nothing else
- [ ] One Pydantic model per `TipoEvento` value (12 total), each with exactly the fields in the R2 table
- [ ] `registrar_evento` exists with the exact signature in R3
- [ ] `registrar_evento` never commits the transaction
- [ ] `registrar_evento` is idempotent on `chave_idempotencia` as described
- [ ] Every model rejects at least the invalid case shown in `Worked example`
- [ ] `pyproject.toml` gains exactly two new dependencies: `psycopg[binary]`, `pydantic`
- [ ] `pytest tests/core/test_eventos.py` passes with zero failures (DB-dependent test, if written,
      skips cleanly without `SEUGADO_TEST_DATABASE_URL`)
- [ ] Module imports nothing from `sensing/`, `planner/`, `api/`

## Worked example
`PayloadLeituraSatelite(entidade_id=uuid4(), piquete_id=uuid4(), data="2026-09-10", ndvi=0.62,
origem_ndvi="optico", pct_nuvem=5.0, pixels_validos=340, massa_kg_ms_ha=3200.0,
taxa_acumulo_kg_ms_ha_dia=45.0, confianca="alta")` validates successfully. The same payload with
`pixels_validos=0` raises `pydantic.ValidationError` (violates `gt=0`).

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-005.md`. Must contain:
- Structural checks: exact table list from the migration, exact column list per table, the
  `REVOKE`/trigger present verbatim, exact Pydantic field sets per tipo, no extra public functions,
  file length limit.
- The worked example above, both the valid and invalid case.
- At least one hidden numeric case not shown in this spec (e.g., `ComposicaoPayload` rejecting
  `n_animais=0`).
- A hidden case exercising idempotency: two calls to `registrar_evento` with the same
  `chave_idempotencia` (this one may be marked to run only when `SEUGADO_TEST_DATABASE_URL` is set,
  and skipped otherwise — record that explicitly so the skip isn't mistaken for a pass).

## Out of scope
- Do NOT create `piquete_distancia` — deferred to a dedicated spec before F-009.
- Do NOT implement the fold (`projetar` / `core/projecao.py`) — that is `SPEC-006`, a separate,
  pure module with no dependency on this one.
- Do NOT write anything that reads from `evento` or the derived tables — this spec is write-only.
- Do NOT add a migration runner, Alembic, or any ORM (ADR-020).
- Do NOT add FastAPI routes, auth, or any HTTP surface.
- Do NOT add logging frameworks, DI containers or decorators.
- Do NOT add caching.
- Do NOT create the full `fazenda` table shape (name, timezone, etc.) — only the minimal stub
  this migration's foreign keys need; the real table is a future spec's job.

## Style constraints
- Python 3.12, type hints on every public function
- Parameterized SQL only — never f-string or `%`-format a value into a query string
- Domain nouns stay in Portuguese in code and SQL: `piquete`, `lote`, `evento`, `fazenda`
- Docstrings and comments in English
- No abstraction without a second use case — one function, one dict of models, no factory classes
- Maximum 300 lines per file — split `persistencia/eventos.py` into a `payloads.py` (the Pydantic
  models) and `eventos.py` (`registrar_evento` + the lookup dict) if it doesn't fit; if you do,
  add both files to your own test imports and note the split in your commit message
