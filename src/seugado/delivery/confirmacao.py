"""Producer answers become events; daily reminder of what is still unanswered.

Every register function rebuilds the projection but never commits: bot.py does.
"""

from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg

from seugado.contratos import Movimentacao, PlanoManejo
from seugado.core.models import OrigemEvento, TipoEvento
from seugado.delivery.canais.base import Canal
from seugado.delivery.envio import enviar_lembrete
from seugado.persistencia.eventos import registrar_evento
from seugado.persistencia.projecao_db import reconstruir_projecao

ALTURA_MAXIMA_CM = 400.0

_TIPOS_RESPOSTA = [
    TipoEvento.MANEJO_CONFIRMADO.value,
    TipoEvento.MANEJO_RECUSADO.value,
    TipoEvento.MANEJO_DIVERGENTE.value,
]

_SELECT_RESPOSTA = (
    "SELECT tipo FROM evento WHERE fazenda_id = %s AND entidade_id = %s AND tipo = ANY(%s)"
    " ORDER BY sequencia LIMIT 1"
)
_SELECT_TIMEZONE = "SELECT timezone FROM fazenda WHERE id = %s"
_SELECT_LOTE = (
    "SELECT nome, piquete_atual_id FROM estado_lote WHERE fazenda_id = %s AND lote_id = %s"
)
_SELECT_PIQUETE = (
    "SELECT p.nome, p.ativo, p.lote_atual_id, l.nome FROM estado_piquete p"
    " LEFT JOIN estado_lote l ON l.fazenda_id = p.fazenda_id AND l.lote_id = p.lote_atual_id"
    " WHERE p.fazenda_id = %s AND p.piquete_id = %s"
)
_SELECT_LIVRES = (
    "SELECT piquete_id, nome FROM estado_piquete"
    " WHERE fazenda_id = %s AND ativo AND lote_atual_id IS NULL ORDER BY nome"
)


class RespostaInvalida(ValueError):
    """The answer cannot be recorded. The message is plain Portuguese for the producer."""


def _chave_resposta(mov_id: UUID) -> str:
    """One answer per movement (Fiz, Não fiz or Fiz diferente), even with repeated taps."""
    return f"resposta:{mov_id}"


def _gravar(  # noqa: PLR0913, PLR0917 — mirrors registrar_evento
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    tipo: TipoEvento,
    payload: dict[str, Any],
    ator: str,
    chave_idempotencia: str | None = None,
) -> None:
    registrar_evento(
        conn,
        fazenda_id,
        tipo,
        OrigemEvento.PRODUTOR,
        ocorrido_em=datetime.now(UTC),
        payload=payload,
        ator=ator,
        chave_idempotencia=chave_idempotencia,
    )
    reconstruir_projecao(conn, fazenda_id)


def _um(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def resposta_existente(conn: psycopg.Connection[Any], fazenda_id: UUID, mov_id: UUID) -> str | None:
    """Event type of the producer's answer to this movement, or None if not answered yet."""
    linha = _um(conn, _SELECT_RESPOSTA, (fazenda_id, mov_id, _TIPOS_RESPOSTA))
    return None if linha is None else str(linha[0])


def _exigir_sem_resposta(conn: psycopg.Connection[Any], fazenda_id: UUID, mov_id: UUID) -> None:
    if resposta_existente(conn, fazenda_id, mov_id) is not None:
        raise RespostaInvalida("Você já respondeu esta movimentação.")


def piquetes_livres(conn: psycopg.Connection[Any], fazenda_id: UUID) -> list[tuple[UUID, str]]:
    """Active, empty piquetes (id, nome): the only valid destinations for a lote."""
    with conn.cursor() as cur:
        cur.execute(_SELECT_LIVRES, (fazenda_id,))
        return [(cast(UUID, linha[0]), str(linha[1])) for linha in cur.fetchall()]


def _validar_destino(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    lote_id: UUID,
    piquete_id: UUID,
    data_execucao: date,
) -> None:
    """Same rule as piquetes_livres, plus a date that is not in the future."""
    fuso = _um(conn, _SELECT_TIMEZONE, (fazenda_id,))
    if fuso is None:
        raise ValueError(f"unknown fazenda {fazenda_id}")
    if data_execucao > datetime.now(ZoneInfo(str(fuso[0]))).date():
        raise RespostaInvalida("A data não pode ser depois de hoje.")
    lote = _um(conn, _SELECT_LOTE, (fazenda_id, lote_id))
    if lote is None:
        raise RespostaInvalida("Não encontrei esse lote.")
    piquete = _um(conn, _SELECT_PIQUETE, (fazenda_id, piquete_id))
    if piquete is None:
        raise RespostaInvalida("Não encontrei esse piquete.")
    lote_nome, piquete_atual_id = lote
    nome, ativo, ocupante_id, ocupante_nome = piquete
    if not ativo:
        raise RespostaInvalida(f"{nome} não está ativo.")
    if piquete_id == piquete_atual_id:
        raise RespostaInvalida(f"O lote {lote_nome} já está nesse piquete.")
    if ocupante_id is not None:
        raise RespostaInvalida(
            f"{nome} está com o lote {ocupante_nome}. Dois lotes não podem dividir um piquete."
        )


def registrar_fiz(
    conn: psycopg.Connection[Any], fazenda_id: UUID, mov: Movimentacao, hoje: date, ator: str
) -> None:
    """Done as recommended: tapped before the day means done today, after it means on the day."""
    _exigir_sem_resposta(conn, fazenda_id, mov.id)
    payload = {
        "entidade_id": str(mov.id),
        "lote_id": str(mov.lote_id),
        "piquete_destino_id": str(mov.piquete_destino_id),
        "data_execucao": min(mov.data, hoje).isoformat(),
    }
    _gravar(conn, fazenda_id, TipoEvento.MANEJO_CONFIRMADO, payload, ator, _chave_resposta(mov.id))


def registrar_nao_fiz(
    conn: psycopg.Connection[Any], fazenda_id: UUID, mov: Movimentacao, ator: str
) -> None:
    """Not done: the lote stays where it is."""
    _exigir_sem_resposta(conn, fazenda_id, mov.id)
    payload = {"entidade_id": str(mov.id), "motivo": None}
    _gravar(conn, fazenda_id, TipoEvento.MANEJO_RECUSADO, payload, ator, _chave_resposta(mov.id))


def registrar_diferente(  # noqa: PLR0913, PLR0917 — signature fixed by LEO.md
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    mov: Movimentacao,
    piquete_real_id: UUID,
    data_execucao: date,
    ator: str,
) -> None:
    """Moved to another piquete or on another day (ADR-007: the most valuable answer)."""
    _exigir_sem_resposta(conn, fazenda_id, mov.id)
    _validar_destino(conn, fazenda_id, mov.lote_id, piquete_real_id, data_execucao)
    payload = {
        "entidade_id": str(mov.id),
        "lote_id": str(mov.lote_id),
        "piquete_real_id": str(piquete_real_id),
        "data_execucao": data_execucao.isoformat(),
        "observacao": None,
    }
    _gravar(conn, fazenda_id, TipoEvento.MANEJO_DIVERGENTE, payload, ator, _chave_resposta(mov.id))


def registrar_avulsa(  # noqa: PLR0913, PLR0917 — signature fixed by LEO.md
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    lote_id: UUID,
    piquete_id: UUID,
    data_execucao: date,
    ator: str,
) -> None:
    """A move nobody recommended: a confirmation with a fresh id and no idempotency key."""
    _validar_destino(conn, fazenda_id, lote_id, piquete_id, data_execucao)
    payload = {
        "entidade_id": str(uuid4()),
        "lote_id": str(lote_id),
        "piquete_destino_id": str(piquete_id),
        "data_execucao": data_execucao.isoformat(),
    }
    _gravar(conn, fazenda_id, TipoEvento.MANEJO_CONFIRMADO, payload, ator)


def registrar_altura(  # noqa: PLR0913, PLR0917 — signature fixed by LEO.md
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    piquete_id: UUID,
    altura_cm: float,
    hoje: date,
    ator: str,
) -> None:
    """Grass height measured with a ruler and typed into the bot."""
    if not 0 < altura_cm <= ALTURA_MAXIMA_CM:
        raise RespostaInvalida("A altura precisa ser maior que 0 e no máximo 400 cm.")
    if _um(conn, _SELECT_PIQUETE, (fazenda_id, piquete_id)) is None:
        raise RespostaInvalida("Não encontrei esse piquete.")
    payload = {
        "entidade_id": str(uuid4()),
        "piquete_id": str(piquete_id),
        "data": hoje.isoformat(),
        "altura_cm": altura_cm,
        "meio": "bot",
    }
    _gravar(conn, fazenda_id, TipoEvento.ALTURA_MEDIDA, payload, ator)


def lembrar_pendentes(
    conn: psycopg.Connection[Any], fazenda_id: UUID, hoje: date, canal: Canal | None = None
) -> int:
    """Remind past, unanswered movements of the current plan; how many were reminded.

    Records nothing and does not commit: until the producer answers, the lote stays put.
    """
    # Imported here, not at the top: persistencia/planos.py (João) only reaches main at the
    # Monday integration (LEO.md, section 2). The ignore covers both before and after it.
    from seugado.persistencia.planos import (  # type: ignore[import-not-found, unused-ignore]  # noqa: PLC0415
        carregar_plano_atual,
        ids_respondidos,
    )

    plano: PlanoManejo | None = carregar_plano_atual(conn, fazenda_id)
    if plano is None:
        return 0
    respondidas: frozenset[UUID] = ids_respondidos(conn, fazenda_id)
    pendentes = [m for m in plano.movimentacoes if m.data < hoje and m.id not in respondidas]
    if not pendentes or not enviar_lembrete(conn, fazenda_id, pendentes, canal):
        return 0
    return len(pendentes)
