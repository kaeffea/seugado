"""Smoke checks for Sentinel-2 sampling (no Earth Engine calls)."""

import json
import uuid
from datetime import date
from typing import Any

import pytest

from seugado.sensing import earth_engine
from seugado.sensing.earth_engine import (
    amostrar_sentinel2,
    extrair_observacoes,
    inicializar_earth_engine,
)

P1 = uuid.UUID("33333333-3333-3333-3333-333333333333")
P2 = uuid.UUID("33333333-3333-3333-3333-333333333334")
DIA = date(2026, 9, 20)
GEOMETRIA = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}


def _linha(piquete_id: Any = P1, **sobrescrever: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "piquete_id": str(piquete_id),
        "data": DIA.isoformat(),
        "red": 500,
        "nir": 3500,
        "pixels_validos": 40,
        "pixels_totais": 50,
    }
    base.update(sobrescrever)
    return base


def test_worked_example() -> None:
    linhas = [
        _linha(),
        _linha(red=600, nir=3000, pixels_validos=12),
        _linha(P2, nir=3000, pixels_validos=2),
    ]
    (obs,) = extrair_observacoes(linhas)
    assert obs.piquete_id == P1
    assert obs.data == DIA
    assert obs.ndvi == pytest.approx(0.75)
    assert obs.refletancia_red == pytest.approx(0.05)
    assert obs.refletancia_nir == pytest.approx(0.35)
    assert (obs.pixels_validos, obs.pixels_totais) == (40, 50)
    assert obs.pct_nuvem == pytest.approx(20.0)


def test_escala_somente_quando_necessario() -> None:
    (pequena,) = extrair_observacoes([_linha(red=0.05, nir=0.35)])
    assert (pequena.refletancia_red, pequena.refletancia_nir) == (0.05, 0.35)
    (mista,) = extrair_observacoes([_linha(red=0.05, nir=3500)])
    assert (mista.refletancia_red, mista.refletancia_nir) == pytest.approx((0.000005, 0.35))


@pytest.mark.parametrize(
    "sobrescrever",
    [
        {"pixels_validos": 2},
        {"red": None},
        {"nir": None},
        {"pixels_validos": None},
        {"red": 0.0, "nir": 0.0},
        {"red": 15000, "nir": 3500},
        {"red": 0.40, "nir": 0.30},
    ],
)
def test_linhas_ruins_sao_descartadas(sobrescrever: dict[str, Any]) -> None:
    assert extrair_observacoes([_linha(**sobrescrever)]) == []


def test_pct_nuvem_limitada_e_ordenacao() -> None:
    linhas = [
        _linha(P2, pixels_validos=30, pixels_totais=30),
        _linha(P1, pixels_validos=40, pixels_totais=30),
        _linha(P1, data="2026-09-21", pixels_validos=10),
    ]
    obs = extrair_observacoes(linhas)
    assert [(o.piquete_id, o.data) for o in obs] == [
        (P1, DIA),
        (P1, date(2026, 9, 21)),
        (P2, DIA),
    ]
    assert obs[0].pct_nuvem == pytest.approx(0.0)
    assert obs[2].pct_nuvem == pytest.approx(0.0)


def test_desempate_mantem_primeira() -> None:
    linhas = [_linha(red=500), _linha(red=600)]
    (obs,) = extrair_observacoes(linhas)
    assert obs.refletancia_red == pytest.approx(0.05)


def test_amostrar_rejeita_periodo_invertido() -> None:
    with pytest.raises(ValueError, match="data_inicio"):
        amostrar_sentinel2([(P1, GEOMETRIA)], DIA, DIA - date.resolution)


def test_amostrar_rejeita_geometria_nao_poligono() -> None:
    with pytest.raises(ValueError, match="Polygon"):
        amostrar_sentinel2([(P1, {"type": "Point", "coordinates": [0, 0]})], DIA, DIA)
    with pytest.raises(ValueError, match="Polygon"):
        amostrar_sentinel2([(P1, {"type": "Polygon", "coordinates": []})], DIA, DIA)
    assert amostrar_sentinel2([], DIA, DIA) == []


def test_inicializar_exige_variaveis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEUGADO_GEE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("SEUGADO_GEE_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="SEUGADO_GEE_SERVICE_ACCOUNT_JSON"):
        inicializar_earth_engine()
    monkeypatch.setenv("SEUGADO_GEE_SERVICE_ACCOUNT_JSON", "{}")
    with pytest.raises(RuntimeError, match="SEUGADO_GEE_PROJECT"):
        inicializar_earth_engine()


def test_inicializar_autentica(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: dict[str, Any] = {}

    class EeFalso:
        @staticmethod
        def ServiceAccountCredentials(email: str, key_data: str) -> tuple[str, str]:
            chamadas["credenciais"] = (email, key_data)
            return ("creds", email)

        @staticmethod
        def Initialize(credentials: Any, project: str) -> None:
            chamadas["init"] = (credentials, project)

    chave = json.dumps({"client_email": "gee@projeto.iam.gserviceaccount.com"})
    monkeypatch.setenv("SEUGADO_GEE_SERVICE_ACCOUNT_JSON", chave)
    monkeypatch.setenv("SEUGADO_GEE_PROJECT", "projeto")
    monkeypatch.setattr(earth_engine, "ee", EeFalso)
    inicializar_earth_engine()
    assert chamadas["credenciais"] == ("gee@projeto.iam.gserviceaccount.com", chave)
    assert chamadas["init"] == (("creds", "gee@projeto.iam.gserviceaccount.com"), "projeto")
