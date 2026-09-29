import json
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import reconstruir_projecao


class PiqueteIn(BaseModel):
    nome: str
    geometria: dict[str, Any]
    cultivar_id: UUID
    metodo_pastejo: Literal["rotacionado", "continuo"]
    altura_atual_cm: float | None = None
    data_medicao: date | None = None


class AlturaIn(BaseModel):
    altura_cm: float = Field(gt=0, le=400)
    data: date


class PiqueteOut(BaseModel):
    id: UUID
    nome: str
    geometria: dict[str, Any]
    area_ha: float
    cultivar_id: UUID
    cultivar_nome: str
    metodo_pastejo: Literal["rotacionado", "continuo"]
    situacao: Literal["ocupado", "descansando"]
    lote_atual_id: UUID | None
    lote_atual_nome: str | None
    ultima_altura_cm: float | None
    ultima_altura_data: date | None


def area_ha(conn: psycopg.Connection[Any], geometria: dict[str, Any]) -> float:
    """Calcula a área em hectares via PostGIS e verifica validade."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ST_IsValid(g), ST_Area(g::geography) / 10000.0
            FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) AS g) t
            """,
            (json.dumps(geometria),),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Erro ao calcular área")
        is_valid, area = row
        if not is_valid:
            raise ValueError("Polígono inválido (ex: se cruza)")
        return float(area)


def criar_piquete(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    usuario_id: UUID,
    dados: PiqueteIn,
) -> UUID:
    """Cria piquete e altura via eventos."""
    if dados.altura_atual_cm is None:
        raise ValueError("altura_atual_cm é obrigatória na criação")

    area = area_ha(conn, dados.geometria)
    piquete_id = uuid4()
    agora = datetime.now(UTC)

    # Evento PIQUETE_CRIADO
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.PIQUETE_CRIADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload={
            "entidade_id": str(piquete_id),
            "nome": dados.nome,
            "area_ha": area,
            "cultivar_id": str(dados.cultivar_id),
            "metodo_pastejo": dados.metodo_pastejo,
            "ativo": True,
            "geometria_geojson": dados.geometria,
        },
        ator=str(usuario_id),
    )

    # Evento ALTURA_MEDIDA
    data_med = dados.data_medicao or agora.date()
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.ALTURA_MEDIDA,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload={
            "entidade_id": str(uuid4()),
            "piquete_id": str(piquete_id),
            "data": data_med.isoformat(),
            "altura_cm": dados.altura_atual_cm,
            "meio": "cadastro",
        },
        ator=str(usuario_id),
    )

    reconstruir_projecao(conn, fazenda_id)
    return piquete_id


def editar_piquete(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    piquete_id: UUID,
    usuario_id: UUID,
    dados: PiqueteIn,
) -> None:
    """Edita os dados do piquete sem altura."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM estado_piquete WHERE piquete_id = %s AND fazenda_id = %s",
            (piquete_id, fazenda_id),
        )
        if not cur.fetchone():
            raise LookupError("Piquete não encontrado")

    area = area_ha(conn, dados.geometria)
    agora = datetime.now(UTC)

    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.PIQUETE_ALTERADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload={
            "entidade_id": str(piquete_id),
            "nome": dados.nome,
            "area_ha": area,
            "cultivar_id": str(dados.cultivar_id),
            "metodo_pastejo": dados.metodo_pastejo,
            "ativo": True,
            "geometria_geojson": dados.geometria,
        },
        ator=str(usuario_id),
    )

    reconstruir_projecao(conn, fazenda_id)


def desativar_piquete(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    piquete_id: UUID,
    usuario_id: UUID,
) -> None:
    """Desativa piquete, negando se estiver ocupado."""

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT nome, area_ha, cultivar_id, metodo_pastejo, lote_atual_id,
                   ST_AsGeoJSON(geometria)::json AS geometria_geojson
            FROM estado_piquete
            WHERE piquete_id = %s AND fazenda_id = %s AND ativo = TRUE
            """,
            (piquete_id, fazenda_id),
        )
        row = cur.fetchone()

    if not row:
        raise LookupError("Piquete não encontrado")
    
    if row["lote_atual_id"] is not None:
        raise ValueError("Tire o lote do piquete antes de desativá-lo")

    agora = datetime.now(UTC)
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.PIQUETE_ALTERADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload={
            "entidade_id": str(piquete_id),
            "nome": row["nome"],
            "area_ha": row["area_ha"],
            "cultivar_id": str(row["cultivar_id"]),
            "metodo_pastejo": row["metodo_pastejo"],
            "ativo": False,
            "geometria_geojson": row["geometria_geojson"],
        },
        ator=str(usuario_id),
    )

    reconstruir_projecao(conn, fazenda_id)


def registrar_altura(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    piquete_id: UUID,
    usuario_id: UUID,
    dados: AlturaIn,
) -> None:
    """Registra uma medição de altura."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM estado_piquete WHERE piquete_id = %s "
            "AND fazenda_id = %s AND ativo = TRUE",
            (piquete_id, fazenda_id),
        )
        if not cur.fetchone():
            raise LookupError("Piquete não encontrado")

    agora = datetime.now(UTC)
    if dados.data > agora.date():
        raise ValueError("Data da medição não pode ser no futuro")

    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.ALTURA_MEDIDA,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload={
            "entidade_id": str(uuid4()),
            "piquete_id": str(piquete_id),
            "data": dados.data.isoformat(),
            "altura_cm": dados.altura_cm,
            "meio": "web",
        },
        ator=str(usuario_id),
    )

    reconstruir_projecao(conn, fazenda_id)


def listar_piquetes(conn: psycopg.Connection[Any], fazenda_id: UUID) -> list[PiqueteOut]:
    """Lista piquetes da fazenda."""

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                p.piquete_id AS id,
                p.nome,
                ST_AsGeoJSON(p.geometria)::json AS geometria,
                p.area_ha,
                p.cultivar_id,
                c.nome AS cultivar_nome,
                p.metodo_pastejo,
                p.situacao,
                p.lote_atual_id,
                l.nome AS lote_atual_nome,
                a.altura_cm AS ultima_altura_cm,
                a.data AS ultima_altura_data
            FROM estado_piquete p
            JOIN cultivar c ON c.id = p.cultivar_id
            LEFT JOIN estado_lote l ON l.lote_id = p.lote_atual_id
            LEFT JOIN altura_atual a ON a.piquete_id = p.piquete_id
            WHERE p.fazenda_id = %s AND p.ativo = TRUE
            ORDER BY p.nome
            """,
            (fazenda_id,),
        )
        rows = cur.fetchall()

    return [PiqueteOut(**row) for row in rows]
