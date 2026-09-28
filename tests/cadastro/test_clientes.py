"""Test clients."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from seugado.cadastro.clientes import ClienteIn, atualizar_cliente, criar_cliente, listar_clientes


def test_cliente_lifecycle(db_conn):
    """Test creating, listing and updating a client."""
    # 1. Create client
    dados = ClienteIn(nome="Test Client", telefone="123", observacoes="obs")
    cliente = criar_cliente(db_conn, dados)
    
    assert isinstance(cliente.id, UUID)
    assert cliente.nome == "Test Client"
    assert cliente.telefone == "123"
    assert cliente.observacoes == "obs"
    
    # 2. List clients
    clientes_list = listar_clientes(db_conn)
    assert any(c.id == cliente.id for c in clientes_list)
    
    # 3. Update client
    dados_update = ClienteIn(nome="Test Client Updated", telefone="456", observacoes=None)
    cliente_upd = atualizar_cliente(db_conn, cliente.id, dados_update)
    assert cliente_upd.nome == "Test Client Updated"
    assert cliente_upd.telefone == "456"
    assert cliente_upd.observacoes is None


def test_cliente_nome_invalido():
    """Test validation."""
    with pytest.raises(ValidationError):
        ClienteIn(nome="", telefone="123", observacoes="obs")
