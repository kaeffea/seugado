"""Fazenda and Cliente routes (owner: Leandro)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from seugado.api.auth import FazendaAutorizada, Usuario
from seugado.api.deps import Conexao
from seugado.cadastro import clientes, fazenda

router = APIRouter(tags=["admin"])


@router.get("/me")
def obter_me(usuario: Usuario) -> dict[str, Any]:
    """Return current user info."""
    return {"usuario_id": usuario.id, "email": usuario.email}


@router.get("/clientes", response_model=list[clientes.Cliente])
def listar_clientes_rota(usuario: Usuario, conn: Conexao) -> list[clientes.Cliente]:
    """List all clients."""
    return clientes.listar_clientes(conn)


@router.post("/clientes", response_model=clientes.Cliente, status_code=status.HTTP_201_CREATED)
def criar_cliente_rota(
    dados: clientes.ClienteIn, usuario: Usuario, conn: Conexao
) -> clientes.Cliente:
    """Create a new client."""
    try:
        cliente = clientes.criar_cliente(conn, dados)
        conn.commit()
        return cliente
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/clientes/{cliente_id}", response_model=clientes.Cliente)
def atualizar_cliente_rota(
    cliente_id: UUID, dados: clientes.ClienteIn, usuario: Usuario, conn: Conexao
) -> clientes.Cliente:
    """Update a client."""
    try:
        cliente = clientes.atualizar_cliente(conn, cliente_id, dados)
        conn.commit()
        return cliente
    except ValueError as e:
        if "não encontrado" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/fazendas", response_model=list[fazenda.FazendaOut])
def listar_fazendas_rota(usuario: Usuario, conn: Conexao) -> list[fazenda.FazendaOut]:
    """List all farms."""
    return fazenda.listar_fazendas(conn)


@router.post("/fazendas", response_model=fazenda.FazendaOut, status_code=status.HTTP_201_CREATED)
def criar_fazenda_rota(
    dados: fazenda.FazendaIn, usuario: Usuario, conn: Conexao
) -> fazenda.FazendaOut:
    """Create a new farm."""
    try:
        fazenda_id = fazenda.criar_fazenda(conn, dados)
        fazenda_api = fazenda.obter_fazenda_api(conn, fazenda_id)
        conn.commit()
        return fazenda_api
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/fazendas/{fazenda_id}", response_model=fazenda.FazendaOut)
def obter_fazenda_rota(
    fazenda_id: FazendaAutorizada, usuario: Usuario, conn: Conexao
) -> fazenda.FazendaOut:
    """Get a single farm."""
    try:
        return fazenda.obter_fazenda_api(conn, fazenda_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/fazendas/{fazenda_id}", response_model=fazenda.FazendaOut)
def atualizar_fazenda_rota(
    fazenda_id: FazendaAutorizada, dados: fazenda.FazendaIn, usuario: Usuario, conn: Conexao
) -> fazenda.FazendaOut:
    """Update a farm."""
    try:
        fazenda.atualizar_fazenda(conn, fazenda_id, dados)
        fazenda_api = fazenda.obter_fazenda_api(conn, fazenda_id)
        conn.commit()
        return fazenda_api
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
