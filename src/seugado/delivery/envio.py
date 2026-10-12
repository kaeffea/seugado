"""Outbound messages started by the scheduled routine (jobs/ciclo.py calls these)."""

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, cast
from uuid import UUID

import psycopg

from seugado.contratos import DiferencaLote, Movimentacao, PlanoManejo
from seugado.delivery.canais.base import Canal
from seugado.delivery.canais.telegram import canal_padrao
from seugado.delivery.mensagem import (
    botoes_candidato,
    botoes_lembrete,
    botoes_ordem_do_dia,
    botoes_plano,
    texto_candidato,
    texto_lembrete,
    texto_ordem_do_dia,
    texto_plano,
)

_SELECT_FAZENDA = "SELECT nome, telegram_chat_id FROM fazenda WHERE id = %s"


def _fazenda_e_chat(conn: psycopg.Connection[Any], fazenda_id: UUID) -> tuple[str, int | None]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_FAZENDA, (fazenda_id,))
        linha = cur.fetchone()
    if linha is None:
        raise ValueError(f"unknown fazenda {fazenda_id}")
    return str(linha[0]), cast("int | None", linha[1])


def enviar_plano(
    conn: psycopg.Connection[Any],
    plano: PlanoManejo,
    atualizado: bool = False,
    canal: Canal | None = None,
) -> bool:
    """Send the plan to the farm's chat; False when no Telegram is linked (not an error)."""
    nome, chat_id = _fazenda_e_chat(conn, plano.fazenda_id)
    if chat_id is None:
        return False
    if canal is None:
        canal = canal_padrao()
    canal.enviar_texto(chat_id, texto_plano(plano, nome, atualizado), botoes_plano(plano))
    return True


def avisar_plano_candidato(
    conn: psycopg.Connection[Any],
    plano: PlanoManejo,
    diferencas: tuple[DiferencaLote, ...],
    canal: Canal | None = None,
) -> bool:
    """Ask whether the producer wants to see a candidate plan; False when no Telegram."""
    _, chat_id = _fazenda_e_chat(conn, plano.fazenda_id)
    if chat_id is None:
        return False
    if canal is None:
        canal = canal_padrao()
    canal.enviar_texto(chat_id, texto_candidato(diferencas), botoes_candidato(plano.id))
    return True


def enviar_lembrete(
    conn: psycopg.Connection[Any],
    fazenda_id: UUID,
    pendentes: Sequence[Movimentacao],
    canal: Canal | None = None,
) -> bool:
    """Remind the producer of unanswered movements; False when no Telegram."""
    _, chat_id = _fazenda_e_chat(conn, fazenda_id)
    if chat_id is None:
        return False
    if canal is None:
        canal = canal_padrao()
    canal.enviar_texto(chat_id, texto_lembrete(pendentes), botoes_lembrete(pendentes))
    return True


def enviar_ordem_do_dia(
    conn: psycopg.Connection[Any], fazenda_id: UUID, hoje: date, canal: Canal | None = None
) -> bool:
    """Send only what is for today in the current plan (ADR-026 §5).

    False when no current plan covers today or no Telegram is linked (not an error).
    The moves come from the current plan, so every button points at a movement the bot knows.
    """
    from seugado.persistencia.planos import (  # noqa: PLC0415
        carregar_plano_atual,
        ids_respondidos,
    )

    plano: PlanoManejo | None = carregar_plano_atual(conn, fazenda_id)
    if plano is None:
        return False
    fim = plano.data_inicio + timedelta(days=plano.horizonte_dias)
    if not plano.data_inicio <= hoje < fim:
        return False
    nome, chat_id = _fazenda_e_chat(conn, fazenda_id)
    if chat_id is None:
        return False
    respondidas: frozenset[UUID] = ids_respondidos(conn, fazenda_id)
    if canal is None:
        canal = canal_padrao()
    canal.enviar_texto(
        chat_id,
        texto_ordem_do_dia(plano, nome, hoje, respondidas),
        botoes_ordem_do_dia(plano, hoje, respondidas),
    )
    return True
