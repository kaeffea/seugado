"""Smoke checks for reading ingestion (no Earth Engine, no database)."""

import json
import uuid
from datetime import date, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.sensing import ingestao
from seugado.sensing.earth_engine import ObservacaoSatelite
from seugado.sensing.ingestao import ingerir_leituras

FAZENDA = uuid.UUID("11111111-1111-1111-1111-111111111111")
P1 = uuid.UUID("33333333-3333-3333-3333-333333333333")
DIA = date(2026, 9, 20)
GEOMETRIA = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}


class CursorFalso:
    """Cursor stub: fixed piquete rows, fixed set of stored idempotency keys."""

    def __init__(self, piquetes: list[tuple[Any, Any]], existentes: set[str]) -> None:
        self._piquetes = piquetes
        self._existentes = existentes
        self._chave: str | None = None

    def __enter__(self) -> "CursorFalso":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        if "estado_piquete" in sql:
            self._chave = None
        else:
            self._chave = str(params[1])

    def fetchall(self) -> list[tuple[Any, Any]]:
        return self._piquetes

    def fetchone(self) -> tuple[int] | None:
        assert self._chave is not None
        return (1,) if self._chave in self._existentes else None


class ConexaoFalsa:
    """Connection stub whose commit() fails the test."""

    def __init__(self, piquetes: list[tuple[Any, Any]], existentes: set[str]) -> None:
        self._cursor = CursorFalso(piquetes, existentes)

    def cursor(self) -> CursorFalso:
        return self._cursor

    def commit(self) -> None:
        raise AssertionError("ingerir_leituras must not commit")


def _obs(piquete_id: uuid.UUID = P1, dia: date = DIA) -> ObservacaoSatelite:
    return ObservacaoSatelite(
        piquete_id=piquete_id,
        data=dia,
        ndvi=0.75,
        refletancia_red=0.05,
        refletancia_nir=0.35,
        pixels_validos=40,
        pixels_totais=50,
        pct_nuvem=20.0,
    )


def test_sem_piquetes_retorna_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("must not reach Earth Engine")

    monkeypatch.setattr(ingestao, "inicializar_earth_engine", _boom)
    monkeypatch.setattr(ingestao, "amostrar_sentinel2", _boom)
    monkeypatch.setattr(ingestao, "registrar_evento", _boom)
    conn = ConexaoFalsa([], set())
    assert ingerir_leituras(conn, FAZENDA, DIA, DIA) == 0  # type: ignore[arg-type]


def test_registra_somente_novas(monkeypatch: pytest.MonkeyPatch) -> None:
    existentes = {f"leitura:{P1}:{DIA.isoformat()}"}
    conn = ConexaoFalsa([(P1, json.dumps(GEOMETRIA))], existentes)
    chamadas_init: list[None] = []
    registradas: list[dict[str, Any]] = []
    obs_nova = _obs(dia=date(2026, 9, 25))
    monkeypatch.setattr(
        ingestao, "inicializar_earth_engine", lambda: chamadas_init.append(None)
    )
    monkeypatch.setattr(ingestao, "amostrar_sentinel2", lambda *a, **k: [_obs(), obs_nova])
    monkeypatch.setattr(
        ingestao, "registrar_evento", lambda *a, **k: registradas.append({"a": a, "k": k})
    )
    assert ingerir_leituras(conn, FAZENDA, DIA, date(2026, 9, 25)) == 1  # type: ignore[arg-type]
    assert chamadas_init == [None]
    assert len(registradas) == 1
    (a, k) = (registradas[0]["a"], registradas[0]["k"])
    assert a[1:4] == (FAZENDA, TipoEvento.LEITURA_SATELITE, OrigemEvento.SATELITE)
    assert isinstance(k["ocorrido_em"], datetime) and k["ocorrido_em"].tzinfo is not None
    chave = f"leitura:{P1}:2026-09-25"
    assert k["ator"] == "ingestao_sentinel2"
    assert k["chave_idempotencia"] == chave
    assert k["payload"] == {
        "entidade_id": uuid5(NAMESPACE_URL, chave),
        "piquete_id": P1,
        "data": date(2026, 9, 25),
        "ndvi": 0.75,
        "refletancia_red": 0.05,
        "refletancia_nir": 0.35,
        "origem_ndvi": "optico",
        "pct_nuvem": 20.0,
        "pixels_validos": 40,
    }


def test_tudo_existente_retorna_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = ConexaoFalsa(
        [(P1, json.dumps(GEOMETRIA))], {f"leitura:{P1}:{DIA.isoformat()}"}
    )

    def _boom_registrar(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("must not register duplicates")

    monkeypatch.setattr(ingestao, "inicializar_earth_engine", lambda: None)
    monkeypatch.setattr(ingestao, "amostrar_sentinel2", lambda *a, **k: [_obs()])
    monkeypatch.setattr(ingestao, "registrar_evento", _boom_registrar)
    assert ingerir_leituras(conn, FAZENDA, DIA, DIA) == 0  # type: ignore[arg-type]
