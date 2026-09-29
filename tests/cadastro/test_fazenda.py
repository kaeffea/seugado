"""Test fazenda."""

import uuid

import pytest
from pydantic import ValidationError

from seugado.cadastro.clientes import ClienteIn, criar_cliente
from seugado.cadastro.fazenda import (
    FazendaIn,
    atualizar_fazenda,
    carregar_fazenda,
    criar_fazenda,
    listar_fazendas,
    obter_fazenda_api,
)


def test_fazenda_lifecycle(db_conn):
    """Test fazenda operations."""
    # Create a client first
    c = criar_cliente(db_conn, ClienteIn(nome="Cliente Fazenda"))
    
    # Create Fazenda
    dados = FazendaIn(
        cliente_id=c.id,
        nome="Fazenda do Teste",
        timezone="America/Fortaleza",
        funcionarios_disponiveis=2,
        animais_por_funcionario_dia=100,
        dias_preferenciais_manejo=[0, 3],
        envio_plano_dia=6,
        envio_plano_hora=18,
    )
    
    f_id = criar_fazenda(db_conn, dados)
    assert isinstance(f_id, uuid.UUID)
    
    # Load Core Fazenda
    core_f = carregar_fazenda(db_conn, f_id)
    assert core_f.id == f_id
    assert core_f.nome == "Fazenda do Teste"
    assert core_f.dias_preferenciais_manejo == (0, 3)
    
    # Load API Fazenda
    api_f = obter_fazenda_api(db_conn, f_id)
    assert api_f.id == f_id
    assert api_f.cliente_nome == "Cliente Fazenda"
    
    # List Fazendas
    lista = listar_fazendas(db_conn)
    assert any(f.id == f_id for f in lista)
    
    # Update Fazenda
    dados_upd = FazendaIn(
        cliente_id=c.id,
        nome="Fazenda do Teste 2",
        timezone="America/Fortaleza",
        funcionarios_disponiveis=3,
        animais_por_funcionario_dia=150,
        dias_preferenciais_manejo=[1, 4],
        envio_plano_dia=5,
        envio_plano_hora=20,
    )
    atualizar_fazenda(db_conn, f_id, dados_upd)
    
    api_f2 = obter_fazenda_api(db_conn, f_id)
    assert api_f2.nome == "Fazenda do Teste 2"
    assert api_f2.dias_preferenciais_manejo == [1, 4]


def test_fazenda_validation():
    """Test fazenda input validation."""
    with pytest.raises(ValidationError):
        FazendaIn(
            cliente_id=uuid.uuid4(),
            nome="",
            timezone="America/Fortaleza",
            funcionarios_disponiveis=0,  # invalid
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[0, 3],
            envio_plano_dia=6,
            envio_plano_hora=18,
        )
    
    with pytest.raises(ValidationError):
        FazendaIn(
            cliente_id=uuid.uuid4(),
            nome="A",
            timezone="America/Fortaleza",
            funcionarios_disponiveis=1,
            animais_por_funcionario_dia=100,
            dias_preferenciais_manejo=[7],  # invalid dia
            envio_plano_dia=6,
            envio_plano_hora=18,
        )
