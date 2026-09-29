"""Testes para o cadastro de piquetes."""

import os
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.fazenda import FazendaIn, criar_fazenda
from seugado.cadastro.piquetes import (
    AlturaIn,
    PiqueteIn,
    area_ha,
    criar_piquete,
    desativar_piquete,
    editar_piquete,
    listar_piquetes,
    registrar_altura,
)


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
        db_conn, fazenda_id, p_id, usuario_id, AlturaIn(altura_cm=35.0, data=date.today())
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
