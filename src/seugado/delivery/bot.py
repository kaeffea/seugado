"""The conversation: which tap or message becomes which event or reply."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

import psycopg

from seugado.contratos import DiferencaLote, PlanoManejo
from seugado.delivery.canais.base import Botao, Canal
from seugado.delivery.envio import enviar_plano
from seugado.delivery.mensagem import (
    CANDIDATO_JA_EM_USO,
    CANDIDATO_VENCIDO,
    PLANO_MANTIDO,
    botoes_diferencas,
    texto_diferencas,
)


@dataclass(frozen=True, slots=True)
class Contexto:
    """Who is talking (a chat and its farm), today's date and where the answer goes."""

    conn: psycopg.Connection[Any]
    canal: Canal
    chat_id: int
    fazenda_id: UUID
    hoje: date

    def responder(self, texto: str, botoes: Sequence[Sequence[Botao]] = ()) -> None:
        self.canal.enviar_texto(self.chat_id, texto, botoes)


def tratar_plano_candidato(ctx: Contexto, acao: str, plano_id: UUID) -> None:
    """pv: see what changes, pu: switch to the candidate, pk: keep the current plan (T5).

    The plan id comes from callback data, which a modified client can forge (Bot API docs),
    so it only counts when it is a plan of this chat's own farm.
    """
    # Imported here, not at the top: persistencia/planos.py and planner/comparacao.py (João)
    # only reach main at the Monday integration (LEO.md, section 2). The ignores hold either way.
    from seugado.persistencia.planos import (  # type: ignore[import-not-found, unused-ignore]  # noqa: PLC0415
        carregar_plano,
        carregar_plano_atual,
        descartar_plano,
        ids_respondidos,
        promover_candidato,
        status_do_plano,
    )
    from seugado.planner.comparacao import (  # type: ignore[import-not-found, unused-ignore]  # noqa: PLC0415
        comparar_planos,
    )

    candidato: PlanoManejo | None = carregar_plano(ctx.conn, plano_id)
    if candidato is None or candidato.fazenda_id != ctx.fazenda_id:
        ctx.responder(CANDIDATO_VENCIDO)
        return
    status: str | None = status_do_plano(ctx.conn, plano_id)
    if status != "candidato":
        ctx.responder(CANDIDATO_JA_EM_USO if status == "vigente" else CANDIDATO_VENCIDO)
        return
    if acao == "pv":
        vigente: PlanoManejo | None = carregar_plano_atual(ctx.conn, ctx.fazenda_id)
        if vigente is None:  # a candidate is only ever saved beside a current plan
            ctx.responder(CANDIDATO_VENCIDO)
            return
        respondidas: frozenset[UUID] = ids_respondidos(ctx.conn, ctx.fazenda_id)
        diferencas: tuple[DiferencaLote, ...] = comparar_planos(
            vigente, candidato, respondidas, ctx.hoje
        )
        ctx.responder(texto_diferencas(diferencas), botoes_diferencas(plano_id))
    elif acao == "pu":
        promovido: PlanoManejo = promover_candidato(ctx.conn, plano_id)
        ctx.conn.commit()
        enviar_plano(ctx.conn, promovido, atualizado=True, canal=ctx.canal)
    elif acao == "pk":
        descartar_plano(ctx.conn, plano_id)
        ctx.conn.commit()
        ctx.responder(PLANO_MANTIDO)
    else:
        raise ValueError(f"unknown candidate action {acao!r}")
