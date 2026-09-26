# SPEC-012 — SAFER daily forage accumulation rate (pure functions)

## Context
SAFER is a published algorithm that estimates how many kilograms of grass dry matter a hectare
produces per day, from one clean satellite observation (red and near-infrared reflectance, which
give NDVI and surface albedo) and that day's weather. The system runs it once per paddock per
day, holding the latest clean satellite observation and using each day's weather. This spec
implements the equation chain as pure functions with runtime sanity checks.

## Domain vocabulary
- `ndvi` — vegetation index from red and near-infrared reflectance, in (0, 1].
- `refletancia_red` / `refletancia_nir` — surface reflectance of the red / near-infrared band, 0–1.
- `rg` — global solar radiation. `ra` — top-of-atmosphere radiation. `tau_sw` = rg / ra.
- `etf` — evapotranspiration fraction. `rfa` — photosynthetically active radiation.
- `rue_max` — maximum radiation-use efficiency of the grass, g per MJ.
- `taxa_acumulo` — forage accumulation rate, kg dry matter per ha per day.

## Reading scope — read this file only
This spec is self-contained. Read **only** this file and the files listed below under
`Files to create or modify`. Do not open, read or modify anything under `revisoes/`,
`docs/` or `tests/conformance/`. Touching any file outside the list is a spec violation
and will be reported as such.

## Files to create or modify
- CREATE `src/seugado/sensing/safer.py`
- CREATE `tests/sensing/test_safer.py`

## Requirements

### R1 — Result type and error
```python
class SaferForaDaFaixa(ValueError):
    """Raised when an intermediate or final SAFER value leaves its sanity range."""

@dataclass(frozen=True, slots=True)
class ResultadoSafer:
    albedo: float
    rn_w_m2: float
    t0_c: float
    etf: float
    rfa_absorvida_w_m2: float
    taxa_acumulo_kg_ms_ha_dia: float
```

### R2 — Main function
```python
def taxa_acumulo_safer(
    ndvi: float,
    refletancia_red: float,
    refletancia_nir: float,
    rg_mj_m2_dia: float,
    t_media_c: float,
    ra_mj_m2_dia: float,
    et0_media_anual_mm_dia: float,
    rue_max_g_por_mj: float,
) -> ResultadoSafer:
    """Run the SAFER chain for one day and one paddock."""
```
Compute, in this order (σ = 5.67e-8):
```
albedo  = 0.08 + 0.41·refletancia_red + 0.14·refletancia_nir
rg_w    = rg_mj_m2_dia · 1e6 / 86400                      # daily mean W/m²
tau_sw  = rg_mj_m2_dia / ra_mj_m2_dia
a_l     = 6.99·t_media_c − 39.93
rn      = (1 − albedo)·rg_w − a_l·tau_sw                  # Slob equation, W/m²
eps_a   = 0.94·(−ln tau_sw)^0.11                          # atmospheric emissivity
eps_0   = 0.06·ln(ndvi) + 1.00                            # surface emissivity
ta_k    = t_media_c + 273.15
rl_down = eps_a·σ·ta_k⁴
rl_up   = (1 − albedo)·rg_w + rl_down − rn                # residual method
t0_c    = (rl_up / (eps_0·σ))^0.25 − 273.15               # surface temperature, °C
etf     = exp(1.80 − 0.008·(t0_c / (albedo·ndvi))) · (et0_media_anual_mm_dia / 5)
f_rfa   = 1.257·ndvi − 0.161
rfa_abs = f_rfa · 0.44 · rg_w                              # W/m²
taxa    = rue_max_g_por_mj · etf · rfa_abs · 0.864         # kg DM/ha/day
```
**The temperature in the ETf equation is in °C, not kelvin.** The factor 0.864 converts
(g/MJ)·(W/m²) to kg/ha/day.

### R3 — Sanity checks (fail loudly)
- Inputs: `0 < ndvi <= 1`; `0 <= refletancia_red, refletancia_nir <= 1`;
  `rg_mj_m2_dia > 0`; `ra_mj_m2_dia > 0`; `0 < tau_sw < 1`; `rue_max_g_por_mj > 0`;
  `et0_media_anual_mm_dia > 0`. Violation → plain `ValueError`.
- `f_rfa <= 0` → taxa is `0.0` (bare soil: no absorbed PAR), and the ETf check below is skipped.
- `etf` outside `[0.05, 1.3]` → `SaferForaDaFaixa`.
- `taxa` outside `[0, 150]` → `SaferForaDaFaixa`.

## Constants and parameters
| Name | Value | Source |
|---|---|---|
| Albedo `a`, `b`, `c` | 0.08, 0.41, 0.14 | Teixeira et al., SAFER (Embrapa), coefficients for red/NIR bands |
| `a_L` = d·Ta − e | d = 6.99, e = 39.93 | Teixeira et al. (2010, 2012), via Ramos (UNIVASF) |
| `a_A`, `b_A` | 0.94, 0.11 | `05-PARAMETROS-CULTIVARES.md`, SAFER constants |
| `a_0`, `b_0` | 0.06, 1.00 | idem |
| σ | 5.67e-8 W m⁻² K⁻⁴ | Stefan-Boltzmann |
| `a_sf`, `b_sf` | 1.80, −0.008 | idem |
| RFA fraction | 0.44 | idem |
| `a_F`, `b_F` | 1.257, −0.161 | idem |
| Conversion | 0.864 | idem |
| ET0 reference | 5 mm/day | idem |
| ETf range | [0.05, 1.3] | `05`, sanity ranges |
| Taxa range | [0, 150] kg/ha/day | `05`, sanity ranges |

## Validation rules
See R3. Every raised error message names the variable and its value.

## Testing — who does what
Write your own tests in `tests/sensing/`, as a smoke check that your code runs and behaves as
described. Keep them short. You will NOT be given a test file to copy, and you must not
wait for one.

Your tests are not the verification of record. A separate agent, which never sees this spec's
worked example, writes an independent conformance suite in `tests/conformance/` and decides
whether the work is accepted. So do not write code that targets a specific assertion: satisfy
the requirement, not the test.

Do not create, modify or delete anything under `tests/conformance/`.

## Acceptance criteria
- [ ] `taxa_acumulo_safer` has the exact signature above and returns `ResultadoSafer`
- [ ] Worked example reproduced within the stated tolerances
- [ ] `SaferForaDaFaixa` is a subclass of `ValueError`
- [ ] ETf is computed with `t0_c` in °C
- [ ] Module imports only `math`, `dataclasses` (no numpy, no I/O)
- [ ] `uv run ruff check .`, `uv run mypy` and `uv run pytest` pass
- [ ] No new dependency added to `pyproject.toml`

## Worked example
`ndvi=0.80`, `refletancia_red=0.04`, `refletancia_nir=0.35`, `rg_mj_m2_dia=20.0`,
`t_media_c=26.0`, `ra_mj_m2_dia=35.0`, `et0_media_anual_mm_dia=4.5`, `rue_max_g_por_mj=2.31`:
- `albedo = 0.1454` (±0.0005)
- `rn_w_m2 = 116.79` (±0.5)
- `t0_c = 31.44` (±0.1)
- `etf = 0.627` (±0.005)
- `rfa_absorvida_w_m2 = 86.02` (±0.3)
- `taxa_acumulo_kg_ms_ha_dia = 107.6` (±1.0)

## Acceptance kit (tester only — NEVER paste into the coding agent)
Lives in `revisoes/KIT-ACEITE-012.md`.

## Out of scope
- Do NOT fetch weather or satellite data
- Do NOT convert accumulation to canopy height or forage mass
- Do NOT add senescence, water balance or soil moisture
- Do NOT vectorise with numpy or process images
- Do NOT catch `SaferForaDaFaixa` inside this module
- Do NOT add logging frameworks or new dependencies

## Style constraints
- Python 3.12, type hints on every public function
- Pure functions only: no I/O, no global state, no side effects
- Variable names carry their unit where they have one
- Docstrings and comments in English; `__init__.py` files stay empty; max 300 lines
