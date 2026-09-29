"""Testes de GET /cultivares (E1)."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from seugado.api.auth import UsuarioAtual, usuario_atual
from seugado.api.deps import obter_conexao
from seugado.api.main import app


@pytest.fixture
def api(db_conn: psycopg.Connection[Any]) -> Iterator[TestClient]:
    """Logged-in client reading the catalog through the test connection."""

    def _conexao() -> Iterator[Any]:
        yield db_conn

    app.dependency_overrides[obter_conexao] = _conexao
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(id=uuid4(), email=None)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(obter_conexao, None)
        app.dependency_overrides.pop(usuario_atual, None)


def test_lista_as_9_cultivares_por_nome_com_calibracao(api):
    resp = api.get("/cultivares")
    assert resp.status_code == 200
    cultivares = resp.json()
    assert len(cultivares) == 9
    nomes = [c["nome"] for c in cultivares]
    assert nomes == sorted(nomes)
    for c in cultivares:
        assert set(c) == {
            "id",
            "slug",
            "nome",
            "regimes_disponiveis",
            "calibrada",
            "faltantes_calibracao",
        }
        assert c["calibrada"] == (not c["faltantes_calibracao"])
        assert set(c["regimes_disponiveis"]) <= {"rotacionado", "continuo"}

    por_nome = {c["nome"]: c for c in cultivares}
    marandu = por_nome["Marandu"]
    assert marandu["calibrada"] is True
    assert marandu["faltantes_calibracao"] == []
    mombaca = por_nome["Mombaça"]
    assert mombaca["calibrada"] is False
    assert mombaca["faltantes_calibracao"]


def test_sem_login_da_401() -> None:
    app.dependency_overrides[obter_conexao] = lambda: MagicMock()
    try:
        resp = TestClient(app).get("/cultivares")
    finally:
        app.dependency_overrides.pop(obter_conexao, None)
    assert resp.status_code == 401
