"""The conversation: which tap or message becomes which event or reply.

Callback data (LEO.md, T6): m: f: n: d: <movement id>, a: <piquete id>, h:, r:,
pv: pu: pk: <plan id> and o:<n>, the n-th option of the step saved in telegram_conversa.
"""

import html
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Json

from seugado.contratos import DiferencaLote, Movimentacao, PlanoManejo
from seugado.delivery.canais.base import Botao, Canal
from seugado.delivery.confirmacao import (
    ALTURA_MAXIMA_CM,
    RespostaInvalida,
    piquetes_livres,
    registrar_altura,
    registrar_avulsa,
    registrar_diferente,
    registrar_fiz,
    registrar_nao_fiz,
    resposta_existente,
)
from seugado.delivery.envio import enviar_plano
from seugado.delivery.mensagem import (
    AJUDA,
    ALTURA_FORA_DA_FAIXA,
    CANDIDATO_JA_EM_USO,
    CANDIDATO_VENCIDO,
    CODIGO_INVALIDO,
    ERRO_INESPERADO,
    JA_RESPONDIDA,
    MOVIMENTACAO_ANTIGA,
    NAO_ENTENDI,
    NAO_FIZ,
    NAO_VINCULADO,
    NUMERO_INVALIDO,
    OPCAO_VENCIDA,
    PLANO_MANTIDO,
    QUAL_LOTE,
    QUANDO,
    RECALCULO_FALHOU,
    REFAZENDO,
    SEM_LOTES,
    SEM_PLANO,
    botoes_alturas,
    botoes_diferencas,
    botoes_movimentacao,
    botoes_opcoes,
    botoes_quando,
    texto_altura_anotada,
    texto_alturas,
    texto_anotado_recalculando,
    texto_diferencas,
    texto_fiz,
    texto_ja_vinculado,
    texto_movimentacao,
    texto_para_qual_piquete,
    texto_pedir_altura,
    texto_sem_piquete_livre,
    texto_vinculado,
)

log = logging.getLogger(__name__)

FUSO_DO_BOT = ZoneInfo("America/Fortaleza")

_NUMERO = re.compile(r"\s*(\d+(?:[.,]\d+)?)\s*(?:cm)?\s*", re.IGNORECASE)
_DIAS_PARA_TRAS = 3  # o:0 today, o:1 yesterday, o:2 the day before

_SELECT_FAZENDA_DO_CHAT = "SELECT id, nome FROM fazenda WHERE telegram_chat_id = %s"
_SELECT_FAZENDA_DO_CODIGO = "SELECT id, nome FROM fazenda WHERE codigo_vinculo_telegram = %s"
_UPDATE_VINCULO = "UPDATE fazenda SET telegram_chat_id = %s WHERE codigo_vinculo_telegram = %s"
_SELECT_ESTADO = "SELECT estado, dados FROM telegram_conversa WHERE chat_id = %s"
_UPSERT_ESTADO = (
    "INSERT INTO telegram_conversa (chat_id, estado, dados, atualizado_em)"
    " VALUES (%s, %s, %s, now())"
    " ON CONFLICT (chat_id) DO UPDATE"
    " SET estado = EXCLUDED.estado, dados = EXCLUDED.dados, atualizado_em = now()"
)
_DELETE_ESTADO = "DELETE FROM telegram_conversa WHERE chat_id = %s"
_SELECT_LOTES = "SELECT lote_id, nome FROM estado_lote WHERE fazenda_id = %s ORDER BY nome"
_SELECT_NOME_LOTE = "SELECT nome FROM estado_lote WHERE fazenda_id = %s AND lote_id = %s"
_SELECT_NOME_PIQUETE = "SELECT nome FROM estado_piquete WHERE fazenda_id = %s AND piquete_id = %s"
_SELECT_MEDIDAS = (
    "SELECT piquete_id, altura_cm FROM altura_atual WHERE fazenda_id = %s AND data >= %s"
)


@dataclass(frozen=True, slots=True)
class Contexto:
    """Who is talking (a chat and its farm), today's date and where the answer goes."""

    conn: psycopg.Connection[Any]
    canal: Canal
    chat_id: int
    fazenda_id: UUID
    hoje: date

    @property
    def ator(self) -> str:
        return f"telegram:{self.chat_id}"

    def responder(self, texto: str, botoes: Sequence[Sequence[Botao]] = ()) -> None:
        self.canal.enviar_texto(self.chat_id, texto, botoes)


# --- entry point --------------------------------------------------------------------------


def processar_update(
    conn: psycopg.Connection[Any], update: dict[str, Any], canal: Canal, hoje: date
) -> None:
    """Handle one Telegram update. Never raises: failures are logged and the producer told."""
    clique = update.get("callback_query")
    if isinstance(clique, dict) and "id" in clique:
        try:
            canal.responder_clique(str(clique["id"]))
        except Exception:  # an expired query must not cost the answer itself
            log.warning("answerCallbackQuery failed", exc_info=True)
    chat_id = _chat_id(update)
    if chat_id is None:
        return  # edited messages, member updates, inline queries: nothing to answer
    try:
        _processar(conn, update, canal, hoje, chat_id)
    except RespostaInvalida as erro:
        _desfazer(conn)
        _encerrar_conversa(conn, chat_id)
        _avisar(canal, chat_id, html.escape(str(erro), quote=False))
    except Exception:
        log.exception("update %s failed for chat %s", update.get("update_id"), chat_id)
        _desfazer(conn)
        _avisar(canal, chat_id, ERRO_INESPERADO)


def hoje_local() -> date:
    """The conversation's today: America/Fortaleza for webhook and polling (LEO.md, T7)."""
    return datetime.now(FUSO_DO_BOT).date()


def processar_update_isolado(
    url_banco: str, update: dict[str, Any], canal: Canal, hoje: date
) -> None:
    """processar_update on a connection of its own, opened and closed here.

    If the database cannot even be reached, the producer is still told something went wrong.
    """
    try:
        conn = psycopg.connect(url_banco, autocommit=False)
    except Exception:
        log.exception("no database connection for update %s", update.get("update_id"))
        chat_id = _chat_id(update)
        if chat_id is not None:
            _avisar(canal, chat_id, ERRO_INESPERADO)
        return
    try:
        processar_update(conn, update, canal, hoje)
    finally:
        conn.close()


def _chat_id(update: dict[str, Any]) -> int | None:
    mensagem = update.get("message")
    if mensagem is None and isinstance(update.get("callback_query"), dict):
        mensagem = update["callback_query"].get("message")
    if not isinstance(mensagem, dict) or not isinstance(mensagem.get("chat"), dict):
        return None
    chat_id = mensagem["chat"].get("id")
    return chat_id if isinstance(chat_id, int) else None


def _processar(
    conn: psycopg.Connection[Any],
    update: dict[str, Any],
    canal: Canal,
    hoje: date,
    chat_id: int,
) -> None:
    fazenda = _um(conn, _SELECT_FAZENDA_DO_CHAT, (chat_id,))
    clique = update.get("callback_query")
    mensagem = update.get("message")
    texto = mensagem.get("text") if isinstance(mensagem, dict) and not clique else None
    comando, argumento = _comando(texto if isinstance(texto, str) else None)
    if comando == "/start":
        _vincular(conn, canal, chat_id, fazenda, argumento)
        return
    if fazenda is None:
        canal.enviar_texto(chat_id, NAO_VINCULADO)
        return
    ctx = Contexto(conn, canal, chat_id, cast(UUID, fazenda[0]), hoje)
    if isinstance(clique, dict):
        _tratar_clique(ctx, str(clique.get("data", "")))
    elif comando is not None:
        _tratar_comando(ctx, comando)
    else:
        _tratar_texto(ctx, texto if isinstance(texto, str) else "")


def _comando(texto: str | None) -> tuple[str | None, str]:
    """'/start@SeuGadoBot abc' -> ('/start', 'abc'); plain text -> (None, '')."""
    if not texto or not texto.startswith("/"):
        return None, ""
    primeiro, _, resto = texto.strip().partition(" ")
    return primeiro.split("@", 1)[0].lower(), resto.strip()


def _vincular(
    conn: psycopg.Connection[Any],
    canal: Canal,
    chat_id: int,
    fazenda: tuple[Any, ...] | None,
    codigo: str,
) -> None:
    """/start <codigo>: link this chat to the farm whose link code it carries."""
    if not codigo:
        canal.enviar_texto(chat_id, texto_ja_vinculado(fazenda[1]) if fazenda else NAO_VINCULADO)
        return
    alvo = _um(conn, _SELECT_FAZENDA_DO_CODIGO, (codigo,))
    if alvo is None:
        canal.enviar_texto(chat_id, CODIGO_INVALIDO)
    elif fazenda is not None and fazenda[0] != alvo[0]:
        canal.enviar_texto(chat_id, texto_ja_vinculado(fazenda[1]))  # one chat, one farm
    else:
        with conn.cursor() as cur:
            cur.execute(_UPDATE_VINCULO, (chat_id, codigo))
            cur.execute(_DELETE_ESTADO, (chat_id,))
        conn.commit()
        canal.enviar_texto(chat_id, texto_vinculado(alvo[1]))


# --- commands and free text ---------------------------------------------------------------


def _tratar_comando(ctx: Contexto, comando: str) -> None:
    _encerrar_conversa(ctx.conn, ctx.chat_id)  # any command starts over
    if comando == "/plano":
        plano = _plano_vigente(ctx)
        if plano is None:
            ctx.responder(SEM_PLANO)
        else:
            enviar_plano(ctx.conn, plano, canal=ctx.canal)
    elif comando == "/alturas":
        _mostrar_alturas(ctx)
    elif comando == "/mover":
        _iniciar_mover(ctx)
    elif comando == "/ajuda":
        ctx.responder(AJUDA)
    else:
        ctx.responder(NAO_ENTENDI)


def _tratar_texto(ctx: Contexto, texto: str) -> None:
    """Only a number is expected, and only right after "Corrigir <piquete>"."""
    estado = _ler_estado(ctx)
    if estado is None or estado[0] != "altura":
        ctx.responder(NAO_ENTENDI)
        return
    achado = _NUMERO.fullmatch(texto)
    if achado is None:
        ctx.responder(NUMERO_INVALIDO)  # the step stays open: he can type again
        return
    altura = float(achado.group(1).replace(",", "."))
    if not 0 < altura <= ALTURA_MAXIMA_CM:
        ctx.responder(ALTURA_FORA_DA_FAIXA)
        return
    piquete_id = UUID(estado[1]["piquete_id"])
    registrar_altura(ctx.conn, ctx.fazenda_id, piquete_id, altura, ctx.hoje, ctx.ator)
    _salvar_estado(ctx, None)
    ctx.conn.commit()
    ctx.responder(texto_altura_anotada(_nome_do_piquete(ctx, piquete_id), altura))
    _mostrar_alturas(ctx)


def _mostrar_alturas(ctx: Contexto) -> None:
    plano = _plano_vigente(ctx)
    if plano is None:
        ctx.responder(SEM_PLANO)
        return
    with ctx.conn.cursor() as cur:
        cur.execute(_SELECT_MEDIDAS, (ctx.fazenda_id, plano.data_inicio))
        medidas = {cast(UUID, linha[0]): float(linha[1]) for linha in cur.fetchall()}
    ctx.responder(texto_alturas(plano, medidas), botoes_alturas(plano))


def _iniciar_mover(ctx: Contexto) -> None:
    with ctx.conn.cursor() as cur:
        cur.execute(_SELECT_LOTES, (ctx.fazenda_id,))
        lotes = [(cast(UUID, linha[0]), str(linha[1])) for linha in cur.fetchall()]
    if not lotes:
        ctx.responder(SEM_LOTES)
        return
    _salvar_estado(ctx, "mover_lote", {"opcoes": [str(lote_id) for lote_id, _ in lotes]})
    ctx.conn.commit()
    ctx.responder(QUAL_LOTE, botoes_opcoes([nome for _, nome in lotes]))


# --- button taps --------------------------------------------------------------------------


def _tratar_clique(ctx: Contexto, dados: str) -> None:
    prefixo, _, resto = dados.partition(":")
    if prefixo == "o":
        _tratar_opcao(ctx, resto)
        return
    _encerrar_conversa(ctx.conn, ctx.chat_id)  # any other button starts over
    ident = _uuid(resto)
    if prefixo == "h":
        _mostrar_alturas(ctx)
    elif prefixo == "r":
        _recalcular(ctx, REFAZENDO)
    elif prefixo in {"pv", "pu", "pk"}:
        if ident is None:
            ctx.responder(CANDIDATO_VENCIDO)
        else:
            tratar_plano_candidato(ctx, prefixo, ident)
    elif prefixo == "a" and ident is not None:
        _pedir_altura(ctx, ident)
    elif prefixo in {"m", "f", "n", "d"}:
        mov = _movimentacao(ctx, ident)
        if mov is None:
            ctx.responder(MOVIMENTACAO_ANTIGA)
        else:
            _tratar_movimentacao(ctx, prefixo, mov)
    else:
        ctx.responder(NAO_ENTENDI)


def _tratar_movimentacao(ctx: Contexto, prefixo: str, mov: Movimentacao) -> None:
    if prefixo in {"m", "d"} and resposta_existente(ctx.conn, ctx.fazenda_id, mov.id):
        ctx.responder(JA_RESPONDIDA)
    elif prefixo == "m":
        ctx.responder(texto_movimentacao(mov), botoes_movimentacao(mov))
    elif prefixo == "f":
        registrar_fiz(ctx.conn, ctx.fazenda_id, mov, ctx.hoje, ctx.ator)
        ctx.conn.commit()
        ctx.responder(texto_fiz(mov.lote_nome, mov.piquete_destino_nome))
    elif prefixo == "n":
        registrar_nao_fiz(ctx.conn, ctx.fazenda_id, mov, ctx.ator)
        ctx.conn.commit()
        _recalcular(ctx, NAO_FIZ)
    else:  # "d": which piquete did the lote really go to?
        _perguntar_piquete(ctx, mov.lote_nome, "divergente_piquete", {"mov_id": str(mov.id)})


def _pedir_altura(ctx: Contexto, piquete_id: UUID) -> None:
    nome = _nome_do_piquete(ctx, piquete_id)  # a forged id of another farm fails
    _salvar_estado(ctx, "altura", {"piquete_id": str(piquete_id)})
    ctx.conn.commit()
    ctx.responder(texto_pedir_altura(nome))


def _perguntar_piquete(ctx: Contexto, lote_nome: str, estado: str, dados: dict[str, Any]) -> None:
    """Offer only active, empty piquetes (the lote's own is occupied by itself)."""
    livres = piquetes_livres(ctx.conn, ctx.fazenda_id)
    if not livres:
        _salvar_estado(ctx, None)
        ctx.conn.commit()
        ctx.responder(texto_sem_piquete_livre(lote_nome))
        return
    _salvar_estado(ctx, estado, {**dados, "opcoes": [str(p) for p, _ in livres]})
    ctx.conn.commit()
    ctx.responder(texto_para_qual_piquete(lote_nome), botoes_opcoes([n for _, n in livres]))


def _tratar_opcao(ctx: Contexto, resto: str) -> None:
    """o:<n> in the multi-step flows: Fiz diferente (d:) and a move nobody recommended (/mover)."""
    estado = _ler_estado(ctx)
    n = int(resto) if resto.isdigit() else -1
    if estado is None:
        ctx.responder(OPCAO_VENCIDA)
        return
    passo, dados = estado
    opcoes: list[str] = dados.get("opcoes", [])
    quando = passo in {"divergente_data", "mover_data"}
    if not 0 <= n < (_DIAS_PARA_TRAS if quando else len(opcoes)):
        ctx.responder(OPCAO_VENCIDA)
    elif passo == "mover_lote":
        lote_id = UUID(opcoes[n])
        lote_nome = _nome_do_lote(ctx, lote_id)
        _perguntar_piquete(ctx, lote_nome, "mover_piquete", {"lote_id": str(lote_id)})
    elif passo in {"divergente_piquete", "mover_piquete"}:
        chave = "mov_id" if passo == "divergente_piquete" else "lote_id"
        proximo = "divergente_data" if passo == "divergente_piquete" else "mover_data"
        _salvar_estado(ctx, proximo, {chave: dados[chave], "piquete_id": opcoes[n]})
        ctx.conn.commit()
        ctx.responder(QUANDO, botoes_quando())
    elif quando:
        _registrar_movimento(ctx, passo, dados, ctx.hoje - timedelta(days=n))
    else:
        ctx.responder(OPCAO_VENCIDA)


def _registrar_movimento(ctx: Contexto, passo: str, dados: dict[str, Any], data: date) -> None:
    piquete_id = UUID(dados["piquete_id"])
    if passo == "divergente_data":
        mov = _movimentacao(ctx, _uuid(dados["mov_id"]))
        if mov is None:
            _salvar_estado(ctx, None)
            ctx.conn.commit()
            ctx.responder(MOVIMENTACAO_ANTIGA)
            return
        lote_nome = mov.lote_nome
        registrar_diferente(ctx.conn, ctx.fazenda_id, mov, piquete_id, data, ctx.ator)
    else:
        lote_id = UUID(dados["lote_id"])
        lote_nome = _nome_do_lote(ctx, lote_id)
        registrar_avulsa(ctx.conn, ctx.fazenda_id, lote_id, piquete_id, data, ctx.ator)
    _salvar_estado(ctx, None)
    ctx.conn.commit()
    piquete_nome = _nome_do_piquete(ctx, piquete_id)
    _recalcular(ctx, texto_anotado_recalculando(lote_nome, piquete_nome))


# --- candidate plan (T5) ------------------------------------------------------------------


def tratar_plano_candidato(ctx: Contexto, acao: str, plano_id: UUID) -> None:
    """pv: see what changes, pu: switch to the candidate, pk: keep the current plan (T5).

    The plan id comes from callback data, which a modified client can forge (Bot API docs),
    so it only counts when it is a plan of this chat's own farm.
    """
    from seugado.persistencia.planos import (  # noqa: PLC0415
        carregar_plano,
        carregar_plano_atual,
        descartar_plano,
        ids_respondidos,
        promover_candidato,
        status_do_plano,
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
        from seugado.planner.comparacao import (  # noqa: PLC0415
            comparar_planos,
        )

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


# --- recalculation ------------------------------------------------------------------------


def _recalcular(ctx: Contexto, aviso: str) -> None:
    """Rebuild the plan now; executar_ciclo saves it as current and sends "Plano atualizado".

    Called after the answer is committed, so a failure here never loses what he told us.
    """
    ctx.responder(aviso)
    try:
        from seugado.jobs.ciclo import (  # noqa: PLC0415
            executar_ciclo,
        )

        executar_ciclo(ctx.conn, ctx.fazenda_id, ingerir_satelite=False, atualizado=True)
    except Exception:
        log.exception("recalculation failed for fazenda %s", ctx.fazenda_id)
        _desfazer(ctx.conn)
        ctx.responder(RECALCULO_FALHOU)


# --- small helpers ------------------------------------------------------------------------


def _plano_vigente(ctx: Contexto) -> PlanoManejo | None:
    from seugado.persistencia.planos import (  # noqa: PLC0415
        carregar_plano_atual,
    )

    plano: PlanoManejo | None = carregar_plano_atual(ctx.conn, ctx.fazenda_id)
    return plano


def _movimentacao(ctx: Contexto, mov_id: UUID | None) -> Movimentacao | None:
    """The movement, only if it belongs to this farm's current plan."""
    plano = _plano_vigente(ctx)
    if plano is None or mov_id is None:
        return None
    return next((mov for mov in plano.movimentacoes if mov.id == mov_id), None)


def _uuid(texto: str) -> UUID | None:
    try:
        return UUID(texto)
    except ValueError:
        return None


def _um(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...]) -> tuple[Any, ...] | None:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def _nome_do_piquete(ctx: Contexto, piquete_id: UUID) -> str:
    linha = _um(ctx.conn, _SELECT_NOME_PIQUETE, (ctx.fazenda_id, piquete_id))
    if linha is None:
        raise RespostaInvalida("Não encontrei esse piquete.")
    return str(linha[0])


def _nome_do_lote(ctx: Contexto, lote_id: UUID) -> str:
    linha = _um(ctx.conn, _SELECT_NOME_LOTE, (ctx.fazenda_id, lote_id))
    if linha is None:
        raise RespostaInvalida("Não encontrei esse lote.")
    return str(linha[0])


def _ler_estado(ctx: Contexto) -> tuple[str, dict[str, Any]] | None:
    linha = _um(ctx.conn, _SELECT_ESTADO, (ctx.chat_id,))
    return None if linha is None else (str(linha[0]), dict(linha[1]))


def _salvar_estado(ctx: Contexto, estado: str | None, dados: dict[str, Any] | None = None) -> None:
    """Overwrite this chat's conversation step (None ends it). The caller commits."""
    with ctx.conn.cursor() as cur:
        if estado is None:
            cur.execute(_DELETE_ESTADO, (ctx.chat_id,))
        else:
            cur.execute(_UPSERT_ESTADO, (ctx.chat_id, estado, Json(dados or {})))


def _encerrar_conversa(conn: psycopg.Connection[Any], chat_id: int) -> None:
    """End any open step now (committed), so an old step never swallows a new action."""
    try:
        with conn.cursor() as cur:
            cur.execute(_DELETE_ESTADO, (chat_id,))
            apagou = cur.rowcount > 0
        if apagou:
            conn.commit()
    except Exception:
        log.exception("could not clear conversation of chat %s", chat_id)
        _desfazer(conn)


def _desfazer(conn: psycopg.Connection[Any]) -> None:
    try:
        conn.rollback()
    except Exception:
        log.exception("rollback failed")


def _avisar(canal: Canal, chat_id: int, texto: str) -> None:
    try:
        canal.enviar_texto(chat_id, texto)
    except Exception:
        log.exception("could not tell chat %s about a failure", chat_id)
