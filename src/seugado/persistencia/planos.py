"""Plan storage with status (vigente, candidato, substituido, descartado).

A vigente plan is the one the producer follows; saving or promoting it records one
manejo_recomendado event per movement. A candidato is only offered, so it records none.
No function here commits: the caller does.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

import psycopg
from psycopg.types.json import Json

from seugado.contratos import PlanoManejo, plano_de_dict, plano_para_dict
from seugado.core.models import OrigemEvento, TipoEvento
from seugado.persistencia.eventos import registrar_evento

StatusSalvar = Literal["vigente", "candidato"]

_TIPOS_RESPOSTA = [
    TipoEvento.MANEJO_CONFIRMADO.value,
    TipoEvento.MANEJO_RECUSADO.value,
    TipoEvento.MANEJO_DIVERGENTE.value,
]

_SUBSTITUIR_VIGENTE = (
    "UPDATE plano SET status = 'substituido' WHERE fazenda_id = %s AND status = 'vigente'"
)
_DESCARTAR_CANDIDATOS = (
    "UPDATE plano SET status = 'descartado' WHERE fazenda_id = %s AND status = 'candidato'"
)
_INSERT_PLANO = (
    "INSERT INTO plano (id, fazenda_id, gerado_em, data_inicio, horizonte_dias, payload, status)"
    " VALUES (%s, %s, %s, %s, %s, %s, %s)"
)
_SELECT_MAIS_RECENTE = (
    "SELECT payload FROM plano WHERE fazenda_id = %s AND status = %s"
    " ORDER BY gerado_em DESC LIMIT 1"
)


def _registrar_recomendacoes(conn: psycopg.Connection[Any], plano: PlanoManejo) -> None:
    """One manejo_recomendado per movement; the idempotency key makes a retry harmless."""
    agora = datetime.now(UTC)
    for mov in plano.movimentacoes:
        registrar_evento(
            conn,
            plano.fazenda_id,
            TipoEvento.MANEJO_RECOMENDADO,
            OrigemEvento.SISTEMA,
            ocorrido_em=agora,
            payload={
                "entidade_id": str(mov.id),
                "lote_id": str(mov.lote_id),
                "piquete_origem_id": (
                    None if mov.piquete_origem_id is None else str(mov.piquete_origem_id)
                ),
                "piquete_destino_id": str(mov.piquete_destino_id),
                "data_prevista": mov.data.isoformat(),
                "dias_previstos": mov.dias_previstos,
                "motivo": mov.motivo,
                "confianca": mov.confianca.value,
                "motivo_confianca": mov.motivo_confianca,
            },
            ator="planner",
            chave_idempotencia=f"recomendacao:{plano.id}:{mov.id}",
        )


def salvar_plano(
    conn: psycopg.Connection[Any], plano: PlanoManejo, status: StatusSalvar = "vigente"
) -> None:
    """Insert the plan; a vigente replaces the current one and records its recommendations."""
    if status not in {"vigente", "candidato"}:
        raise ValueError(f"status must be 'vigente' or 'candidato', got {status!r}")
    with conn.cursor() as cur:
        if status == "vigente":
            cur.execute(_SUBSTITUIR_VIGENTE, (plano.fazenda_id,))
        cur.execute(_DESCARTAR_CANDIDATOS, (plano.fazenda_id,))
        cur.execute(
            _INSERT_PLANO,
            (
                plano.id,
                plano.fazenda_id,
                plano.data_geracao,
                plano.data_inicio,
                plano.horizonte_dias,
                Json(plano_para_dict(plano)),
                status,
            ),
        )
    if status == "vigente":
        _registrar_recomendacoes(conn, plano)


def promover_candidato(conn: psycopg.Connection[Any], plano_id: UUID) -> PlanoManejo:
    """The producer accepted the candidate: it becomes vigente and its movements are recommended."""
    with conn.cursor() as cur:
        cur.execute("SELECT status, payload FROM plano WHERE id = %s FOR UPDATE", (plano_id,))
        row = cur.fetchone()
        if row is None or row[0] != "candidato":
            raise ValueError(f"plano {plano_id} is not a candidato")
        plano = plano_de_dict(row[1])
        cur.execute(_SUBSTITUIR_VIGENTE, (plano.fazenda_id,))
        cur.execute("UPDATE plano SET status = 'vigente' WHERE id = %s", (plano_id,))
    _registrar_recomendacoes(conn, plano)
    return plano


def descartar_plano(conn: psycopg.Connection[Any], plano_id: UUID) -> None:
    """The producer kept the current plan: the candidate is discarded."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE plano SET status = 'descartado' WHERE id = %s AND status = 'candidato'",
            (plano_id,),
        )


def _mais_recente(
    conn: psycopg.Connection[Any], fazenda_id: UUID, status: str
) -> PlanoManejo | None:
    with conn.cursor() as cur:
        cur.execute(_SELECT_MAIS_RECENTE, (fazenda_id, status))
        row = cur.fetchone()
    return None if row is None else plano_de_dict(row[0])


def carregar_plano_atual(conn: psycopg.Connection[Any], fazenda_id: UUID) -> PlanoManejo | None:
    """The most recent vigente plan, or None."""
    return _mais_recente(conn, fazenda_id, "vigente")


def carregar_candidato(conn: psycopg.Connection[Any], fazenda_id: UUID) -> PlanoManejo | None:
    """The most recent candidato plan, or None."""
    return _mais_recente(conn, fazenda_id, "candidato")


def carregar_plano(conn: psycopg.Connection[Any], plano_id: UUID) -> PlanoManejo | None:
    """A plan by id, whatever its status."""
    with conn.cursor() as cur:
        cur.execute("SELECT payload FROM plano WHERE id = %s", (plano_id,))
        row = cur.fetchone()
    return None if row is None else plano_de_dict(row[0])


def status_do_plano(conn: psycopg.Connection[Any], plano_id: UUID) -> str | None:
    """The plan's status, or None when it does not exist."""
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM plano WHERE id = %s", (plano_id,))
        row = cur.fetchone()
    return None if row is None else str(row[0])


def ids_respondidos(conn: psycopg.Connection[Any], fazenda_id: UUID) -> frozenset[UUID]:
    """Movements the producer already answered (confirmed, refused or done differently)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT entidade_id FROM evento"
            " WHERE fazenda_id = %s AND tipo = ANY(%s) AND entidade_id IS NOT NULL",
            (fazenda_id, _TIPOS_RESPOSTA),
        )
        linhas = cur.fetchall()
    return frozenset(
        valor if isinstance(valor, UUID) else UUID(str(valor)) for (valor,) in linhas
    )
