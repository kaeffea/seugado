"""Independent conformance suite covering SPEC-011 (Clima / Open-Meteo).

Written by the tester role (Antigravity), not the implementer.
Tests map to requirements of SPEC-011 and verification scenarios in KIT-ACEITE-011.
"""

import socket
from dataclasses import fields, is_dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from seugado.sensing.clima import (
    ClimaDia,
    buscar_clima,
    et0_media_anual_mm_dia,
    graus_dia,
    parse_resposta_open_meteo,
    radiacao_extraterrestre_mj_m2_dia,
)

ROOT = Path(__file__).resolve().parents[2]
CLIMA_PY = ROOT / "src" / "seugado" / "sensing" / "clima.py"


# ==============================================================================
# Structural Checks (KIT-ACEITE-011)
# ==============================================================================


def test_file_under_300_lines() -> None:
    """src/seugado/sensing/clima.py must stay under 300 lines."""
    lines = CLIMA_PY.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 300, f"File exceeds 300 lines: {len(lines)}"


def test_clima_dia_frozen_slotted_eight_fields() -> None:
    """ClimaDia is frozen/slotted with exact 8 fields in order."""
    assert is_dataclass(ClimaDia)
    params = getattr(ClimaDia, "__dataclass_params__", None)
    assert params is not None and params.frozen is True
    assert hasattr(ClimaDia, "__slots__")

    expected_fields = [
        "data",
        "rg_mj_m2_dia",
        "t_max_c",
        "t_min_c",
        "t_media_c",
        "et0_mm_dia",
        "chuva_mm",
        "previsto",
    ]
    actual_fields = [f.name for f in fields(ClimaDia)]
    assert actual_fields == expected_fields


def test_exact_endpoints_constants() -> None:
    """Endpoints match archive and forecast URLs exactly."""
    content = CLIMA_PY.read_text(encoding="utf-8")
    assert "https://archive-api.open-meteo.com/v1/archive" in content
    assert "https://api.open-meteo.com/v1/forecast" in content


@pytest.fixture(autouse=True)
def block_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no test calls the real network."""

    def _guarded_connect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network call attempted during tests!")

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)


# ==============================================================================
# Canonical Case (KIT-ACEITE-011)
# ==============================================================================


def test_canonical_case_fao56_example_8() -> None:
    """FAO-56 exemplo 8: Ra(-20°, 03/09) = 32,2 ± 0,1."""
    # Day 246 of 2021 (non-leap year) is September 3
    ra = radiacao_extraterrestre_mj_m2_dia(-20.0, date(2021, 9, 3))
    assert ra == pytest.approx(32.2, abs=0.1)


# ==============================================================================
# Casos que a spec não mostra (KIT-ACEITE-011)
# ==============================================================================


def test_hidden_case_1_ra_sao_miguel_dos_campos() -> None:
    """Caso 1: radiacao_extraterrestre_mj_m2_dia(-9.78, date(2026, 9, 28)) = 37,47 ± 0,1."""
    ra = radiacao_extraterrestre_mj_m2_dia(-9.78, date(2026, 9, 28))
    assert ra == pytest.approx(37.47, abs=0.1)


def test_hidden_case_2_graus_dia_base_above_mean() -> None:
    """Caso 2: graus_dia(14, 10, 15) = 0,0."""
    # (14 + 10) / 2 = 12. 12 - 15 = -3 -> max(0, -3) = 0.0
    gd = graus_dia(14.0, 10.0, 15.0)
    assert gd == pytest.approx(0.0)


def test_hidden_case_3_buscar_clima_120_dias_two_requests_no_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caso 3: buscar_clima hoje - 120 dias faz 2 requisições e não repete datas."""
    hoje = date(2026, 9, 27)
    data_inicio = hoje - timedelta(days=120)
    data_fim = hoje + timedelta(days=5)

    chamadas: list[dict[str, Any]] = []

    def make_response(datas: list[date]) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {
            "daily": {
                "time": [d.isoformat() for d in datas],
                "shortwave_radiation_sum": [18.0] * len(datas),
                "temperature_2m_max": [30.0] * len(datas),
                "temperature_2m_min": [20.0] * len(datas),
                "temperature_2m_mean": [25.0] * len(datas),
                "et0_fao_evapotranspiration": [4.0] * len(datas),
                "precipitation_sum": [0.0] * len(datas),
            }
        }
        return resp

    # Archive returns days from hoje - 120 to hoje - 91
    dias_arquivo = [data_inicio + timedelta(days=i) for i in range(30)]
    # Forecast returns days from hoje - 92 to hoje + 16 (overlaps with archive at -92, -91)
    dias_previsao = [hoje - timedelta(days=92) + timedelta(days=i) for i in range(109)]

    def fake_get(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> MagicMock:
        chamadas.append({"url": url, "params": params, **kwargs})
        if "archive" in url:
            return make_response(dias_arquivo)
        return make_response(dias_previsao)

    monkeypatch.setattr(httpx, "get", fake_get)

    resultado = buscar_clima(
        lat=-9.78,
        lon=-36.09,
        data_inicio=data_inicio,
        data_fim=data_fim,
        hoje=hoje,
        timezone="America/Maceio",
    )

    # 1. Deve fazer exatamente 2 requisições: arquivo e previsão
    assert len(chamadas) == 2
    urls = [c["url"] for c in chamadas]
    assert "https://archive-api.open-meteo.com/v1/archive" in urls
    assert "https://api.open-meteo.com/v1/forecast" in urls

    # 2. Não repete datas no resultado
    datas_resultado = [c.data for c in resultado]
    assert len(datas_resultado) == len(set(datas_resultado)), "Duplicate dates returned!"
    # Deve estar ordenado
    assert datas_resultado == sorted(datas_resultado)
    # Todos os dias dentro do intervalo solicitado
    assert datas_resultado[0] == data_inicio
    assert datas_resultado[-1] == data_fim


# ==============================================================================
# Validações Adicionais da Especificação (SPEC-011)
# ==============================================================================


def test_radiacao_polar_latitudes_raises_value_error() -> None:
    """radiacao_extraterrestre_mj_m2_dia raises ValueError outside [-66.5, 66.5]."""
    hoje = date(2026, 9, 27)
    with pytest.raises(ValueError, match="lat_graus"):
        radiacao_extraterrestre_mj_m2_dia(66.6, hoje)
    with pytest.raises(ValueError, match="lat_graus"):
        radiacao_extraterrestre_mj_m2_dia(-66.6, hoje)


def test_graus_dia_tmax_less_than_tmin_raises_value_error() -> None:
    """graus_dia raises ValueError when t_max_c < t_min_c."""
    with pytest.raises(ValueError):
        graus_dia(20.0, 25.0, 15.0)


def test_buscar_clima_invalid_range_raises_value_error() -> None:
    """buscar_clima requires data_inicio <= data_fim <= hoje + 15 days."""
    hoje = date(2026, 9, 27)
    with pytest.raises(ValueError):
        buscar_clima(-9.78, -36.09, hoje, hoje - timedelta(days=1), hoje, "America/Maceio")
    with pytest.raises(ValueError):
        buscar_clima(-9.78, -36.09, hoje, hoje + timedelta(days=16), hoje, "America/Maceio")


def test_http_errors_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP errors propagate as httpx.HTTPStatusError without being swallowed."""
    hoje = date(2026, 9, 27)

    def fake_get_error(*args: Any, **kwargs: Any) -> MagicMock:
        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(),
        )
        return resp

    monkeypatch.setattr(httpx, "get", fake_get_error)

    with pytest.raises(httpx.HTTPStatusError):
        buscar_clima(-9.78, -36.09, hoje, hoje, hoje, "America/Maceio")


def test_parse_resposta_skips_null_days() -> None:
    """parse_resposta_open_meteo skips days containing null values in any variable."""
    hoje = date(2026, 9, 27)
    resp = {
        "daily": {
            "time": ["2026-09-26", "2026-09-27", "2026-09-28"],
            "shortwave_radiation_sum": [20.0, None, 22.0],
            "temperature_2m_max": [30.0, 31.0, 32.0],
            "temperature_2m_min": [20.0, 21.0, 22.0],
            "temperature_2m_mean": [25.0, 26.0, 27.0],
            "et0_fao_evapotranspiration": [4.0, 4.5, 5.0],
            "precipitation_sum": [0.0, 0.0, 0.0],
        }
    }
    dias = parse_resposta_open_meteo(resp, hoje)
    assert len(dias) == 2
    assert [d.data for d in dias] == [date(2026, 9, 26), date(2026, 9, 28)]
    assert dias[0].previsto is False
    assert dias[1].previsto is True


def test_et0_media_anual_requires_at_least_300_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """et0_media_anual_mm_dia raises ValueError if fewer than 300 non-null values."""
    hoje = date(2026, 9, 27)
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    # 299 valid values, 66 nulls
    resp.json.return_value = {
        "daily": {"et0_fao_evapotranspiration": [4.0] * 299 + [None] * 66}
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: resp)

    with pytest.raises(ValueError, match="300"):
        et0_media_anual_mm_dia(-9.78, -36.09, hoje, "America/Maceio")
