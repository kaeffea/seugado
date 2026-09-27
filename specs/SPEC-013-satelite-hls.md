# SPEC-013 — Satellite readings per paddock from Sentinel-2 (10 m) on Google Earth Engine

## Context
The system needs, for each paddock, the mean red and near-infrared surface reflectance of its
cloud-free pixels on each date the satellite passed. Paddocks are small (often 0.1 to 0.5 ha),
so the 10 m Sentinel-2 surface-reflectance product is used, with Google's Cloud Score+ layer to
remove clouds and cloud shadows. Google Earth Engine (GEE) computes the means server-side, so
only a few numbers per paddock per date come back. This spec creates the GEE sampling function
and the ingestion function that stores each reading as an idempotent `leitura_satelite` event.
The file name keeps the historical "hls" suffix.

## Domain vocabulary
- `piquete` — paddock (a polygon). `leitura` — one satellite reading of one piquete on one date.
- `pixels_validos` — number of 10 m pixels inside the shrunken polygon that are clear.
- `pct_nuvem` — percentage of the shrunken polygon's pixels that were masked out.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

You may read (not modify) `src/seugado/persistencia/eventos.py` and `src/seugado/core/models.py`.

## Files to create or modify
- CREATE `src/seugado/sensing/earth_engine.py`
- CREATE `src/seugado/sensing/ingestao.py`
- CREATE `tests/sensing/test_earth_engine.py`
- CREATE `tests/sensing/test_ingestao.py`

## Requirements

### R1 — `earth_engine.py`: types and initialisation
```python
@dataclass(frozen=True, slots=True)
class ObservacaoSatelite:
    piquete_id: UUID
    data: date
    ndvi: float
    refletancia_red: float
    refletancia_nir: float
    pixels_validos: int
    pixels_totais: int
    pct_nuvem: float

def inicializar_earth_engine() -> None:
    """Authenticate with a service account taken from the environment."""
```
`inicializar_earth_engine` reads `SEUGADO_GEE_SERVICE_ACCOUNT_JSON` (the JSON key **content**,
not a path) and `SEUGADO_GEE_PROJECT`, builds
`ee.ServiceAccountCredentials(email=<client_email from the JSON>, key_data=<the JSON string>)`
and calls `ee.Initialize(credentials, project=<project>)`. Missing variable → `RuntimeError`
naming it.

### R2 — `earth_engine.py`: sampling
```python
def amostrar_sentinel2(
    piquetes: Sequence[tuple[UUID, dict[str, Any]]],   # (piquete_id, GeoJSON Polygon)
    data_inicio: date,
    data_fim: date,                                     # inclusive
) -> list[ObservacaoSatelite]: ...

def extrair_observacoes(linhas: Sequence[Mapping[str, Any]]) -> list[ObservacaoSatelite]: ...
```
`amostrar_sentinel2` (GEE side):
1. FeatureCollection of the piquetes, each geometry shrunk with `.buffer(-5)` (metres) and
   carrying property `piquete_id` (string).
2. Collection `COPERNICUS/S2_SR_HARMONIZED`, filtered by bounds and by
   `[data_inicio, data_fim + 1 day)`, linked with `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`
   (`linkCollection(cs_plus, ["cs_cdf"])`).
3. Per image: clear-pixel mask = `cs_cdf >= 0.60`. Bands: red = `B4`, NIR = `B8`, both 10 m,
   kept as they come (scaling is decided in `extrair_observacoes`).
4. Per image, `reduceRegions` over the shrunken piquetes at `scale=10` with
   `ee.Reducer.mean()` on masked `B4` and `B8`, plus the count of masked pixels
   (`pixels_validos`) and the count of all pixels of an unmasked constant band
   (`pixels_totais`). Each output row carries `piquete_id`, `data` (`YYYY-MM-DD` from
   `system:time_start`), `red`, `nir`, `pixels_validos`, `pixels_totais`.
5. Collect the rows as plain dicts and return `extrair_observacoes(rows)`.

`extrair_observacoes` (pure):
- Scaling: Sentinel-2 SR stores reflectance × 10 000. If `red > 1.0` or `nir > 1.0`, multiply
  **both** by 0.0001; otherwise use them as they are.
- Drop rows with `pixels_validos < 3`, or `red`/`nir` missing, or `red + nir <= 0`, or (after
  scaling) `red` or `nir` outside `[0, 1]`.
- `ndvi = (nir − red) / (nir + red)`; drop rows with `ndvi <= 0`.
- `pct_nuvem = 100 · (1 − pixels_validos / pixels_totais)`, clamped to `[0, 100]`.
- When the same `(piquete_id, data)` appears more than once (overlapping tiles), keep the row
  with the most `pixels_validos` (tie: the first).
- Return sorted by `(piquete_id, data)`.

### R3 — `ingestao.py`
```python
def ingerir_leituras(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    data_inicio: date,
    data_fim: date,
) -> int:
    """Sample Sentinel-2 for the farm's active piquetes; record one event per new reading.

    Returns how many readings were NEW (not already stored)."""
```
1. Load active piquetes:
   `SELECT piquete_id, ST_AsGeoJSON(geometria) FROM estado_piquete WHERE fazenda_id = %s AND ativo`.
   None → return 0.
2. `inicializar_earth_engine()`; `amostrar_sentinel2(...)`.
3. For each observation, key = `f"leitura:{piquete_id}:{data.isoformat()}"`. If an event with
   this `chave_idempotencia` already exists for the farm (`SELECT 1 FROM evento WHERE
   fazenda_id = %s AND chave_idempotencia = %s`), skip it. Otherwise call
   `registrar_evento(conn, fazenda_id, TipoEvento.LEITURA_SATELITE, OrigemEvento.SATELITE,
   ocorrido_em=<now, UTC>, payload=…, ator="ingestao_sentinel2", chave_idempotencia=key)`,
   where `payload` has `entidade_id` = `uuid5(NAMESPACE_URL, key)`, `piquete_id`, `data`,
   `ndvi`, `refletancia_red`, `refletancia_nir`, `origem_ndvi="optico"`, `pct_nuvem`,
   `pixels_validos`.
4. Return the number of NEW readings registered. **Do not commit** and do not rebuild
   projections: the caller does both.

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Collection | `COPERNICUS/S2_SR_HARMONIZED` (Level-2A) | GEE catalog |
| Cloud mask | `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, `cs_cdf >= 0.60` | GEE catalog (recommended 0.50–0.65; example uses 0.60) |
| Bands | red `B4`, NIR `B8` (both 10 m) | Sentinel-2 MSI |
| Reflectance scale | 0.0001 | Sentinel-2 L2A (DN / 10 000) |
| Negative buffer | −5 m | `HIPOTESE-CALIBRAR` — ADR-025 (half a pixel) |
| Minimum clear pixels | 3 | `HIPOTESE-CALIBRAR` — ADR-023 |
| Pixel scale | 10 m | Sentinel-2 B4/B8 native |

## Validation rules
- `amostrar_sentinel2` with `data_inicio > data_fim` → `ValueError`.
- A piquete geometry that is not a GeoJSON Polygon → `ValueError` before calling GEE.
- GEE exceptions propagate (no retry, no swallowing).

## Testing — who does what
Write your own tests in `tests/sensing/`. Test `extrair_observacoes` with literal rows. Test
`ingerir_leituras` by monkeypatching `inicializar_earth_engine`, `amostrar_sentinel2` and
`registrar_evento`, and with a fake connection whose cursor returns fixed rows. No test may call
Earth Engine or a real database. You will NOT be given a test file to copy.

Your tests are not the verification of record. A separate agent writes an independent
conformance suite in `tests/conformance/` and decides whether the work is accepted. Do not
create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `extrair_observacoes` applies scaling, pixel threshold, NDVI, deduplication and sorting
- [ ] `ingerir_leituras` uses the key `leitura:<piquete_id>:<YYYY-MM-DD>` and returns only NEW readings
- [ ] Running `ingerir_leituras` twice for the same period returns 0 the second time and
      creates no duplicate events (tester, real Supabase + GEE)
- [ ] A 0.1 ha test paddock gets at least one reading in a 30-day window (tester, real GEE)
- [ ] Neither function commits
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run --env-file .env pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
Rows: `{piquete_id: P1, data: "2026-09-20", red: 500, nir: 3500, pixels_validos: 40,
pixels_totais: 50}`, `{P1, "2026-09-20", red: 600, nir: 3000, pixels_validos: 12,
pixels_totais: 50}` and `{P2, "2026-09-20", red: 500, nir: 3000, pixels_validos: 2,
pixels_totais: 50}`. Result: one observation, P1 on 2026-09-20, `refletancia_red = 0.05`,
`refletancia_nir = 0.35`, `ndvi = 0.30/0.40 = 0.75`, `pct_nuvem = 20.0`, `pixels_validos = 40`.
P2 is dropped (fewer than 3 clear pixels).

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-013.md`.

## Out of scope
- Do NOT compute SAFER, forage mass or height here
- Do NOT use HLS, Landsat, Sentinel-1 (radar) or any other collection
- Do NOT download images or use raster libraries
- Do NOT write to derived tables or rebuild projections
- Do NOT add retries, caching, threads or new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- `extrair_observacoes` is pure; I/O only in `amostrar_sentinel2`, `inicializar_earth_engine`,
  `ingerir_leituras`
- Domain nouns stay in Portuguese; docstrings in English
- `__init__.py` files stay empty; maximum 300 lines per file
