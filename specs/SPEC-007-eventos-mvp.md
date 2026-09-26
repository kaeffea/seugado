# SPEC-007 — Extend the domain model, event payloads and event fold for the MVP

## Context
The system stores everything that happens on a cattle farm as immutable events and derives
the current state by folding them (a "projection"). This spec extends that machinery for the
first working product: a paddock now carries its polygon, a new event records a canopy height
measured by the farmer with a ruler, a satellite reading now stores the raw observation
(no derived forage mass), a "did it differently" answer now moves the herd group, and a pure
function combines three confidence levels into one.

## Domain vocabulary
- `piquete` — a fenced paddock; the spatial unit. Keep this name in code.
- `lote` — a group of cattle managed as one unit. Keep this name in code.
- `manejo` — moving a lote from one piquete to another.
- `altura` — canopy height of the grass, in cm, measured with a ruler.
- `origem_peso` — where an animal category's mean live weight came from: typed by the farmer
  (`produtor`) or filled from the Animal Unit table (`ua_tabela`).
- `confianca` — reliability tier: `alta`, `media`, `baixa`.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- MODIFY `src/seugado/core/models.py`
- MODIFY `src/seugado/core/regras.py`
- MODIFY `src/seugado/core/projecao.py`
- MODIFY `src/seugado/persistencia/eventos.py`
- MODIFY `tests/core/test_models.py`, `tests/core/test_regras.py`, `tests/core/test_projecao.py`,
  `tests/persistencia/test_eventos.py` (add tests; keep existing ones passing unless a requirement
  below changes the behavior they check — then update them)

## Requirements

### R1 — `models.py`: weight origin and new event type
1. Add a `StrEnum`:
   ```python
   class OrigemPeso(StrEnum):
       """Where a category's mean live weight came from."""
       PRODUTOR = "produtor"
       UA_TABELA = "ua_tabela"
   ```
2. Add a last field to `ComposicaoLote`, with a default so existing constructors keep working:
   `origem_peso: OrigemPeso = OrigemPeso.PRODUTOR`.
3. Add member `ALTURA_MEDIDA = "altura_medida"` to `TipoEvento` (append it after
   `PARAMETRO_ALTERADO`). No other enum changes.

### R2 — `regras.py`: `combinar_confianca`
```python
def combinar_confianca(*fatores: Confianca) -> Confianca:
    """Return the weakest confidence among the factors (minimum on an ordered scale)."""
```
- The order is declared in a module-level dict `_ORDEM_CONFIANCA = {Confianca.BAIXA: 0,
  Confianca.MEDIA: 1, Confianca.ALTA: 2}`. Never derive the order by comparing enum members.
- Raise `ValueError` when called with zero factors.
- Examples: `(ALTA, MEDIA, ALTA) -> MEDIA`; `(ALTA,) -> ALTA`; `(MEDIA, BAIXA) -> BAIXA`.

### R3 — `eventos.py`: payload changes
Apply exactly these changes to the Pydantic payload models (all keep `extra="forbid"`):
1. `ComposicaoPayload`: add `origem_peso: Literal["produtor", "ua_tabela"]` (required).
2. `PayloadPiqueteCriado` and `PayloadPiqueteAlterado`: add
   `geometria_geojson: dict[str, Any]` (required). Validate with a `field_validator`: the dict
   must have `"type" == "Polygon"` and a `"coordinates"` list whose first ring has at least 4
   positions; otherwise raise `ValueError`.
3. `PayloadManejoDivergente`: add `lote_id: UUID` (required).
4. `PayloadLeituraSatelite`: replace the fields with exactly:
   `entidade_id: UUID`, `piquete_id: UUID`, `data: date`, `ndvi: float = Field(gt=0, le=1)`,
   `refletancia_red: float = Field(ge=0, le=1)`, `refletancia_nir: float = Field(ge=0, le=1)`,
   `origem_ndvi: Literal["optico"]`, `pct_nuvem: float = Field(ge=0, le=100)`,
   `pixels_validos: int = Field(gt=0)`.
   (`massa_kg_ms_ha`, `taxa_acumulo_kg_ms_ha_dia` and `confianca` are removed.)
5. New model and mapping entry:
   ```python
   class PayloadAlturaMedida(_PayloadBase):
       entidade_id: UUID                       # a fresh uuid per measurement
       piquete_id: UUID
       data: date
       altura_cm: float = Field(gt=0, le=400)
       meio: Literal["cadastro", "bot", "web"]
   ```
   `PAYLOAD_POR_TIPO[TipoEvento.ALTURA_MEDIDA] = PayloadAlturaMedida`.
6. `registrar_evento` itself does not change.

### R4 — `projecao.py`: fold the new shapes
1. `EstadoPiquete` gains `geometria_geojson: dict[str, Any]` (place it after `ativo`).
   `piquete_criado` and `piquete_alterado` set it from the payload.
2. `Leitura` becomes exactly: `id: UUID`, `piquete_id: UUID`, `data: date`, `ndvi: float`,
   `refletancia_red: float`, `refletancia_nir: float`, `origem_ndvi: str`, `pct_nuvem: float`,
   `pixels_validos: int`. The "keep the latest reading per piquete" rule is unchanged.
3. New frozen/slots dataclass and state field:
   ```python
   @dataclass(frozen=True, slots=True)
   class AlturaMedida:
       """Most recent ruler measurement projected for one piquete."""
       id: UUID
       piquete_id: UUID
       data: date
       altura_cm: float
       meio: str
   ```
   `EstadoFazenda` gains `alturas: dict[UUID, AlturaMedida]` (keyed by piquete id). An
   `altura_medida` event replaces the stored one when its `data` is `>=` the stored `data`.
4. `_composicao` reads `origem_peso` from each item with default `"produtor"` when the key is
   absent, and builds `ComposicaoLote(..., origem_peso=OrigemPeso(value))`.
5. `manejo_divergente`: behaves exactly like `manejo_confirmado`, using `lote_id`,
   `piquete_real_id` as the destination, and `data_execucao`. Same unknown-id errors.
6. Everything else in the fold is unchanged (ordering, corrections, `data_referencia`).

## Constants and parameters
| Name | Value | Unit | Source |
|---|---|---|---|
| `altura_cm` upper bound | 400 | cm | Sanity bound only (tallest cultivar in the catalog is below 200 cm) |

## Validation rules
- `combinar_confianca()` with no arguments raises `ValueError`.
- Piquete payload with a geometry that is not a `Polygon`, or whose first ring has fewer than 4
  positions, raises `pydantic.ValidationError` inside `registrar_evento`.
- `PayloadLeituraSatelite` with `ndvi <= 0` raises `ValidationError`.
- `manejo_divergente` whose `lote_id` or `piquete_real_id` is unknown raises `ValueError` in
  `projetar`.

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
- [ ] `OrigemPeso` exists with exactly two members and the values above
- [ ] `ComposicaoLote` has `origem_peso` as its last field, default `OrigemPeso.PRODUTOR`
- [ ] `TipoEvento.ALTURA_MEDIDA.value == "altura_medida"`
- [ ] `combinar_confianca` returns the minimum and raises on no arguments
- [ ] `PAYLOAD_POR_TIPO` has 13 entries and maps `ALTURA_MEDIDA` to `PayloadAlturaMedida`
- [ ] `PayloadLeituraSatelite` has exactly the 9 fields listed in R3.4
- [ ] `projetar` exposes `alturas`, the new `Leitura` shape and `geometria_geojson`
- [ ] `manejo_divergente` moves the lote to `piquete_real_id` and rests the previous piquete
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
Events for one farm, in `ocorrido_em` order: `piquete_criado` P1 (square polygon, 4.0 ha),
`piquete_criado` P2, `lote_criado` L1 (40 `novilho`, 337.5 kg, `origem_peso="ua_tabela"`),
`manejo_confirmado` L1 → P1 on 2026-09-20, `altura_medida` P2 = 28.0 cm on 2026-09-21,
`manejo_recomendado` L1 → P2 (entidade M1), `manejo_divergente` (entidade M1, `lote_id` L1,
`piquete_real_id` P2, `data_execucao` 2026-09-24). After `projetar`: P2 is `ocupado` by L1
since 2026-09-24; P1 is `descansando` since 2026-09-24; `alturas[P2].altura_cm == 28.0`;
L1's composition item has `origem_peso == OrigemPeso.UA_TABELA`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-007.md`.

## Out of scope
- Do NOT touch the database schema or any `.sql` file
- Do NOT write to derived tables or add any persistence function
- Do NOT change `forragem.py`, `resolver_parametros`, `apto_para_entrada`, `precisa_sair`,
  `urgencia` or `descanso_cumprido`
- Do NOT add projection effects for `manejo_recomendado`, `manejo_recusado`,
  `foto_validacao` or `parametro_alterado` (they stay no-ops in the fold)
- Do NOT add logging, caching, abstract classes or new dependencies
- Do NOT reorganise or rename existing files, functions or fields beyond what R1–R4 state

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions in `core/`: no I/O, no global state, no side effects
- Variable names carry their unit: `altura_cm`, not `altura`
- Domain nouns stay in Portuguese; docstrings and comments in English
- `__init__.py` files stay empty
- Maximum 300 lines per file
