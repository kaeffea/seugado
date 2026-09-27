"""SAFER daily forage accumulation rate (pure functions)."""

from dataclasses import dataclass
from math import exp, log

_STEFAN_BOLTZMANN_W_M2_K4 = 5.67e-8
_KELVIN_OFFSET_C = 273.15
_SEGUNDOS_DIA = 86400
_ETF_MINIMO = 0.05
_ETF_MAXIMO = 1.3
_TAXA_MAXIMA_KG_MS_HA_DIA = 150.0


class SaferForaDaFaixa(ValueError):
    """Raised when an intermediate or final SAFER value leaves its sanity range."""


@dataclass(frozen=True, slots=True)
class ResultadoSafer:
    """SAFER chain outputs for one day and one paddock."""

    albedo: float
    rn_w_m2: float
    t0_c: float
    etf: float
    rfa_absorvida_w_m2: float
    taxa_acumulo_kg_ms_ha_dia: float


def taxa_acumulo_safer(  # noqa: PLR0913, PLR0917 — arity is the R2 contract
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
    if not 0.0 < ndvi <= 1.0:
        raise ValueError(f"ndvi {ndvi} outside (0, 1]")
    if not 0.0 <= refletancia_red <= 1.0:
        raise ValueError(f"refletancia_red {refletancia_red} outside [0, 1]")
    if not 0.0 <= refletancia_nir <= 1.0:
        raise ValueError(f"refletancia_nir {refletancia_nir} outside [0, 1]")
    if not rg_mj_m2_dia > 0.0:
        raise ValueError(f"rg_mj_m2_dia {rg_mj_m2_dia} must be positive")
    if not ra_mj_m2_dia > 0.0:
        raise ValueError(f"ra_mj_m2_dia {ra_mj_m2_dia} must be positive")
    if not rue_max_g_por_mj > 0.0:
        raise ValueError(f"rue_max_g_por_mj {rue_max_g_por_mj} must be positive")
    if not et0_media_anual_mm_dia > 0.0:
        raise ValueError(f"et0_media_anual_mm_dia {et0_media_anual_mm_dia} must be positive")

    albedo = 0.08 + 0.41 * refletancia_red + 0.14 * refletancia_nir
    rg_w_m2 = rg_mj_m2_dia * 1e6 / _SEGUNDOS_DIA
    tau_sw = rg_mj_m2_dia / ra_mj_m2_dia
    if not 0.0 < tau_sw < 1.0:
        raise ValueError(f"tau_sw {tau_sw} outside (0, 1)")
    a_l = 6.99 * t_media_c - 39.93
    rn_w_m2 = (1 - albedo) * rg_w_m2 - a_l * tau_sw
    eps_a = 0.94 * (-log(tau_sw)) ** 0.11
    eps_0 = 0.06 * log(ndvi) + 1.00
    ta_k = t_media_c + _KELVIN_OFFSET_C
    rl_down_w_m2 = eps_a * _STEFAN_BOLTZMANN_W_M2_K4 * ta_k**4
    rl_up_w_m2 = (1 - albedo) * rg_w_m2 + rl_down_w_m2 - rn_w_m2
    t0_c = (rl_up_w_m2 / (eps_0 * _STEFAN_BOLTZMANN_W_M2_K4)) ** 0.25 - _KELVIN_OFFSET_C
    etf = exp(1.80 - 0.008 * (t0_c / (albedo * ndvi))) * (et0_media_anual_mm_dia / 5)
    f_rfa = 1.257 * ndvi - 0.161
    if f_rfa <= 0.0:
        return ResultadoSafer(albedo, rn_w_m2, t0_c, etf, 0.0, 0.0)
    if not _ETF_MINIMO <= etf <= _ETF_MAXIMO:
        raise SaferForaDaFaixa(f"etf {etf} outside [0.05, 1.3]")
    rfa_abs_w_m2 = f_rfa * 0.44 * rg_w_m2
    taxa_kg_ms_ha_dia = rue_max_g_por_mj * etf * rfa_abs_w_m2 * 0.864
    if not 0.0 <= taxa_kg_ms_ha_dia <= _TAXA_MAXIMA_KG_MS_HA_DIA:
        raise SaferForaDaFaixa(f"taxa {taxa_kg_ms_ha_dia} outside [0, 150]")
    return ResultadoSafer(albedo, rn_w_m2, t0_c, etf, rfa_abs_w_m2, taxa_kg_ms_ha_dia)
