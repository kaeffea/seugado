"""Testes para o cadastro de piquetes."""

import os
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from seugado.api.auth import UsuarioAtual, usuario_atual
from seugado.api.deps import obter_conexao
from seugado.api.main import app
from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.fazenda import FazendaIn, criar_fazenda
from seugado.cadastro.lotes import ComposicaoItemIn, LoteIn, criar_lote
from seugado.cadastro.piquetes import (
    AlturaIn,
    PiqueteIn,
    PiqueteOcupadoError,
    area_ha,
    criar_piquete,
    desativar_piquete,
    editar_piquete,
    listar_piquetes,
    registrar_altura,
)
from seugado.core.models import CategoriaAnimal


# Testes sem banco
def test_piquete_in_validacao():
    # Deve aceitar rotacionado e continuo
    PiqueteIn(
        nome="Piquete 1",
        geometria={"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]},
        cultivar_id=uuid4(),
        metodo_pastejo="rotacionado"
    )
    PiqueteIn(
        nome="Piquete 1",
        geometria={"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]},
        cultivar_id=uuid4(),
        metodo_pastejo="continuo"
    )
    
    # Não deve aceitar método inválido
    with pytest.raises(ValidationError):
        PiqueteIn(
            nome="Piquete 1",
            geometria={"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]},
            cultivar_id=uuid4(),
            metodo_pastejo="invalido" # type: ignore
        )


def test_altura_in_validacao():
    # Válido
    AlturaIn(altura_cm=20.5, data=date.today())
    
    # Inválido
    with pytest.raises(ValidationError):
        AlturaIn(altura_cm=0, data=date.today())
    with pytest.raises(ValidationError):
        AlturaIn(altura_cm=401, data=date.today())


# Testes com banco
@pytest.fixture
def fazenda_id(db_conn):
    if not os.environ.get("SEUGADO_TEST_DATABASE_URL") and not os.environ.get("DATABASE_URL"):
        pytest.skip("Sem banco de dados")
    
    c_id = criar_cliente(db_conn, ClienteIn(nome="Cliente Teste Piquetes")).id
    f_id = criar_fazenda(
        db_conn,
        FazendaIn(
            cliente_id=c_id,
            nome="Fazenda Teste Piquetes",
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0],
            envio_plano_dia=0,
            envio_plano_hora=8,
        )
    )
    return f_id


def test_ciclo_piquete_com_banco(db_conn, fazenda_id):
    usuario_id = uuid4()
    # Pega um cultivar qualquer para teste (o banco deve ter fixtures)
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM cultivar LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("Sem cultivares no banco")
        cultivar_id = row[0]

    geometria = {
        "type": "Polygon",
        "coordinates": [
            [
                [-46.0, -23.0],
                [-46.002, -23.0],
                [-46.002, -23.002],
                [-46.0, -23.002],
                [-46.0, -23.0],
            ]
        ],
    }

    # 1. Criar
    dados_in = PiqueteIn(
        nome="Piquete A",
        geometria=geometria,
        cultivar_id=cultivar_id,
        metodo_pastejo="rotacionado",
        altura_atual_cm=30.0,
    )
    p_id = criar_piquete(db_conn, fazenda_id, usuario_id, dados_in)

    # 2. Listar
    lista = listar_piquetes(db_conn, fazenda_id)
    assert len(lista) == 1
    p = lista[0]
    assert p.id == p_id
    assert p.nome == "Piquete A"
    assert p.ultima_altura_cm == 30.0

    # 3. Editar
    dados_edit = PiqueteIn(
        nome="Piquete A Editado",
        geometria=geometria,
        cultivar_id=cultivar_id,
        metodo_pastejo="continuo",
    )
    editar_piquete(db_conn, fazenda_id, p_id, usuario_id, dados_edit)
    
    lista2 = listar_piquetes(db_conn, fazenda_id)
    assert lista2[0].nome == "Piquete A Editado"
    assert lista2[0].metodo_pastejo == "continuo"

    # 4. Registrar Altura
    registrar_altura(
        db_conn,
        fazenda_id,
        p_id,
        usuario_id,
        AlturaIn(altura_cm=35.0, data=datetime.now(ZoneInfo("America/Fortaleza")).date()),
    )
    lista3 = listar_piquetes(db_conn, fazenda_id)
    assert lista3[0].ultima_altura_cm == 35.0

    # 5. Desativar
    desativar_piquete(db_conn, fazenda_id, p_id, usuario_id)
    lista4 = listar_piquetes(db_conn, fazenda_id)
    assert len(lista4) == 0


def test_area_ha_valida_poligono_invalido(db_conn):
    # Poligono que se cruza (borboleta)
    geometria = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [1.0, 1.0],
                [1.0, 0.0],
                [0.0, 1.0],
                [0.0, 0.0],
            ]
        ],
    }
    with pytest.raises(ValueError, match="Polígono inválido"):
        area_ha(db_conn, geometria)


# Regras de cadastro (E2/E3): validações antes do evento, nome único, área, 409 só p/ ocupado

# Irregular quadrilateral whose raw area has many decimals.
GEOMETRIA_IRREGULAR = {
    "type": "Polygon",
    "coordinates": [
        [
            [-46.0, -23.0],
            [-46.0017, -23.0003],
            [-46.0021, -23.0019],
            [-46.0003, -23.0023],
            [-46.0, -23.0],
        ]
    ],
}


class _ConexaoSemCommit:
    """Delegates to the test connection but ignores commit/rollback from the routes.

    Keeps everything inside the fixture's transaction, which db_conn rolls back at the end,
    so the shared database is never written.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def __getattr__(self, nome: str) -> Any:
        return getattr(self._conn, nome)


@pytest.fixture
def api(db_conn: psycopg.Connection[Any]) -> Iterator[TestClient]:
    """TestClient logged in, using the test transaction as the request connection."""
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


def _cultivar_id(db_conn: psycopg.Connection[Any]) -> UUID:
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM cultivar ORDER BY nome LIMIT 1")
        row = cur.fetchone()
    assert row is not None, "catálogo de cultivares vazio"
    return UUID(str(row[0]))


def _corpo(nome: str, cultivar_id: UUID) -> dict[str, Any]:
    return {
        "nome": nome,
        "geometria": GEOMETRIA_IRREGULAR,
        "cultivar_id": str(cultivar_id),
        "metodo_pastejo": "rotacionado",
        "altura_atual_cm": 30.0,
    }


def _contar_eventos(db_conn: psycopg.Connection[Any], fazenda_id: UUID) -> int:
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM evento WHERE fazenda_id = %s", (fazenda_id,))
        row = cur.fetchone()
    assert row is not None
    return int(row[0])


def test_criar_com_cultivar_inexistente_da_400_sem_evento(db_conn, fazenda_id, api):
    antes = _contar_eventos(db_conn, fazenda_id)
    resp = api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete X", uuid4()))
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Cultivar não encontrada"
    assert _contar_eventos(db_conn, fazenda_id) == antes


def test_criar_com_nome_repetido_da_400_sem_evento(db_conn, fazenda_id, api):
    cultivar_id = _cultivar_id(db_conn)
    primeiro = api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete 1", cultivar_id))
    assert primeiro.status_code == 201
    antes = _contar_eventos(db_conn, fazenda_id)

    repetido = api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete 1", cultivar_id))
    assert repetido.status_code == 400
    assert repetido.json()["detail"] == "Já existe um piquete ativo com esse nome"
    assert _contar_eventos(db_conn, fazenda_id) == antes


def test_editar_com_nome_de_outro_piquete_da_400(db_conn, fazenda_id, api):
    cultivar_id = _cultivar_id(db_conn)
    api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete 1", cultivar_id))
    segundo = api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete 2", cultivar_id))
    corpo = _corpo("Piquete 1", cultivar_id)
    del corpo["altura_atual_cm"]
    resp = api.put(f"/fazendas/{fazenda_id}/piquetes/{segundo.json()['id']}", json=corpo)
    assert resp.status_code == 400


def test_editar_mantendo_o_proprio_nome_funciona(db_conn, fazenda_id):
    cultivar_id = _cultivar_id(db_conn)
    usuario_id = uuid4()
    dados = PiqueteIn(
        nome="Piquete Fixo",
        geometria=GEOMETRIA_IRREGULAR,
        cultivar_id=cultivar_id,
        metodo_pastejo="rotacionado",
        altura_atual_cm=30.0,
    )
    p_id = criar_piquete(db_conn, fazenda_id, usuario_id, dados)
    editar_piquete(
        db_conn,
        fazenda_id,
        p_id,
        usuario_id,
        dados.model_copy(update={"metodo_pastejo": "continuo", "altura_atual_cm": None}),
    )
    [p] = listar_piquetes(db_conn, fazenda_id)
    assert p.nome == "Piquete Fixo"
    assert p.metodo_pastejo == "continuo"


def test_area_arredondada_em_duas_casas(db_conn, fazenda_id):
    bruta = area_ha(db_conn, GEOMETRIA_IRREGULAR)
    assert bruta != round(bruta, 2)  # the fixture really has more than 2 decimals

    p_id = criar_piquete(
        db_conn,
        fazenda_id,
        uuid4(),
        PiqueteIn(
            nome="Piquete Area",
            geometria=GEOMETRIA_IRREGULAR,
            cultivar_id=_cultivar_id(db_conn),
            metodo_pastejo="rotacionado",
            altura_atual_cm=30.0,
        ),
    )
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT payload->>'area_ha' FROM evento"
            " WHERE fazenda_id = %s AND tipo = 'piquete_criado'",
            (fazenda_id,),
        )
        row = cur.fetchone()
    assert row is not None
    assert float(row[0]) == round(bruta, 2)
    [p] = listar_piquetes(db_conn, fazenda_id)
    assert p.id == p_id
    assert p.area_ha == round(bruta, 2)


def test_delete_de_piquete_ocupado_da_409(db_conn, fazenda_id, api):
    cultivar_id = _cultivar_id(db_conn)
    criado = api.post(
        f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete Ocupado", cultivar_id)
    )
    assert criado.status_code == 201
    p_id = UUID(criado.json()["id"])
    criar_lote(
        db_conn,
        fazenda_id,
        str(uuid4()),
        LoteIn(
            nome="Lote Teste",
            composicao=[ComposicaoItemIn(categoria=CategoriaAnimal.NOVILHO, n_animais=10)],
            piquete_atual_id=p_id,
        ),
    )
    with pytest.raises(PiqueteOcupadoError):
        desativar_piquete(db_conn, fazenda_id, p_id, uuid4())

    resp = api.delete(f"/fazendas/{fazenda_id}/piquetes/{p_id}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Tire o lote do piquete antes de desativá-lo"


def test_registrar_altura_no_futuro_da_fazenda_da_400(db_conn, fazenda_id, api):
    cultivar_id = _cultivar_id(db_conn)
    criado = api.post(f"/fazendas/{fazenda_id}/piquetes", json=_corpo("Piquete H", cultivar_id))
    hoje_fazenda = datetime.now(ZoneInfo("America/Fortaleza")).date()
    amanha = date.fromordinal(hoje_fazenda.toordinal() + 1)
    url = f"/fazendas/{fazenda_id}/piquetes/{criado.json()['id']}/alturas"
    hoje_ok = api.post(url, json={"altura_cm": 25.0, "data": hoje_fazenda.isoformat()})
    assert hoje_ok.status_code == 201
    futuro = api.post(url, json={"altura_cm": 25.0, "data": amanha.isoformat()})
    assert futuro.status_code == 400
