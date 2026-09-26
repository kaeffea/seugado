# SPEC-008 — MVP database schema, projection rebuild and cultivar catalog

## Context
The farm's history lives in an append-only `evento` table; the screens and the planner read
"derived" tables that are rebuilt from those events. This spec adds the second SQL migration
(farm settings, user↔farm link, cultivar catalog, derived tables with every column the screens
need, the weekly plan table, the Telegram conversation table, and row-level security), a
function that rebuilds the derived tables for one farm, and a loader for the cultivar catalog
with the farm's own height overrides applied.

## Domain vocabulary
- `fazenda` — farm. `piquete` — paddock. `lote` — cattle group. `cultivar` — grass variety.
- `metodo_pastejo` — `continuo` (animals stay) or `rotacionado` (animals rotate).
- `override` — a height typed by the farmer for a cultivar × grazing-method cell that has no
  published source; it applies to that farm only.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read (not modify) `src/seugado/core/models.py`, `src/seugado/core/projecao.py`,
`src/seugado/core/regras.py` and `src/seugado/persistencia/eventos.py` to import from them.

## Files to create or modify
- CREATE `db/migrations/0002_mvp.sql`
- CREATE `src/seugado/persistencia/projecao_db.py`
- CREATE `src/seugado/persistencia/catalogo.py`
- CREATE `tests/persistencia/test_projecao_db.py`
- CREATE `tests/persistencia/test_catalogo.py`

## Requirements

### R1 — `db/migrations/0002_mvp.sql`
Runs after `0001_evento_e_derivadas.sql`, in one transaction (`BEGIN; … COMMIT;`). Contents,
in this order:

1. `CREATE EXTENSION IF NOT EXISTS postgis;`
2. Farm settings on the existing `fazenda` table:
   ```sql
   ALTER TABLE fazenda
       ADD COLUMN nome TEXT NOT NULL DEFAULT '',
       ADD COLUMN timezone TEXT NOT NULL DEFAULT 'America/Fortaleza',
       ADD COLUMN funcionarios_disponiveis INTEGER NOT NULL DEFAULT 1
           CHECK (funcionarios_disponiveis >= 1),
       ADD COLUMN manejos_por_funcionario_dia INTEGER NOT NULL DEFAULT 1
           CHECK (manejos_por_funcionario_dia >= 1),
       ADD COLUMN dias_preferenciais_manejo SMALLINT[] NOT NULL DEFAULT '{0}'
           CHECK (cardinality(dias_preferenciais_manejo) >= 1
                  AND dias_preferenciais_manejo <@ '{0,1,2,3,4,5,6}'::smallint[]),
       ADD COLUMN telegram_chat_id BIGINT,
       ADD COLUMN codigo_vinculo_telegram TEXT NOT NULL
           DEFAULT substr(replace(gen_random_uuid()::text, '-', ''), 1, 16),
       ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT true,
       ADD COLUMN criado_em TIMESTAMPTZ NOT NULL DEFAULT now();
   CREATE UNIQUE INDEX fazenda_codigo_vinculo_idx ON fazenda (codigo_vinculo_telegram);
   ```
   `dias_preferenciais_manejo` uses Python's `date.weekday()` numbering: 0 = Monday … 6 = Sunday.
3. User ↔ farm link (one farm per user in the MVP):
   ```sql
   CREATE TABLE fazenda_usuario (
       usuario_id UUID PRIMARY KEY,               -- Supabase Auth user id
       fazenda_id UUID NOT NULL REFERENCES fazenda(id),
       criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```
4. Cultivar catalog and seed — copy the `INSERT` block from the section **Cultivar seed** below
   verbatim:
   ```sql
   CREATE TABLE cultivar (
       id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       slug       TEXT NOT NULL UNIQUE,
       nome       TEXT NOT NULL,
       parametros JSONB NOT NULL
   );
   ```
5. `INSERT INTO tipo_evento (tipo) VALUES ('altura_medida');`
6. Replace the derived tables (they hold no data yet):
   ```sql
   DROP TABLE estado_piquete;
   DROP TABLE estado_lote;
   DROP TABLE leitura;

   CREATE TABLE estado_piquete (
       fazenda_id     UUID NOT NULL REFERENCES fazenda(id),
       piquete_id     UUID NOT NULL,
       nome           TEXT NOT NULL,
       area_ha        DOUBLE PRECISION NOT NULL,
       cultivar_id    UUID NOT NULL,
       metodo_pastejo TEXT NOT NULL,
       ativo          BOOLEAN NOT NULL,
       geometria      geometry(Polygon, 4326) NOT NULL,
       situacao       TEXT NOT NULL,
       lote_atual_id  UUID,
       desde          DATE NOT NULL,
       dias_descanso  INTEGER NOT NULL,
       derivado_ate_sequencia BIGINT NOT NULL,
       derivado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
       PRIMARY KEY (fazenda_id, piquete_id)
   );
   CREATE TABLE estado_lote (
       fazenda_id       UUID NOT NULL REFERENCES fazenda(id),
       lote_id          UUID NOT NULL,
       nome             TEXT NOT NULL,
       indissoluvel     BOOLEAN NOT NULL,
       composicao       JSONB NOT NULL,   -- [{categoria, n_animais, peso_medio_kg, origem_peso}]
       piquete_atual_id UUID,
       desde            DATE,
       peso_vivo_total_kg DOUBLE PRECISION NOT NULL,
       derivado_ate_sequencia BIGINT NOT NULL,
       derivado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
       PRIMARY KEY (fazenda_id, lote_id)
   );
   CREATE TABLE leitura (
       id              UUID NOT NULL,
       fazenda_id      UUID NOT NULL REFERENCES fazenda(id),
       piquete_id      UUID NOT NULL,
       data            DATE NOT NULL,
       ndvi            DOUBLE PRECISION NOT NULL,
       refletancia_red DOUBLE PRECISION NOT NULL,
       refletancia_nir DOUBLE PRECISION NOT NULL,
       origem          TEXT NOT NULL,
       pct_nuvem       DOUBLE PRECISION NOT NULL,
       pixels_validos  INTEGER NOT NULL,
       derivado_ate_sequencia BIGINT NOT NULL,
       derivado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
       PRIMARY KEY (fazenda_id, piquete_id)
   );
   CREATE TABLE altura_atual (
       fazenda_id  UUID NOT NULL REFERENCES fazenda(id),
       piquete_id  UUID NOT NULL,
       data        DATE NOT NULL,
       altura_cm   DOUBLE PRECISION NOT NULL,
       meio        TEXT NOT NULL,
       derivado_ate_sequencia BIGINT NOT NULL,
       derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
       PRIMARY KEY (fazenda_id, piquete_id)
   );
   ```
7. Weekly plan and Telegram conversation state:
   ```sql
   CREATE TABLE plano (
       id             UUID PRIMARY KEY,
       fazenda_id     UUID NOT NULL REFERENCES fazenda(id),
       gerado_em      TIMESTAMPTZ NOT NULL,
       data_inicio    DATE NOT NULL,
       horizonte_dias INTEGER NOT NULL,
       payload        JSONB NOT NULL
   );
   CREATE INDEX plano_fazenda_gerado_idx ON plano (fazenda_id, gerado_em DESC);

   CREATE TABLE telegram_conversa (
       chat_id       BIGINT PRIMARY KEY,
       estado        TEXT NOT NULL,
       dados         JSONB NOT NULL DEFAULT '{}'::jsonb,
       atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```
8. Row-level security, so that Supabase's public REST API cannot read or write any table (the
   backend connects as the table owner, which bypasses RLS). One statement per table:
   `ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;` for `tipo_evento`, `origem_evento`, `fazenda`,
   `evento`, `fazenda_usuario`, `cultivar`, `estado_piquete`, `estado_lote`, `leitura`,
   `altura_atual`, `plano`, `telegram_conversa`. Create **no** policies.

### R2 — `persistencia/projecao_db.py`
```python
def carregar_eventos(conn: psycopg.Connection[Any], fazenda_id: UUID) -> list[Evento]:
    """Load every event of one farm ordered by (ocorrido_em, sequencia)."""

def reconstruir_projecao(conn: psycopg.Connection[Any], fazenda_id: UUID) -> EstadoFazenda:
    """Rebuild all derived tables of one farm from its events, inside the caller's transaction."""
```
- `carregar_eventos` maps each row to `core.models.Evento` (`tipo` → `TipoEvento`, `origem` →
  `OrigemEvento`, `payload` as the decoded dict).
- `reconstruir_projecao`, in this order:
  1. `SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))` with the farm id.
  2. Load events. If there are none: delete the farm's rows from the four derived tables and
     return `EstadoFazenda(fazenda_id=fazenda_id, piquetes={}, lotes={}, leituras={}, alturas={})`.
  3. `estado = projetar(eventos)`; `seq = max(e.sequencia for e in eventos)`.
  4. `DELETE` the farm's rows from `estado_piquete`, `estado_lote`, `leitura`, `altura_atual`.
  5. `INSERT` one row per projected piquete, lote, leitura and altura, with
     `derivado_ate_sequencia = seq`. Geometry is written with
     `ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)` from `json.dumps(geometria_geojson)`.
     `composicao` is written as JSON: a list of
     `{"categoria", "n_animais", "peso_medio_kg", "origem_peso"}` using enum `.value`.
  6. Return `estado`. **Never commit or roll back**: the caller owns the transaction.

### R3 — `persistencia/catalogo.py`
```python
@dataclass(frozen=True, slots=True)
class CultivarCatalogo:
    """A catalog cultivar with this farm's overrides applied; numeric gaps stay None."""
    id: UUID
    slug: str
    nome: str
    parametros_por_regime: tuple[ParametrosRegime, ...]
    eficiencia_por_metodo: tuple[tuple[MetodoPastejo, float], ...]
    densidade_kg_ha_por_cm: float | None
    rue_max_g_por_mj: float | None
    temperatura_base_c: float | None
    descanso_min_dias: float
    qualidade_base: QualidadeBase | None

CAMPOS_ALTURA = ("altura_entrada_cm", "altura_saida_cm", "altura_maxima_cm", "altura_minima_cm")

def cultivar_de_linha(id: UUID, slug: str, nome: str, parametros: dict[str, Any]) -> CultivarCatalogo: ...
def overrides_da_fazenda(eventos: Sequence[Evento]) -> dict[UUID, tuple[tuple[MetodoPastejo, str, float], ...]]: ...
def aplicar_overrides(
    cultivar: CultivarCatalogo,
    overrides: Sequence[tuple[MetodoPastejo, str, float]],
    fazenda_id: UUID,
) -> CultivarCatalogo: ...
def carregar_catalogo(conn: psycopg.Connection[Any], fazenda_id: UUID | None) -> dict[UUID, CultivarCatalogo]: ...
def resolver_alturas(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> ResolucaoParametros: ...
def eficiencia_pastejo(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> float | None: ...
def faltantes_calibracao(cultivar: CultivarCatalogo, metodo: MetodoPastejo) -> tuple[str, ...]: ...
```
- `cultivar_de_linha` parses the `parametros` JSON shape used in the seed below. Each entry of
  `por_regime` becomes a `ParametrosRegime` (the four height keys, `confianca`, `fonte`); an
  entry's optional `eficiencia_pastejo` (number) becomes a pair in `eficiencia_por_metodo`.
  `qualidade_base: null` → `None`.
- `overrides_da_fazenda` reads only `parametro_alterado` events. For each
  `(cultivar_id, metodo_pastejo, campo)` it keeps the value of the last event in
  `(ocorrido_em, sequencia)` order. Result is keyed by cultivar id.
- `aplicar_overrides`: for each `(metodo, campo, valor)`, `campo` must be in `CAMPOS_ALTURA`
  (else `ValueError`). If a block for `metodo` exists, replace that field; otherwise create a
  block for `metodo` with every other height `None`. Every block touched by an override gets
  `confianca=Confianca.BAIXA` and `fonte=f"produtor:{fazenda_id}"`. Untouched blocks are kept.
- `carregar_catalogo`: `SELECT id, slug, nome, parametros FROM cultivar ORDER BY nome`; when
  `fazenda_id` is not `None`, loads the farm's events with `carregar_eventos` and applies
  `overrides_da_fazenda` through `aplicar_overrides`.
- `resolver_alturas` builds a `core.models.Cultivar` with the catalog's
  `parametros_por_regime` (numeric fields filled with `0.0` and `qualidade_base` with
  `QualidadeBase.MEDIA` when missing — `resolver_parametros` reads only
  `parametros_por_regime`) and returns `core.regras.resolver_parametros(cultivar, metodo)`.
- `eficiencia_pastejo` returns the pair's value for `metodo`, or `None`.
- `faltantes_calibracao` returns, in this order and only when missing:
  `"densidade_kg_ha_por_cm"`, `"rue_max_g_por_mj"`, and `"eficiencia_pastejo"` **only when
  `metodo` is `ROTACIONADO`**.

## Cultivar seed
Copy verbatim into the migration (step R1.4). All numbers come from
`05-PARAMETROS-CULTIVARES.md`.

```sql
INSERT INTO cultivar (slug, nome, parametros) VALUES
('marandu', 'Marandu', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 30, "altura_saida_cm": 15,
     "altura_maxima_cm": null, "altura_minima_cm": null, "eficiencia_pastejo": 0.72,
     "confianca": "media", "fonte": "Andrade (2008), Embrapa Acre, via Soares et al. (2021)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 35, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": 110, "rue_max_g_por_mj": 2.31, "temperatura_base_c": 15.0,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": "alta"}'),
('mombaca', 'Mombaça', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 85, "altura_saida_cm": 45,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "media", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 75, "altura_minima_cm": 50,
     "confianca": "media", "fonte": "Kill-Silveira (2020), Rev. Vet. Zootec. 27"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": "alta"}'),
('tanzania', 'Tanzânia', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 70, "altura_saida_cm": 35,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "media", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 60, "altura_minima_cm": 40,
     "confianca": "media", "fonte": "Kill-Silveira (2020), Rev. Vet. Zootec. 27"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": 15.0,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('zuri', 'Zuri', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 80, "altura_saida_cm": 40,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('massai', 'Massai', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 55, "altura_saida_cm": 30,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('tamani', 'Tamani', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 50, "altura_saida_cm": 25,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('xaraes', 'Xaraés', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 40, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('piata', 'Piatã', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 40, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "rotacionado", "altura_entrada_cm": 32.9, "altura_saida_cm": null,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "baixa", "fonte": "Crestani et al., Embrapa (ILPF, pleno sol)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": 2.31, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('decumbens', 'Brachiaria decumbens', '{
  "especie": "Brachiaria decumbens", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 30, "altura_minima_cm": 15,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": 16.7,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}');
```

## Constants and parameters
Every agronomic number is inside the seed above and comes from `05-PARAMETROS-CULTIVARES.md`.
No other number is used.

## Validation rules
- `aplicar_overrides` raises `ValueError` for a `campo` outside `CAMPOS_ALTURA`.
- `cultivar_de_linha` raises `ValueError` when `por_regime` is missing or an entry has an
  unknown `metodo` or `confianca`.
- `reconstruir_projecao` lets database errors propagate; it never swallows exceptions.

## Testing — who does what
Write your own tests in `tests/persistencia/`, as a smoke check that your code runs and behaves
as described. Keep them short. Tests that need a real database read
`SEUGADO_TEST_DATABASE_URL` from the environment and are skipped with `pytest.mark.skipif` when
it is absent. Pure functions (`cultivar_de_linha`, `overrides_da_fazenda`, `aplicar_overrides`,
`resolver_alturas`, `eficiencia_pastejo`, `faltantes_calibracao`) are always tested without a
database. You will NOT be given a test file to copy, and you must not wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `0002_mvp.sql` applies cleanly after `0001` on a fresh Supabase database
- [ ] After the migration, `SELECT count(*) FROM cultivar` returns 9
- [ ] RLS is enabled on the 12 listed tables and no policy exists
- [ ] `reconstruir_projecao` writes exactly one `estado_piquete` row per projected piquete,
      with a valid PostGIS polygon, and never commits
- [ ] `carregar_catalogo(conn, None)["<marandu id>"].densidade_kg_ha_por_cm == 110`
- [ ] `faltantes_calibracao(mombaca, ROTACIONADO) == ("densidade_kg_ha_por_cm", "rue_max_g_por_mj", "eficiencia_pastejo")`
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
Catalog Xaraés has only a `continuo` block. A farm registers one `parametro_alterado` event
(`cultivar_id` = Xaraés, `metodo_pastejo` = `rotacionado`, `campo` = `altura_entrada_cm`,
`valor` = 35) and later another one with `campo` = `altura_saida_cm`, `valor` = 18.
`carregar_catalogo(conn, fazenda_id)` returns Xaraés with two blocks: the untouched `continuo`
block, and a new `rotacionado` block with entry 35 cm, exit 18 cm, `confianca=baixa`,
`fonte="produtor:<fazenda_id>"`. `resolver_alturas(xaraes, ROTACIONADO).faltantes == ()`.
With only the first event, `faltantes == ("altura_saida_cm",)`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-008.md`.

## Out of scope
- Do NOT modify `0001_evento_e_derivadas.sql`, `core/` or `persistencia/eventos.py`
- Do NOT create a `piquete_distancia` table or any distance computation
- Do NOT add HTTP endpoints, auth or Supabase client code
- Do NOT add an ORM, a migration tool or any new dependency
- Do NOT commit inside any function of this spec
- Do NOT cache the catalog

## Style constraints
- Python 3.12, type hints on every public function
- SQL as plain strings with `%s` parameters (psycopg 3); never build SQL with f-strings from data
- Domain nouns stay in Portuguese; docstrings and comments in English
- `__init__.py` files stay empty
- Maximum 300 lines per file
