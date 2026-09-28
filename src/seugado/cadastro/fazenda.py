"""Fazenda module."""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from seugado.core.models import Fazenda as CoreFazenda


class FazendaIn(BaseModel):
    """Fazenda input."""
    model_config = ConfigDict(from_attributes=True)

    cliente_id: UUID
    nome: str = Field(..., min_length=1)
    timezone: str = "America/Fortaleza"
    funcionarios_disponiveis: int = Field(..., ge=1)
    animais_por_funcionario_dia: int = Field(..., ge=1)
    dias_preferenciais_manejo: list[int] = Field(..., min_length=1)
    envio_plano_dia: int = Field(..., ge=0, le=6)
    envio_plano_hora: int = Field(..., ge=0, le=23)

    @field_validator("dias_preferenciais_manejo")
    @classmethod
    def validate_dias(cls, v: list[int]) -> list[int]:
        if any(dia < 0 or dia > 6 for dia in v):  # noqa: PLR2004
            raise ValueError("Dias devem estar entre 0 e 6")
        return sorted(list(set(v)))


class FazendaOut(FazendaIn):
    """Fazenda API response."""
    id: UUID
    cliente_nome: str


def listar_fazendas(conn: psycopg.Connection[Any]) -> list[FazendaOut]:
    """List all active fazendas."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                f.id, f.cliente_id, c.nome AS cliente_nome, f.nome, f.timezone,
                f.funcionarios_disponiveis, f.animais_por_funcionario_dia,
                f.dias_preferenciais_manejo, f.envio_plano_dia, f.envio_plano_hora
            FROM fazenda f
            LEFT JOIN cliente c ON f.cliente_id = c.id
            WHERE f.ativo = TRUE
            ORDER BY c.nome, f.nome
            """
        )
        rows = cur.fetchall()
        return [FazendaOut.model_validate(row) for row in rows]


def _validar_cliente_existe(conn: psycopg.Connection[Any], cliente_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM cliente WHERE id = %s", (cliente_id,))
        if cur.fetchone() is None:
            raise ValueError("Cliente não encontrado")


def criar_fazenda(conn: psycopg.Connection[Any], dados: FazendaIn) -> UUID:
    """Create a new fazenda and return its ID."""
    _validar_cliente_existe(conn, dados.cliente_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fazenda (
                cliente_id, nome, timezone, funcionarios_disponiveis,
                animais_por_funcionario_dia, dias_preferenciais_manejo,
                envio_plano_dia, envio_plano_hora
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                dados.cliente_id,
                dados.nome,
                dados.timezone,
                dados.funcionarios_disponiveis,
                dados.animais_por_funcionario_dia,
                dados.dias_preferenciais_manejo,
                dados.envio_plano_dia,
                dados.envio_plano_hora,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        return UUID(str(row[0]))


def atualizar_fazenda(conn: psycopg.Connection[Any], fazenda_id: UUID, dados: FazendaIn) -> None:
    """Update an existing fazenda."""
    _validar_cliente_existe(conn, dados.cliente_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE fazenda
            SET cliente_id = %s, nome = %s, timezone = %s,
                funcionarios_disponiveis = %s, animais_por_funcionario_dia = %s,
                dias_preferenciais_manejo = %s, envio_plano_dia = %s,
                envio_plano_hora = %s
            WHERE id = %s
            """,
            (
                dados.cliente_id,
                dados.nome,
                dados.timezone,
                dados.funcionarios_disponiveis,
                dados.animais_por_funcionario_dia,
                dados.dias_preferenciais_manejo,
                dados.envio_plano_dia,
                dados.envio_plano_hora,
                fazenda_id,
            ),
        )
        if cur.rowcount == 0:
            raise ValueError("Fazenda não encontrada")


def carregar_fazenda(conn: psycopg.Connection[Any], fazenda_id: UUID) -> CoreFazenda:
    """Load the domain Fazenda entity."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id, nome, timezone, funcionarios_disponiveis,
                animais_por_funcionario_dia, dias_preferenciais_manejo,
                envio_plano_dia, envio_plano_hora, ativo
            FROM fazenda
            WHERE id = %s
            """,
            (fazenda_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Fazenda não encontrada")
        # Need to cast dias_preferenciais_manejo to tuple[int, ...]
        row["dias_preferenciais_manejo"] = tuple(row["dias_preferenciais_manejo"])
        return CoreFazenda(**row)


def obter_fazenda_api(conn: psycopg.Connection[Any], fazenda_id: UUID) -> FazendaOut:
    """Load the API Fazenda representation."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                f.id, f.cliente_id, c.nome AS cliente_nome, f.nome, f.timezone,
                f.funcionarios_disponiveis, f.animais_por_funcionario_dia,
                f.dias_preferenciais_manejo, f.envio_plano_dia, f.envio_plano_hora
            FROM fazenda f
            LEFT JOIN cliente c ON f.cliente_id = c.id
            WHERE f.id = %s
            """,
            (fazenda_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Fazenda não encontrada")
        return FazendaOut.model_validate(row)
