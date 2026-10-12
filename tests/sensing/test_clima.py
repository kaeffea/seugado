"""Smoke checks for the weather module (no network: httpx.get is faked)."""

import dataclasses
from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from typing import Any

import httpx
import pytest

from seugado.sensing import clima
from seugado.sensing.clima import (
    ClimaDia,
    buscar_clima,
    et0_media_anual_mm_dia,
    graus_dia,
    parse_resposta_open_meteo,
    radiacao_extraterrestre_mj_m2_dia,
)

HOJE = date(2026, 9, 27)
LAT, LON, TZ = -3.7, -38.5, "America/Fortaleza"


class RespostaFalsa:
    """Minimal httpx.Response stub: json() returns a fixed payload."""

    def __init__(self, corpo: dict[str, Any]) -> None:
        self._corpo = corpo

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._corpo


def _bloco(datas: list[date], nulo_em: set[int] | None = None) -> dict[str, Any]:
    """Build a daily block with constant values; indices in nulo_em get null et0."""
    nulo = nulo_em or set()
    n = len(datas)
    return {
        "daily": {
            "time": [d.isoformat() for d in datas],
            "shortwave_radiation_sum": [20.0] * n,
            "temperature_2m_max": [31.0] * n,
            "temperature_2m_min": [21.0] * n,
            "temperature_2m_mean": [26.0] * n,
            "et0_fao_evapotranspiration": [None if i in nulo else 4.5 for i in range(n)],
            "precipitation_sum": [0.0] * n,
        }
    }


def _fake_get(corpos: list[dict[str, Any]], chamadas: list[dict[str, Any]]) -> Any:
    """Fake httpx.get serving one payload per call and recording url/params."""

    def fake(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> RespostaFalsa:
        chamadas.append({"url": url, "params": params, **kwargs})
        return RespostaFalsa(corpos[len(chamadas) - 1])

    return fake


def test_clima_dia_frozen_slotted_with_eight_fields() -> None:
    c = ClimaDia(date(2026, 9, 27), 20.0, 31.0, 21.0, 26.0, 4.5, 0.0, False)
    assert [f.name for f in dataclasses.fields(ClimaDia)] == [
        "data",
        "rg_mj_m2_dia",
        "t_max_c",
        "t_min_c",
        "t_media_c",
        "et0_mm_dia",
        "chuva_mm",
        "previsto",
    ]
    assert not hasattr(c, "__dict__")
    with pytest.raises(FrozenInstanceError):
        c.chuva_mm = 1.0  # type: ignore[misc]  # intentional: verifying frozen raises


def test_radiacao_reproduces_fao56_example_8() -> None:
    assert radiacao_extraterrestre_mj_m2_dia(-20.0, date(2021, 9, 3)) == pytest.approx(
        32.2, abs=0.1
    )


def test_radiacao_rejects_polar_latitudes() -> None:
    with pytest.raises(ValueError):
        radiacao_extraterrestre_mj_m2_dia(70.0, HOJE)
    with pytest.raises(ValueError):
        radiacao_extraterrestre_mj_m2_dia(-70.0, HOJE)
    assert radiacao_extraterrestre_mj_m2_dia(66.5, date(2021, 3, 20)) > 0
    assert radiacao_extraterrestre_mj_m2_dia(-66.5, date(2021, 3, 20)) > 0


def test_graus_dia() -> None:
    assert graus_dia(31, 21, 15) == 11.0
    assert graus_dia(16, 14, 15) == 0.0
    with pytest.raises(ValueError):
        graus_dia(20, 25, 15)


def test_parse_skips_null_and_marks_forecast() -> None:
    corpo = _bloco([HOJE - timedelta(days=1), HOJE, HOJE + timedelta(days=1)], {1})
    dias = parse_resposta_open_meteo(corpo, HOJE)
    assert [c.data for c in dias] == [HOJE - timedelta(days=1), HOJE + timedelta(days=1)]
    assert [c.previsto for c in dias] == [False, True]
    assert dias[0].et0_mm_dia == 4.5


def test_buscar_clima_uses_only_forecast_in_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inicio, fim = HOJE - timedelta(days=10), HOJE + timedelta(days=5)
    datas = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "get", _fake_get([_bloco(datas)], chamadas))
    dias = buscar_clima(LAT, LON, inicio, fim, HOJE, TZ)
    assert len(chamadas) == 1
    assert chamadas[0]["url"] == "https://api.open-meteo.com/v1/forecast"
    assert chamadas[0]["params"]["past_days"] == 92
    assert chamadas[0]["params"]["forecast_days"] == 16
    assert chamadas[0]["timeout"] == 20.0
    assert [c.data for c in dias] == datas
    assert [c.previsto for c in dias] == [d > HOJE for d in datas]


def test_buscar_clima_merges_archive_and_forecast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inicio, fim = HOJE - timedelta(days=100), HOJE + timedelta(days=2)
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(
        httpx,
        "get",
        _fake_get(
            [
                _bloco([HOJE - timedelta(days=100), HOJE - timedelta(days=95)]),
                _bloco(
                    [
                        HOJE - timedelta(days=91),
                        HOJE - timedelta(days=90),
                        HOJE,
                        fim,
                        fim + timedelta(days=1),
                    ]
                ),
            ],
            chamadas,
        ),
    )
    dias = buscar_clima(LAT, LON, inicio, fim, HOJE, TZ)
    assert [c["url"] for c in chamadas] == [
        "https://archive-api.open-meteo.com/v1/archive",
        "https://api.open-meteo.com/v1/forecast",
    ]
    assert chamadas[0]["params"]["start_date"] == inicio.isoformat()
    assert chamadas[0]["params"]["end_date"] == (HOJE - timedelta(days=91)).isoformat()
    assert [c.data for c in dias] == [
        HOJE - timedelta(days=100),
        HOJE - timedelta(days=95),
        HOJE - timedelta(days=90),
        HOJE,
        fim,
    ]


def test_buscar_clima_rejects_bad_range_without_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("must not touch the network")

    monkeypatch.setattr(httpx, "get", _boom)
    with pytest.raises(ValueError):
        buscar_clima(LAT, LON, HOJE, HOJE + timedelta(days=16), HOJE, TZ)
    with pytest.raises(ValueError):
        buscar_clima(LAT, LON, HOJE, HOJE - timedelta(days=1), HOJE, TZ)


def test_buscar_clima_propagates_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class Erro(RespostaFalsa):
        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"),
                response=httpx.Response(500),
            )

    monkeypatch.setattr(httpx, "get", lambda *a, **k: Erro({}))
    with pytest.raises(httpx.HTTPStatusError):
        buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)


def test_et0_media_anual(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    valores = [4.0] * 360 + [None] * 5
    corpo = {"daily": {"et0_fao_evapotranspiration": valores}}

    def fake(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> RespostaFalsa:
        chamadas.append({"url": url, "params": params, **kwargs})
        return RespostaFalsa(corpo)

    monkeypatch.setattr(httpx, "get", fake)
    assert et0_media_anual_mm_dia(LAT, LON, HOJE, TZ) == pytest.approx(4.0)
    assert chamadas[0]["url"] == "https://archive-api.open-meteo.com/v1/archive"
    assert chamadas[0]["params"]["start_date"] == (HOJE - timedelta(days=370)).isoformat()
    assert chamadas[0]["params"]["end_date"] == (HOJE - timedelta(days=6)).isoformat()
    assert chamadas[0]["params"]["daily"] == "et0_fao_evapotranspiration"


def test_et0_media_anual_rejects_sparse_series(monkeypatch: pytest.MonkeyPatch) -> None:
    corpo = {"daily": {"et0_fao_evapotranspiration": [4.0] * 299 + [None] * 66}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: RespostaFalsa(corpo))
    with pytest.raises(ValueError):
        et0_media_anual_mm_dia(LAT, LON, HOJE, TZ)


def _http(
    status: int, url: str, corpo: dict[str, Any] | None = None, retry_after: str | None = None
) -> Any:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return httpx.Response(
        status, json=corpo or {}, headers=headers, request=httpx.Request("GET", url)
    )


def _sequencia(respostas: list[Any], chamadas: list[dict[str, Any]]) -> Any:
    def fake(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        chamadas.append({"url": url, "params": params, **kwargs})
        return respostas[len(chamadas) - 1]

    return fake


_URL_PREVISAO = "https://api.open-meteo.com/v1/forecast"


def test_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    corpo = _bloco([HOJE])
    chamadas: list[dict[str, Any]] = []
    esperas: list[float] = []
    monkeypatch.setattr(clima, "_esperar", esperas.append)
    monkeypatch.setattr(
        httpx,
        "get",
        _sequencia(
            [_http(429, _URL_PREVISAO)] * 2 + [_http(200, _URL_PREVISAO, corpo)],
            chamadas,
        ),
    )
    dias = buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert [c.data for c in dias] == [HOJE]
    assert len(chamadas) == 3
    assert esperas == [2.0, 5.0]


def test_retries_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    corpo = _bloco([HOJE])
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(
        httpx,
        "get",
        _sequencia([_http(503, _URL_PREVISAO), _http(200, _URL_PREVISAO, corpo)], chamadas),
    )
    assert len(buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)) == 1
    assert len(chamadas) == 2


def test_four_429_raise_after_four_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    esperas: list[float] = []
    monkeypatch.setattr(clima, "_esperar", esperas.append)
    monkeypatch.setattr(
        httpx, "get", _sequencia([_http(429, _URL_PREVISAO) for _ in range(5)], chamadas)
    )
    with pytest.raises(httpx.HTTPStatusError) as info:
        buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert info.value.response.status_code == 429
    assert len(chamadas) == 4
    assert esperas == [2.0, 5.0, 10.0]


def test_does_not_retry_other_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    monkeypatch.setattr(httpx, "get", _sequencia([_http(400, _URL_PREVISAO)] * 2, chamadas))
    with pytest.raises(httpx.HTTPStatusError):
        buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert len(chamadas) == 1


def test_retry_after_is_respected_and_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    esperas: list[float] = []
    monkeypatch.setattr(clima, "_esperar", esperas.append)
    monkeypatch.setattr(
        httpx,
        "get",
        _sequencia(
            [
                _http(429, _URL_PREVISAO, retry_after="7"),
                _http(429, _URL_PREVISAO, retry_after="120"),
                _http(429, _URL_PREVISAO, retry_after="logo"),
                _http(200, _URL_PREVISAO, _bloco([HOJE])),
            ],
            chamadas,
        ),
    )
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert esperas == [7.0, 30.0, 10.0]


def test_same_query_uses_cache_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    corpo = _http(200, _URL_PREVISAO, _bloco([HOJE]))
    monkeypatch.setattr(httpx, "get", _sequencia([corpo], chamadas))
    primeira = buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    segunda = buscar_clima(LAT + 0.001, LON - 0.001, HOJE, HOJE, HOJE, TZ)  # mesmo lugar
    assert primeira == segunda
    assert len(chamadas) == 1


def test_cache_separates_place_and_day(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    corpo = _bloco([HOJE, HOJE + timedelta(days=1)])
    monkeypatch.setattr(
        httpx, "get", _sequencia([_http(200, _URL_PREVISAO, corpo) for _ in range(3)], chamadas)
    )
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    buscar_clima(LAT + 0.5, LON, HOJE, HOJE, HOJE, TZ)
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE + timedelta(days=1), TZ)
    assert len(chamadas) == 3


def test_cache_expires_after_six_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    relogio = [1000.0]
    monkeypatch.setattr(clima, "_agora_s", lambda: relogio[0])
    corpo = _http(200, _URL_PREVISAO, _bloco([HOJE]))
    monkeypatch.setattr(httpx, "get", _sequencia([corpo, corpo], chamadas))
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    relogio[0] += 6 * 3600 - 1
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert len(chamadas) == 1
    relogio[0] += 2
    buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert len(chamadas) == 2


def test_failures_are_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[dict[str, Any]] = []
    respostas = [_http(500, _URL_PREVISAO) for _ in range(4)]
    respostas.append(_http(200, _URL_PREVISAO, _bloco([HOJE])))
    monkeypatch.setattr(httpx, "get", _sequencia(respostas, chamadas))
    with pytest.raises(httpx.HTTPStatusError):
        buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)
    assert len(buscar_clima(LAT, LON, HOJE, HOJE, HOJE, TZ)) == 1
