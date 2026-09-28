"""Clientes module."""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field


class ClienteIn(BaseModel):
    """Cliente input."""
    model_config = ConfigDict(from_attributes=True)

    nome: str = Field(..., min_length=1)
    telefone: str | None = None
    observacoes: str | None = None


class Cliente(ClienteIn):
    """Cliente."""
    id: UUID


def listar_clientes(conn: psycopg.Connection[Any]) -> list[Cliente]:
    """List all clientes ordered by name."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, nome, telefone, observacoes FROM cliente ORDER BY nome")
        rows = cur.fetchall()
        return [Cliente.model_validate(row) for row in rows]


def criar_cliente(conn: psycopg.Connection[Any], dados: ClienteIn) -> Cliente:
    """Create a new cliente."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO cliente (nome, telefone, observacoes)
            VALUES (%s, %s, %s)
            RETURNING id, nome, telefone, observacoes
            """,
            (dados.nome, dados.telefone, dados.observacoes),
        )
        row = cur.fetchone()
        assert row is not None
        return Cliente.model_validate(row)


def atualizar_cliente(
    conn: psycopg.Connection[Any], cliente_id: UUID, dados: ClienteIn
) -> Cliente:
    """Update a cliente."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE cliente
            SET nome = %s, telefone = %s, observacoes = %s
            WHERE id = %s
            RETURNING id, nome, telefone, observacoes
            """,
            (dados.nome, dados.telefone, dados.observacoes, cliente_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Cliente não encontrado")
        return Cliente.model_validate(row)
