"""Daily weather client (Open-Meteo) and solar/thermal-time formulas."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from math import acos, cos, pi, radians, sin, tan
from typing import Any, cast

import httpx

GSC_MJ_M2_MIN = 0.0820

VARIAVEIS_DIARIAS = (
    "shortwave_radiation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "et0_fao_evapotranspiration",
    "precipitation_sum",
)

_URL_PREVISAO = "https://api.open-meteo.com/v1/forecast"
_URL_ARQUIVO = "https://archive-api.open-meteo.com/v1/archive"

_LAT_MAX_GRAUS = 66.5
_ALCANCE_PREVISAO_DIAS = 15
_PASSADO_PREVISAO_DIAS = 90
_PASSADO_ARQUIVO_DIAS = 91
_ATRASO_ARQUIVO_DIAS = 6
_JANELA_ANUAL_DIAS = 365
_MINIMO_ET0_NAO_NULO = 300

_CHAVES_DIARIAS = ("time", *VARIAVEIS_DIARIAS)


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


def radiacao_extraterrestre_mj_m2_dia(lat_graus: float, data: date) -> float:
    """Daily extraterrestrial radiation Ra (FAO-56, eq. 21)."""
    if not -_LAT_MAX_GRAUS <= lat_graus <= _LAT_MAX_GRAUS:
        raise ValueError(f"lat_graus {lat_graus} outside [-66.5, 66.5]")
    dia_ano = data.timetuple().tm_yday
    angulo_rad = 2 * pi * dia_ano / 365
    dr = 1 + 0.033 * cos(angulo_rad)
    delta_rad = 0.409 * sin(angulo_rad - 1.39)
    phi_rad = radians(lat_graus)
    omega_s_rad = acos(-tan(phi_rad) * tan(delta_rad))
    return (
        (24 * 60 / pi)
        * GSC_MJ_M2_MIN
        * dr
        * (
            omega_s_rad * sin(phi_rad) * sin(delta_rad)
            + cos(phi_rad) * cos(delta_rad) * sin(omega_s_rad)
        )
    )


def graus_dia(t_max_c: float, t_min_c: float, temperatura_base_c: float) -> float:
    """Daily growing degree-days: max(0, (t_max + t_min)/2 - t_base)."""
    if t_max_c < t_min_c:
        raise ValueError(f"t_max_c {t_max_c} below t_min_c {t_min_c}")
    return max(0.0, (t_max_c + t_min_c) / 2 - temperatura_base_c)


def parse_resposta_open_meteo(
    resposta: Mapping[str, Any], hoje: date
) -> tuple[ClimaDia, ...]:
    """Convert an Open-Meteo JSON response with a `daily` block into ClimaDia, sorted by date."""
    bloco = resposta["daily"]
    dias: list[ClimaDia] = []
    for i in range(len(bloco["time"])):
        valores = [bloco[chave][i] for chave in _CHAVES_DIARIAS]
        if any(v is None for v in valores):
            continue
        dia = date.fromisoformat(valores[0])
        dias.append(
            ClimaDia(
                data=dia,
                rg_mj_m2_dia=float(valores[1]),
                t_max_c=float(valores[2]),
                t_min_c=float(valores[3]),
                t_media_c=float(valores[4]),
                et0_mm_dia=float(valores[5]),
                chuva_mm=float(valores[6]),
                previsto=dia > hoje,
            )
        )
    return tuple(sorted(dias, key=lambda c: c.data))


def _buscar(url: str, params: dict[str, Any]) -> Mapping[str, Any]:
    """GET a JSON body, raising HTTP errors to the caller."""
    resposta = httpx.get(url, params=params, timeout=30.0)
    resposta.raise_for_status()
    return cast("Mapping[str, Any]", resposta.json())


def buscar_clima(  # noqa: PLR0913, PLR0917 — arity is the R4 contract
    lat: float,
    lon: float,
    data_inicio: date,
    data_fim: date,
    hoje: date,
    timezone: str,
) -> tuple[ClimaDia, ...]:
    """Fetch daily weather for [data_inicio, data_fim] from archive and/or forecast."""
    if not (data_inicio <= data_fim <= hoje + timedelta(days=_ALCANCE_PREVISAO_DIAS)):
        raise ValueError("require data_inicio <= data_fim <= hoje + 15 days")
    por_data: dict[date, ClimaDia] = {}
    if data_inicio < hoje - timedelta(days=_PASSADO_PREVISAO_DIAS):
        fim_arquivo = min(data_fim, hoje - timedelta(days=_PASSADO_ARQUIVO_DIAS))
        corpo = _buscar(
            _URL_ARQUIVO,
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": data_inicio.isoformat(),
                "end_date": fim_arquivo.isoformat(),
                "daily": ",".join(VARIAVEIS_DIARIAS),
                "timezone": timezone,
            },
        )
        for clima in parse_resposta_open_meteo(corpo, hoje):
            por_data[clima.data] = clima
    if data_fim >= hoje - timedelta(days=_PASSADO_PREVISAO_DIAS):
        corpo = _buscar(
            _URL_PREVISAO,
            {
                "latitude": lat,
                "longitude": lon,
                "past_days": 92,
                "forecast_days": 16,
                "daily": ",".join(VARIAVEIS_DIARIAS),
                "timezone": timezone,
            },
        )
        inicio = max(data_inicio, hoje - timedelta(days=_PASSADO_PREVISAO_DIAS))
        for clima in parse_resposta_open_meteo(corpo, hoje):
            if inicio <= clima.data <= data_fim:
                por_data[clima.data] = clima
    return tuple(por_data[d] for d in sorted(por_data))


def et0_media_anual_mm_dia(lat: float, lon: float, hoje: date, timezone: str) -> float:
    """Mean daily FAO-56 ET0 over the 365 days ending 6 days ago (archive lag)."""
    fim = hoje - timedelta(days=_ATRASO_ARQUIVO_DIAS)
    inicio = fim - timedelta(days=_JANELA_ANUAL_DIAS - 1)
    corpo = _buscar(
        _URL_ARQUIVO,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": inicio.isoformat(),
            "end_date": fim.isoformat(),
            "daily": "et0_fao_evapotranspiration",
            "timezone": timezone,
        },
    )
    valores = [
        float(v) for v in corpo["daily"]["et0_fao_evapotranspiration"] if v is not None
    ]
    if len(valores) < _MINIMO_ET0_NAO_NULO:
        raise ValueError(f"only {len(valores)} non-null ET0 values, need 300")
    return sum(valores) / len(valores)
