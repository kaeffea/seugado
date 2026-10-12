"""Smoke tests for the module and feeding square routes (SPEC-017).

Same pattern as the plan route tests: one transaction, rolled back at the end, route commits
ignored, so the shared database is never written.
"""

import os
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from seugado.api.auth import UsuarioAtual, usuario_atual
from seugado.api.deps import obter_conexao
from seugado.api.main import app
from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.fazenda import FazendaIn, criar_fazenda

precisa_banco = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"),
    reason="needs SEUGADO_TEST_DATABASE_URL",
)


class _ConexaoSemCommit:
    """The test connection, with commit/rollback from the code under test turned into no-ops."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        self._conn = conn

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def __getattr__(self, nome: str) -> Any:
        return getattr(self._conn, nome)


@pytest.fixture
def db_conn() -> Iterator[psycopg.Connection[Any]]:
    conn = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"], autocommit=False)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def api(db_conn: psycopg.Connection[Any]) -> Iterator[TestClient]:
    conexao = _ConexaoSemCommit(db_conn)

    def _conexao() -> Iterator[Any]:
        yield conexao

    app.dependency_overrides[obter_conexao] = _conexao
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(id=uuid4(), email=None)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(obter_conexao, None)
        app.dependency_overrides.pop(usuario_atual, None)


@pytest.fixture
def fazenda_id(db_conn: psycopg.Connection[Any]) -> UUID:
    cliente = criar_cliente(db_conn, ClienteIn(nome="Cliente Teste Estrutura"))
    return criar_fazenda(
        db_conn,
        FazendaIn(
            cliente_id=cliente.id,
            nome="Fazenda Teste Estrutura",
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0],
            envio_plano_dia=0,
            envio_plano_hora=6,
        ),
    )


@precisa_banco
def test_ciclo_de_modulo(api: TestClient, fazenda_id: UUID) -> None:
    base = f"/fazendas/{fazenda_id}/modulos"
    criado = api.post(base, json={"nome": "Módulo A"})
    assert criado.status_code == 201, criado.text
    modulo_id = criado.json()["id"]
    assert criado.json()["lotacao_ua_ha"] is None

    assert api.post(base, json={"nome": "Módulo A"}).status_code == 400
    assert api.put(f"{base}/{modulo_id}", json={"nome": "Módulo B"}).json()["nome"] == "Módulo B"
    assert [m["nome"] for m in api.get(base).json()] == ["Módulo B"]
    assert api.delete(f"{base}/{modulo_id}").status_code == 204
    assert api.delete(f"{base}/{modulo_id}").status_code == 404


@precisa_banco
def test_praca_valida_latitude_e_apaga(api: TestClient, fazenda_id: UUID) -> None:
    base = f"/fazendas/{fazenda_id}/pracas"
    assert api.post(base, json={"nome": "P", "lat": 91, "lon": 0}).status_code == 422
    criada = api.post(base, json={"nome": "Praça 1", "lat": -9.6, "lon": -36.0})
    assert criada.status_code == 201, criada.text
    assert criada.json()["lat"] == pytest.approx(-9.6)
    assert api.delete(f"{base}/{criada.json()['id']}").status_code == 204


@precisa_banco
def test_estrutura_vazia_e_vinculos_inexistentes(api: TestClient, fazenda_id: UUID) -> None:
    assert api.get(f"/fazendas/{fazenda_id}/estrutura").json() == {"piquetes": [], "lotes": []}
    resp = api.put(
        f"/fazendas/{fazenda_id}/piquetes/{uuid4()}/estrutura",
        json={"modulo_id": None, "praca_id": None},
    )
    assert resp.status_code == 404
    resp = api.put(f"/fazendas/{fazenda_id}/lotes/{uuid4()}/modulo", json={"modulo_id": None})
    assert resp.status_code == 404


def test_rotas_exigem_login() -> None:
    app.dependency_overrides[obter_conexao] = lambda: MagicMock()
    try:
        resp = TestClient(app).get(f"/fazendas/{uuid4()}/modulos")
    finally:
        app.dependency_overrides.pop(obter_conexao, None)
    assert resp.status_code == 401


def test_onze_rotas_no_openapi() -> None:
    caminhos = TestClient(app).get("/openapi.json").json()["paths"]
    rotas = {
        (metodo.upper(), caminho)
        for caminho, ops in caminhos.items()
        for metodo in ops
        if any(s in caminho for s in ("/modulos", "/pracas", "/estrutura", "/modulo"))
    }
    assert len(rotas) == 11
