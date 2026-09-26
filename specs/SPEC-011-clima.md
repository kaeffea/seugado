# SPEC-011 — Daily weather client (Open-Meteo), extraterrestrial radiation and degree-days

## Context
Grass grows with solar energy and temperature. Between satellite passes the system advances
each paddock day by day using daily weather, and for the next two weeks it uses the weather
forecast. This spec creates the weather module: a client for the free Open-Meteo API (history
and forecast, no key), the extraterrestrial radiation formula needed to compute atmospheric
transmissivity, and the degree-day formula.

## Domain vocabulary
- `clima` — weather. `chuva` — rainfall. `graus_dia` — growing degree-days.
- `rg` — global solar radiation reaching the ground. `ra` — radiation at the top of the atmosphere.
- `et0` — reference evapotranspiration (FAO-56), in mm per day.
- `previsto` — the value comes from a forecast (future day), not from observation.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- CREATE `src/seugado/sensing/clima.py`
- CREATE `tests/sensing/test_clima.py`

## Requirements

### R1 — Data type
```python
@dataclass(frozen=True, slots=True)
class ClimaDia:
    """Daily weather for one location."""
    data: date
    rg_mj_m2_dia: float
    t_max_c: float
    t_min_c: float
    t_media_c: float
    et0_mm_dia: float
    chuva_mm: float
    previsto: bool
```

### R2 — Pure formulas
```python
def radiacao_extraterrestre_mj_m2_dia(lat_graus: float, data: date) -> float:
    """Daily extraterrestrial radiation Ra (FAO-56, eq. 21)."""

def graus_dia(t_max_c: float, t_min_c: float, temperatura_base_c: float) -> float:
    """Daily growing degree-days: max(0, (t_max + t_min)/2 - t_base)."""
```
Ra, with `J` = day of year (1–366), `φ` = latitude in radians (south is negative):
```
dr = 1 + 0.033 * cos(2π J / 365)
δ  = 0.409 * sin(2π J / 365 − 1.39)
ωs = arccos(−tan φ · tan δ)
Ra = (24·60/π) · Gsc · dr · [ωs · sin φ · sin δ + cos φ · cos δ · sin ωs]
```
- Raise `ValueError` when `lat_graus` is outside `[-66.5, 66.5]` (polar day/night is out of scope).
- Raise `ValueError` in `graus_dia` when `t_max_c < t_min_c`.

### R3 — Parsing (pure)
```python
def parse_resposta_open_meteo(resposta: Mapping[str, Any], hoje: date) -> tuple[ClimaDia, ...]:
    """Convert an Open-Meteo JSON response with a `daily` block into ClimaDia, sorted by date."""
```
- Reads `resposta["daily"]` arrays `time`, `shortwave_radiation_sum`, `temperature_2m_max`,
  `temperature_2m_min`, `temperature_2m_mean`, `et0_fao_evapotranspiration`,
  `precipitation_sum` (all the same length).
- `previsto = data > hoje`.
- A day with any `null` value is **skipped** (not filled).

### R4 — HTTP client
```python
VARIAVEIS_DIARIAS = (
    "shortwave_radiation_sum", "temperature_2m_max", "temperature_2m_min",
    "temperature_2m_mean", "et0_fao_evapotranspiration", "precipitation_sum",
)

def buscar_clima(lat: float, lon: float, data_inicio: date, data_fim: date,
                 hoje: date, timezone: str) -> tuple[ClimaDia, ...]: ...

def et0_media_anual_mm_dia(lat: float, lon: float, hoje: date, timezone: str) -> float: ...
```
- Use `httpx.get(..., timeout=30.0)` and `response.raise_for_status()`.
- `buscar_clima` requires `data_inicio <= data_fim <= hoje + 15 days` (else `ValueError`).
  - Part A (only if `data_inicio < hoje - 90 days`): archive endpoint
    `https://archive-api.open-meteo.com/v1/archive` with `latitude`, `longitude`,
    `start_date=data_inicio`, `end_date=min(data_fim, hoje - 91 days)`,
    `daily=",".join(VARIAVEIS_DIARIAS)`, `timezone`.
  - Part B (only if `data_fim >= hoje - 90 days`): forecast endpoint
    `https://api.open-meteo.com/v1/forecast` with `latitude`, `longitude`, `past_days=92`,
    `forecast_days=16`, `daily=...`, `timezone`; keep only days in
    `[max(data_inicio, hoje - 90 days), data_fim]`.
  - Return parts A and B concatenated, sorted by date, without duplicate dates.
- `et0_media_anual_mm_dia`: archive endpoint for the 365 days ending at `hoje - 6 days`
  (the archive lags about 5 days), `daily=et0_fao_evapotranspiration`; return the arithmetic
  mean of the non-null values. Raise `ValueError` if fewer than 300 values are non-null.

## Constants and parameters
| Name | Value | Unit | Source |
|---|---|---|---|
| `GSC_MJ_M2_MIN` (solar constant) | 0.0820 | MJ m⁻² min⁻¹ | Allen et al. (1998), FAO-56, eq. 21 |
| 0.033, 0.409, 1.39 | — | — | FAO-56, eqs. 23–24 |
| Forecast `past_days` / `forecast_days` | 92 / 16 | days | Open-Meteo API maximums |
| Archive lag | 6 | days | Open-Meteo docs: ERA5 is available with ~5 days delay |

## Validation rules
- `radiacao_extraterrestre_mj_m2_dia(70.0, …)` raises `ValueError`.
- `graus_dia(20, 25, 15)` raises `ValueError`.
- `buscar_clima` with `data_fim > hoje + 15 days` raises `ValueError`.
- HTTP errors propagate as `httpx.HTTPStatusError` (no retry, no swallowing).

## Testing — who does what
Write your own tests in `tests/sensing/`, as a smoke check. Test the pure functions directly;
test `buscar_clima` and `et0_media_anual_mm_dia` by monkeypatching `httpx.get` with a fake
response. No test may call the real network. You will NOT be given a test file to copy.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `ClimaDia` is frozen/slotted with the 8 fields above
- [ ] FAO-56 example 8 reproduced (see Worked example) within ±0.1
- [ ] `graus_dia(31, 21, 15) == 11.0`
- [ ] `parse_resposta_open_meteo` skips days with `null` and marks future days `previsto=True`
- [ ] `buscar_clima` issues only the forecast request when `data_inicio >= hoje - 90 days`
- [ ] No test touches the network
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml` (`httpx` is already there)

## Worked example
FAO-56 example 8: latitude 20° S (`lat_graus = -20.0`) on 3 September (day of year 246):
`Ra ≈ 32.2 MJ m⁻² day⁻¹`.
Degree-days: `t_max = 31 °C`, `t_min = 21 °C`, `t_base = 15 °C` → `(31 + 21)/2 − 15 = 11.0`.

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-011.md`.

## Out of scope
- Do NOT compute ET0 yourself (Open-Meteo already returns FAO-56 ET0)
- Do NOT use INMET or any other weather source
- Do NOT interpolate, fill or extrapolate missing days
- Do NOT add caching, retries, async code or new dependencies
- Do NOT touch the database or any other module

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions for R2 and R3; I/O only in R4
- Variable names carry their unit; domain nouns stay in Portuguese; docstrings in English
- `__init__.py` files stay empty; maximum 300 lines per file
