"""Lotes management."""

import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from seugado.core.models import CategoriaAnimal, OrigemEvento, OrigemPeso, TipoEvento
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import reconstruir_projecao
from seugado.planner.estado import peso_por_ua_kg


class ComposicaoItemIn(BaseModel):
    """Composição item input."""

    categoria: CategoriaAnimal
    n_animais: int = Field(..., ge=1)
    peso_medio_kg: float | None = Field(default=None, ge=20.0, le=1500.0)


class LoteIn(BaseModel):
    """Lote input."""

    nome: str = Field(..., min_length=1)
    indissoluvel: bool = False
    composicao: list[ComposicaoItemIn] = Field(..., min_length=1)
    piquete_atual_id: UUID
    desde: date | None = None

    @field_validator("composicao")
    @classmethod
    def validar_categorias_unicas(cls, v: list[ComposicaoItemIn]) -> list[ComposicaoItemIn]:
        categorias = set()
        for item in v:
            if item.categoria in categorias:
                raise ValueError("Categoria repetida na composição")
            categorias.add(item.categoria)
        return v


class ComposicaoItemOut(BaseModel):
    """Composição item output."""
    model_config = ConfigDict(from_attributes=True)

    categoria: CategoriaAnimal
    n_animais: int
    peso_medio_kg: float
    origem_peso: OrigemPeso


class LoteOut(BaseModel):
    """Lote output."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    indissoluvel: bool
    composicao: list[ComposicaoItemOut]
    piquete_atual_id: UUID | None
    piquete_atual_nome: str | None = None
    desde: date | None
    peso_vivo_total_kg: float
    n_animais_total: int


def _validar_piquete_livre(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    piquete_id: UUID,
    ignorar_lote_id: UUID | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ativo, lote_atual_id FROM estado_piquete WHERE piquete_id = %s",
            (piquete_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("Piquete não encontrado")
        ativo, lote_atual = row
        if not ativo:
            raise ValueError("Piquete não está ativo")
        if lote_atual is not None and lote_atual != ignorar_lote_id:
            raise ValueError("Piquete já está ocupado")


def _validar_nome_lote(
    conn: psycopg.Connection[Any], fazenda_id: UUID, nome: str, ignorar_lote_id: UUID | None = None
) -> None:
    with conn.cursor() as cur:
        query = "SELECT 1 FROM estado_lote WHERE fazenda_id = %s AND nome = %s"
        params: list[Any] = [fazenda_id, nome]
        if ignorar_lote_id:
            query += " AND lote_id != %s"
            params.append(ignorar_lote_id)
        cur.execute(query, tuple(params))
        if cur.fetchone() is not None:
            raise ValueError("Nome de lote já existe na fazenda")


def _preparar_composicao(composicao_in: list[ComposicaoItemIn]) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    for item in composicao_in:
        if item.peso_medio_kg is None:
            peso = peso_por_ua_kg(item.categoria)
            origem = OrigemPeso.UA_TABELA.value
        else:
            peso = item.peso_medio_kg
            origem = OrigemPeso.PRODUTOR.value
        
        resultado.append({
            "categoria": item.categoria.value,
            "n_animais": item.n_animais,
            "peso_medio_kg": float(peso),
            "origem_peso": origem
        })
    return resultado


def criar_lote(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    ator: str,
    dados: LoteIn,
) -> UUID:
    """Cria um lote registrando os eventos necessários."""
    hoje = datetime.now(UTC).date()
    desde = dados.desde or hoje
    
    if desde > hoje:
        raise ValueError("Data 'desde' não pode ser no futuro")
        
    _validar_nome_lote(conn, fazenda_id, dados.nome)
    _validar_piquete_livre(conn, fazenda_id, dados.piquete_atual_id)
    
    composicao = _preparar_composicao(dados.composicao)
    lote_id = uuid4()
    agora = datetime.now(UTC)
    
    payload_criado = {
        "entidade_id": str(lote_id),
        "nome": dados.nome,
        "indissoluvel": dados.indissoluvel,
        "composicao": composicao,
    }
    
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.LOTE_CRIADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload=payload_criado,
        ator=ator,
    )
    
    payload_manejo = {
        "entidade_id": str(uuid4()),
        "lote_id": str(lote_id),
        "piquete_destino_id": str(dados.piquete_atual_id),
        "data_execucao": desde.isoformat(),
    }
    
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.MANEJO_CONFIRMADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload=payload_manejo,
        ator=ator,
    )
    
    reconstruir_projecao(conn, fazenda_id)
    return lote_id


def editar_lote(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    lote_id: UUID,
    ator: str,
    dados: LoteIn,
) -> None:
    """Edita um lote registrando o evento LOTE_ALTERADO (e MANEJO_CONFIRMADO se mudou piquete)."""
    hoje = datetime.now(UTC).date()
    
    # Verifica se o lote existe e pega o piquete atual
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT piquete_atual_id FROM estado_lote WHERE lote_id = %s AND fazenda_id = %s",
            (lote_id, fazenda_id)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("Lote não encontrado")
        piquete_antigo_id = row["piquete_atual_id"]
    
    _validar_nome_lote(conn, fazenda_id, dados.nome, ignorar_lote_id=lote_id)
    
    mudou_piquete = piquete_antigo_id != dados.piquete_atual_id
    if mudou_piquete:
        _validar_piquete_livre(conn, fazenda_id, dados.piquete_atual_id)
        
    composicao = _preparar_composicao(dados.composicao)
    agora = datetime.now(UTC)
    
    payload_alterado = {
        "entidade_id": str(lote_id),
        "nome": dados.nome,
        "indissoluvel": dados.indissoluvel,
        "composicao": composicao,
        "ativo": True,
    }
    
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.LOTE_ALTERADO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload=payload_alterado,
        ator=ator,
    )
    
    if mudou_piquete:
        payload_manejo = {
            "entidade_id": str(uuid4()),
            "lote_id": str(lote_id),
            "piquete_destino_id": str(dados.piquete_atual_id),
            "data_execucao": hoje.isoformat(),
        }
        registrar_evento(
            conn=conn,
            fazenda_id=fazenda_id,
            tipo=TipoEvento.MANEJO_CONFIRMADO,
            origem=OrigemEvento.PRODUTOR,
            ocorrido_em=agora,
            payload=payload_manejo,
            ator=ator,
        )
        
    reconstruir_projecao(conn, fazenda_id)


def dissolver_lote(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    lote_id: UUID,
    ator: str,
) -> None:
    """Dissolve um lote registrando o evento LOTE_DISSOLVIDO."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM estado_lote WHERE lote_id = %s AND fazenda_id = %s",
            (lote_id, fazenda_id)
        )
        if not cur.fetchone():
            raise ValueError("Lote não encontrado")
            
    agora = datetime.now(UTC)
    payload_dissolvido = {
        "entidade_id": str(lote_id),
    }
    
    registrar_evento(
        conn=conn,
        fazenda_id=fazenda_id,
        tipo=TipoEvento.LOTE_DISSOLVIDO,
        origem=OrigemEvento.PRODUTOR,
        ocorrido_em=agora,
        payload=payload_dissolvido,
        ator=ator,
    )
    
    reconstruir_projecao(conn, fazenda_id)


def listar_lotes(conn: psycopg.Connection[Any], fazenda_id: UUID) -> list[LoteOut]:
    """Lista todos os lotes ativos da fazenda."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                l.lote_id AS id,
                l.nome,
                l.indissoluvel,
                l.composicao,
                l.piquete_atual_id,
                p.nome AS piquete_atual_nome,
                l.desde,
                l.peso_vivo_total_kg
            FROM estado_lote l
            LEFT JOIN estado_piquete p ON l.piquete_atual_id = p.piquete_id
            WHERE l.fazenda_id = %s
            ORDER BY l.nome
            """,
            (fazenda_id,),
        )
        rows = cur.fetchall()
        
    resultados = []
    for row in rows:
        composicao = row["composicao"]
        if isinstance(composicao, str):
            composicao = json.loads(composicao)
        
        row["composicao"] = composicao
        n_animais_total = sum(item["n_animais"] for item in composicao)
        row["n_animais_total"] = n_animais_total
        resultados.append(LoteOut.model_validate(row))
        
    return resultados
