"""L5: plan, cycle and Telegram routes.

The database tests run inside one transaction that is rolled back at the end (route commits
are ignored), so the shared database is never written. Weather is faked: no network.
"""

import os
from collections.abc import Iterator
from datetime import date, timedelta
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
from seugado.cadastro.lotes import ComposicaoItemIn, LoteIn, criar_lote
from seugado.cadastro.piquetes import PiqueteIn, criar_piquete
from seugado.contratos import plano_de_dict
from seugado.core.models import CategoriaAnimal
from seugado.planner import carga
from seugado.sensing.clima import ClimaDia

precisa_banco = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"),
    reason="needs SEUGADO_TEST_DATABASE_URL",
)

GEOMETRIA = {
    "type": "Polygon",
    "coordinates": [
        [[-36.09, -9.78], [-36.089, -9.78], [-36.089, -9.781], [-36.09, -9.781], [-36.09, -9.78]]
    ],
}


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
    """A fresh farm with one Marandu piquete holding lote "Recria"."""
    cliente = criar_cliente(db_conn, ClienteIn(nome="Cliente Teste Plano"))
    fid = criar_fazenda(
        db_conn,
        FazendaIn(
            cliente_id=cliente.id,
            nome="Fazenda Teste Plano",
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0, 1, 2, 3, 4, 5, 6],
            envio_plano_dia=0,
            envio_plano_hora=6,
        ),
    )
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM cultivar WHERE slug = 'marandu'")
        row = cur.fetchone()
    assert row is not None
    piquete_id = criar_piquete(
        db_conn,
        fid,
        uuid4(),
        PiqueteIn(
            nome="Piquete 1",
            geometria=GEOMETRIA,
            cultivar_id=row[0],
            metodo_pastejo="rotacionado",
            altura_atual_cm=30.0,
        ),
    )
    criar_lote(
        db_conn,
        fid,
        str(uuid4()),
        LoteIn(
            nome="Recria",
            composicao=[ComposicaoItemIn(categoria=CategoriaAnimal.NOVILHO, n_animais=10)],
            piquete_atual_id=piquete_id,
        ),
    )
    return fid


def _clima_falso(
    lat: float, lon: float, inicio: date, fim: date, **_: Any
) -> tuple[ClimaDia, ...]:
    dias = (fim - inicio).days + 1
    return tuple(
        ClimaDia(
            data=inicio + timedelta(days=i),
            rg_mj_m2_dia=20.0,
            t_max_c=31.0,
            t_min_c=21.0,
            t_media_c=26.0,
            et0_mm_dia=4.5,
            chuva_mm=2.0,
            previsto=False,
        )
        for i in range(dias)
    )


@precisa_banco
def test_plano_atual_sem_plano_da_404(api: TestClient, fazenda_id: UUID) -> None:
    resp = api.get(f"/fazendas/{fazenda_id}/plano/atual")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Ainda não há plano"


@precisa_banco
def test_ciclo_gera_plano_e_plano_atual_devolve(
    api: TestClient, fazenda_id: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(carga, "buscar_clima", _clima_falso)
    monkeypatch.setattr(carga, "et0_media_anual_mm_dia", lambda *_a, **_k: 4.5)

    resp = api.post(
        f"/fazendas/{fazenda_id}/ciclo", json={"ingerir_satelite": False, "enviar": False}
    )
    assert resp.status_code == 200, resp.text
    plano = plano_de_dict(resp.json())
    assert plano.fazenda_id == fazenda_id
    assert [p.nome for p in plano.piquetes] == ["Piquete 1"]

    atual = api.get(f"/fazendas/{fazenda_id}/plano/atual")
    assert atual.status_code == 200
    assert plano_de_dict(atual.json()) == plano


@precisa_banco
def test_link_do_telegram_usa_o_codigo_da_fazenda(
    api: TestClient,
    fazenda_id: UUID,
    db_conn: psycopg.Connection[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "SeuGadoTesteBot")
    with db_conn.cursor() as cur:
        cur.execute("SELECT codigo_vinculo_telegram FROM fazenda WHERE id = %s", (fazenda_id,))
        row = cur.fetchone()
    assert row is not None
    resp = api.get(f"/fazendas/{fazenda_id}/telegram")
    assert resp.status_code == 200
    assert resp.json() == {
        "vinculado": False,
        "link": f"https://t.me/SeuGadoTesteBot?start={row[0]}",
    }


@pytest.mark.parametrize(
    ("metodo", "sufixo"),
    [("get", "plano/atual"), ("post", "ciclo"), ("get", "telegram")],
)
def test_sem_login_da_401(metodo: str, sufixo: str) -> None:
    app.dependency_overrides[obter_conexao] = lambda: MagicMock()
    try:
        resp = getattr(TestClient(app), metodo)(f"/fazendas/{uuid4()}/{sufixo}")
    finally:
        app.dependency_overrides.pop(obter_conexao, None)
    assert resp.status_code == 401
