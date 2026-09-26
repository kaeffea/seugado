# SPEC-013 — Satellite readings per paddock from HLS on Google Earth Engine

## Context
The system needs, for each paddock, the mean red and near-infrared surface reflectance of its
cloud-free pixels on each date a satellite passed. Google Earth Engine (GEE) hosts the
Harmonized Landsat Sentinel-2 (HLS) collections and computes these means server-side, so only a
few numbers per paddock per date come back. This spec creates the GEE sampling function (with
cloud, cloud-shadow and edge masking) and the ingestion function that stores each reading as an
idempotent `leitura_satelite` event.

## Domain vocabulary
- `piquete` — paddock (a polygon). `leitura` — one satellite reading of one piquete on one date.
- `pixels_validos` — number of 30 m pixels inside the shrunken polygon that are clear.
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
class ObservacaoHLS:
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
def amostrar_hls(
    piquetes: Sequence[tuple[UUID, dict[str, Any]]],   # (piquete_id, GeoJSON Polygon)
    data_inicio: date,
    data_fim: date,                                     # inclusive
) -> list[ObservacaoHLS]: ...

def extrair_observacoes(linhas: Sequence[Mapping[str, Any]]) -> list[ObservacaoHLS]: ...
```
`amostrar_hls` (GEE side, one `getInfo()` call per image batch is fine):
1. FeatureCollection of the piquetes, each geometry shrunk with `.buffer(-15)` (metres) and
   carrying property `piquete_id` (string).
2. Collections `NASA/HLS/HLSS30/v002` (red `B4`, NIR `B8A`) and `NASA/HLS/HLSL30/v002`
   (red `B4`, NIR `B5`), each filtered by bounds and by `[data_inicio, data_fim + 1 day)`,
   bands renamed to `red`, `nir`, `Fmask`, and merged.
3. Per image: keep `red` and `nir` as they come (scaling is decided in `extrair_observacoes`,
   below). Clear-pixel mask = `Fmask` bits 1 (cloud),
   2 (adjacent to cloud/shadow), 3 (cloud shadow), 4 (snow/ice) and 5 (water) **all zero**.
4. Per image, `reduceRegions` over the shrunken piquetes at `scale=30` with
   `ee.Reducer.mean()` on masked `red` and `nir`, plus the count of masked pixels
   (`pixels_validos`) and the count of all pixels of an unmasked constant band
   (`pixels_totais`). Each output row carries `piquete_id`, `data` (image date,
   `YYYY-MM-DD` from `system:time_start`), `red`, `nir`, `pixels_validos`, `pixels_totais`.
5. Collect all rows as plain dicts and return `extrair_observacoes(rows)`.

`extrair_observacoes` (pure):
- Scaling: the GEE catalog shows these bands as reflectance already scaled to 0–1
  (visualisation range 0.01–0.18), but the HLS files store int16 × 0.0001. Handle both: if
  `red > 1.0` or `nir > 1.0`, multiply **both** by 0.0001; otherwise use them as they are.
- Drop rows with `pixels_validos < 3`, or `red`/`nir` missing, or `red + nir <= 0`, or (after
  scaling) `red` or `nir` outside `[0, 1]`.
- `ndvi = (nir − red) / (nir + red)`; drop rows with `ndvi <= 0`.
- `pct_nuvem = 100 · (1 − pixels_validos / pixels_totais)`, clamped to `[0, 100]`.
- When the same `(piquete_id, data)` appears more than once, keep the row with the most
  `pixels_validos` (tie: the first).
- Return sorted by `(piquete_id, data)`.

### R3 — `ingestao.py`
```python
def ingerir_leituras(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    data_inicio: date,
    data_fim: date,
) -> int:
    """Sample HLS for the farm's active piquetes and record one event per new reading."""
```
1. Load active piquetes:
   `SELECT piquete_id, ST_AsGeoJSON(geometria) FROM estado_piquete WHERE fazenda_id = %s AND ativo`.
   None → return 0.
2. `inicializar_earth_engine()`; `amostrar_hls(...)`.
3. For each observation call `registrar_evento(conn, fazenda_id, TipoEvento.LEITURA_SATELITE,
   OrigemEvento.SATELITE, ocorrido_em=<data at 12:00 UTC>, payload=…, ator="ingestao_hls",
   chave_idempotencia=f"leitura:{piquete_id}:{data.isoformat()}")`, where `payload` has
   `entidade_id` = `uuid5(NAMESPACE_URL, chave)`, `piquete_id`, `data`, `ndvi`,
   `refletancia_red`, `refletancia_nir`, `origem_ndvi="optico"`, `pct_nuvem`, `pixels_validos`.
4. Return the number of observations sent to `registrar_evento`. **Do not commit** and do not
   rebuild projections: the caller does both.

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Collections | `NASA/HLS/HLSS30/v002`, `NASA/HLS/HLSL30/v002` | GEE catalog |
| Reflectance scale | 0.0001 | HLS v2.0 user guide (int16 surface reflectance) |
| Fmask bits masked | 1, 2, 3, 4, 5 | GEE catalog band description |
| Negative buffer | −15 m | `HIPOTESE-CALIBRAR` (example value in `04` §4) — ADR-023 |
| Minimum clear pixels | 3 | `HIPOTESE-CALIBRAR` — ADR-023 |
| Pixel scale | 30 m | HLS native resolution |

## Validation rules
- `amostrar_hls` with `data_inicio > data_fim` → `ValueError`.
- A piquete geometry that is not a GeoJSON Polygon → `ValueError` before calling GEE.
- GEE exceptions propagate (no retry, no swallowing).

## Testing — who does what
Write your own tests in `tests/sensing/`. Test `extrair_observacoes` with literal rows. Test
`ingerir_leituras` by monkeypatching `inicializar_earth_engine`, `amostrar_hls` and
`registrar_evento`, and with a fake connection whose cursor returns fixed rows. No test may call
Earth Engine or a real database. You will NOT be given a test file to copy.

Your tests are not the verification of record. A separate agent writes an independent
conformance suite in `tests/conformance/` and decides whether the work is accepted. Do not
create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `extrair_observacoes` applies the pixel threshold, NDVI formula, deduplication and sorting
- [ ] `ingerir_leituras` uses the idempotency key `leitura:<piquete_id>:<YYYY-MM-DD>`
- [ ] Running `ingerir_leituras` twice for the same period creates no duplicate events
      (checked against a real Supabase database by the tester)
- [ ] Neither function commits
- [ ] `mypy` passes (an override for the untyped `ee` module is already configured)
- [ ] `uv run ruff check .` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
Rows: `{piquete_id: P1, data: "2026-09-20", red: 0.05, nir: 0.35, pixels_validos: 40,
pixels_totais: 50}`, `{P1, "2026-09-20", red: 0.06, nir: 0.30, pixels_validos: 12,
pixels_totais: 50}` and `{P2, "2026-09-20", red: 0.05, nir: 0.30, pixels_validos: 2,
pixels_totais: 50}`. Result: one observation, P1 on 2026-09-20, `ndvi = 0.30/0.40 = 0.75`,
`pct_nuvem = 20.0`, `pixels_validos = 40`. P2 is dropped (fewer than 3 clear pixels).

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-013.md`.

## Out of scope
- Do NOT compute SAFER, forage mass or height here
- Do NOT use Sentinel-1 (radar), Sentinel-2 10 m or any other collection
- Do NOT download images or use GeoTIFF/raster libraries
- Do NOT write to derived tables or rebuild projections
- Do NOT add retries, caching, threads or new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- `extrair_observacoes` is pure; I/O only in `amostrar_hls`, `inicializar_earth_engine`,
  `ingerir_leituras`
- Domain nouns stay in Portuguese; docstrings in English
- `__init__.py` files stay empty; maximum 300 lines per file
