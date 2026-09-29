"""Conversation tests. T5: see, use or keep a candidate plan. T6: processar_update."""

import logging
import random
import sys
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import pytest

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo
from seugado.delivery.bot import Contexto, processar_update, tratar_plano_candidato
from seugado.delivery.canais.base import Botao
from seugado.delivery.canais.telegram import ErroTelegram
from seugado.delivery.confirmacao import registrar_avulsa
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
    SEM_PLANO,
    botoes_alturas,
    botoes_diferencas,
    botoes_movimentacao,
    botoes_opcoes,
    botoes_plano,
    botoes_quando,
    texto_alturas,
    texto_diferencas,
    texto_ja_vinculado,
    texto_movimentacao,
    texto_plano,
)
from tests.delivery.banco import (
    RECRIA,
    VACAS,
    FazendaTeste,
    Transacoes,
    criar_fazenda,
    emular_transacoes,
    piquete,
    requer_banco,
)
from tests.delivery.falsos import (
    CanalFalso,
    CicloFalso,
    ConexaoFalsa,
    Enviado,
    PlanosFalsos,
    conexao_falsa,
    modulo_falso,
)

CHAT_ID = 123456789
QUA = date(2026, 9, 30)
DIFERENCAS = (
    DiferencaLote(
        uuid.UUID("22222222-2222-4222-8222-000000000002"),
        "Vacas com bezerro",
        (PassoPlano(date(2026, 10, 1), "Piquete 3"),),
        (PassoPlano(date(2026, 10, 1), "Piquete 4"),),
    ),
)


class _CanalQueVeCommits(CanalFalso):
    """Also records how many commits had happened when each message left."""

    def __init__(self, conexao: ConexaoFalsa) -> None:
        super().__init__()
        self._conexao = conexao
        self.commits_ao_enviar: list[int] = []

    def enviar_texto(self, chat_id: int, texto: str, botoes: Any = ()) -> None:
        self.commits_ao_enviar.append(self._conexao.commits)
        super().enviar_texto(chat_id, texto, botoes)


@dataclass
class _Cenario:
    ctx: Contexto
    canal: _CanalQueVeCommits
    conexao: ConexaoFalsa
    planos: PlanosFalsos
    vigente: PlanoManejo
    candidato: PlanoManejo
    comparacoes: list[tuple[Any, ...]] = field(default_factory=list)


@pytest.fixture
def cenario(plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch) -> _Cenario:
    """A current plan (the fixture) and a candidate for the same farm."""
    candidato = replace(plano, id=uuid.uuid4())
    planos = PlanosFalsos()
    planos.guardar(plano, "vigente")
    planos.guardar(candidato, "candidato")
    planos.respondidas = frozenset({plano.movimentacoes[0].id})
    conn, conexao = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = _CanalQueVeCommits(conexao)
    c = _Cenario(
        Contexto(conn, canal, CHAT_ID, plano.fazenda_id, QUA),
        canal,
        conexao,
        planos,
        plano,
        candidato,
    )

    def comparar_planos(*args: Any) -> tuple[DiferencaLote, ...]:
        c.comparacoes.append(args)
        return DIFERENCAS

    monkeypatch.setitem(sys.modules, "seugado.persistencia.planos", planos.modulo())
    monkeypatch.setitem(
        sys.modules,
        "seugado.planner.comparacao",
        modulo_falso("seugado.planner.comparacao", comparar_planos=comparar_planos),
    )
    return c


def test_ver_mudancas_compara_com_o_vigente(cenario: _Cenario) -> None:
    c = cenario
    tratar_plano_candidato(c.ctx, "pv", c.candidato.id)
    assert c.comparacoes == [(c.vigente, c.candidato, c.planos.respondidas, QUA)]
    assert c.canal.enviados == [
        Enviado(CHAT_ID, texto_diferencas(DIFERENCAS), botoes_diferencas(c.candidato.id))
    ]
    assert botoes_diferencas(c.candidato.id) == [
        [
            Botao("✅ Usar o plano novo", f"pu:{c.candidato.id}"),
            Botao("↩️ Manter o anterior", f"pk:{c.candidato.id}"),
        ]
    ]
    assert c.planos.status[c.candidato.id] == "candidato"
    assert c.conexao.commits == 0


def test_ver_e_usar_troca_o_plano_e_manda_completo(cenario: _Cenario) -> None:
    c = cenario
    tratar_plano_candidato(c.ctx, "pv", c.candidato.id)
    tratar_plano_candidato(c.ctx, "pu", c.candidato.id)
    assert c.planos.status == {c.vigente.id: "substituido", c.candidato.id: "vigente"}
    assert c.canal.enviados[-1] == Enviado(
        CHAT_ID,
        texto_plano(c.candidato, "Fazenda Exemplo", atualizado=True),
        botoes_plano(c.candidato),
    )
    assert c.conexao.commits == 1
    assert c.canal.commits_ao_enviar[-1] == 1  # promoted and committed before telling him


def test_manter_descarta_o_candidato_e_nada_muda(cenario: _Cenario) -> None:
    c = cenario
    tratar_plano_candidato(c.ctx, "pk", c.candidato.id)
    assert c.planos.status == {c.vigente.id: "vigente", c.candidato.id: "descartado"}
    assert c.canal.enviados == [Enviado(CHAT_ID, PLANO_MANTIDO, [])]
    assert c.conexao.commits == 1
    assert c.planos.promovidos == []


@pytest.mark.parametrize("status", ["descartado", "substituido"])
@pytest.mark.parametrize("acao", ["pv", "pu", "pk"])
def test_candidato_velho_nao_vale_mais(cenario: _Cenario, status: str, acao: str) -> None:
    c = cenario
    c.planos.status[c.candidato.id] = status
    tratar_plano_candidato(c.ctx, acao, c.candidato.id)
    assert c.canal.enviados == [Enviado(CHAT_ID, CANDIDATO_VENCIDO, [])]
    assert c.planos.status[c.candidato.id] == status
    assert c.planos.status[c.vigente.id] == "vigente"
    assert (c.conexao.commits, c.comparacoes) == (0, [])


def test_usar_duas_vezes_avisa_que_ja_esta_em_uso(cenario: _Cenario) -> None:
    c = cenario
    tratar_plano_candidato(c.ctx, "pu", c.candidato.id)
    tratar_plano_candidato(c.ctx, "pu", c.candidato.id)
    assert c.canal.enviados[-1] == Enviado(CHAT_ID, CANDIDATO_JA_EM_USO, [])
    assert c.planos.promovidos == [c.candidato.id]
    assert c.conexao.commits == 1


@pytest.mark.parametrize("acao", ["pv", "pu", "pk"])
def test_plano_inexistente_ou_de_outra_fazenda(cenario: _Cenario, acao: str) -> None:
    """Forged callback data must not touch another farm's plan."""
    c = cenario
    de_outra = replace(c.candidato, id=uuid.uuid4(), fazenda_id=uuid.uuid4())
    c.planos.guardar(de_outra, "candidato")
    tratar_plano_candidato(c.ctx, acao, de_outra.id)
    tratar_plano_candidato(c.ctx, acao, uuid.uuid4())
    assert c.canal.enviados == [Enviado(CHAT_ID, CANDIDATO_VENCIDO, [])] * 2
    assert c.planos.status[de_outra.id] == "candidato"
    assert (c.conexao.commits, c.planos.promovidos) == (0, [])


# --- T6 without a database: nothing escapes without an answer ------------------------------


def _mensagem(chat_id: int, texto: str) -> dict[str, Any]:
    return {"update_id": 1, "message": {"message_id": 1, "chat": {"id": chat_id}, "text": texto}}


def _clique(chat_id: int, dados: str) -> dict[str, Any]:
    mensagem = {"message_id": 2, "chat": {"id": chat_id}}
    return {"update_id": 2, "callback_query": {"id": "q1", "data": dados, "message": mensagem}}


def test_update_sem_chat_e_ignorado() -> None:
    conn, falsa = conexao_falsa(None)
    canal = CanalFalso()
    editada = {"message_id": 1, "chat": {"id": CHAT_ID}, "text": "oi"}
    processar_update(conn, {"update_id": 1, "edited_message": editada}, canal, QUA)
    processar_update(
        conn, {"update_id": 2, "callback_query": {"id": "q9", "data": "h:"}}, canal, QUA
    )
    assert canal.ordem == ["clique"]  # the tap is still acknowledged
    assert falsa.consultas == []


def test_erro_inesperado_responde_e_nao_sobe(caplog: pytest.LogCaptureFixture) -> None:
    conn, falsa = conexao_falsa(None, erro=psycopg.OperationalError("conexão caiu"))
    canal = CanalFalso()
    with caplog.at_level(logging.ERROR, logger="seugado.delivery.bot"):
        processar_update(conn, _mensagem(CHAT_ID, "/plano"), canal, QUA)
    assert canal.enviados == [Enviado(CHAT_ID, ERRO_INESPERADO, [])]
    assert falsa.rollbacks == 1
    assert "failed for chat 123456789" in caplog.text


class _CanalQuebrado(CanalFalso):
    def __init__(self, *, texto: bool, clique: bool) -> None:
        super().__init__()
        self._texto, self._clique = texto, clique

    def enviar_texto(self, chat_id: int, texto: str, botoes: Any = ()) -> None:
        if self._texto:
            raise ErroTelegram("Telegram sendMessage: HTTP 502")
        super().enviar_texto(chat_id, texto, botoes)

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        if self._clique:
            raise ErroTelegram("Telegram answerCallbackQuery: HTTP 400 query is too old")
        super().responder_clique(id_clique, texto)


def test_erro_ao_avisar_tambem_nao_sobe() -> None:
    conn, _ = conexao_falsa(None, erro=psycopg.OperationalError("conexão caiu"))
    processar_update(conn, _clique(CHAT_ID, "h:"), _CanalQuebrado(texto=True, clique=True), QUA)


def test_clique_que_nao_pode_ser_confirmado_ainda_recebe_resposta() -> None:
    """An expired callback query (answerCallbackQuery fails) must not cost the answer."""
    conn, _ = conexao_falsa(None)
    canal = _CanalQuebrado(texto=False, clique=True)
    processar_update(conn, _clique(CHAT_ID, "h:"), canal, QUA)
    assert canal.textos == [NAO_VINCULADO]


# --- T6 with the test database (commit/rollback emulated inside the test's transaction) ----

RECALCULO = {"ingerir_satelite": False, "atualizado": True}


@dataclass
class _Bot:
    conn: psycopg.Connection[Any]
    canal: CanalFalso
    fazenda: FazendaTeste
    plano: PlanoManejo
    planos: PlanosFalsos
    ciclo: CicloFalso
    transacoes: Transacoes
    hoje: date
    chat_id: int

    def escrever(self, texto: str) -> None:
        processar_update(self.conn, _mensagem(self.chat_id, texto), self.canal, self.hoje)

    def tocar(self, dados: str) -> None:
        processar_update(self.conn, _clique(self.chat_id, dados), self.canal, self.hoje)

    @property
    def ultimo(self) -> Enviado:
        return self.canal.enviados[-1]

    def eventos(self, tipo: str) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM evento WHERE fazenda_id = %s AND tipo = %s ORDER BY sequencia",
                (self.fazenda.id, tipo),
            )
            return [linha[0] for linha in cur.fetchall()]

    def conversa(self) -> tuple[Any, ...] | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT estado, dados FROM telegram_conversa WHERE chat_id = %s", (self.chat_id,)
            )
            return cur.fetchone()


def _novo_chat() -> int:
    return -random.randint(10**12, 10**13)


@pytest.fixture
def bot(
    conn_banco: psycopg.Connection[Any], plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> _Bot:
    """A linked farm (Recria in Piquete 2, Vacas in 5) whose current plan is the fixture."""
    fazenda = criar_fazenda(conn_banco)
    assert fazenda.chat_id is not None
    hoje = datetime.now(ZoneInfo("America/Fortaleza")).date()  # dates must not be in the future
    vigente = replace(plano, fazenda_id=fazenda.id, data_inicio=hoje)
    planos = PlanosFalsos()
    planos.guardar(vigente, "vigente")
    ciclo = CicloFalso()
    monkeypatch.setitem(sys.modules, "seugado.persistencia.planos", planos.modulo())
    monkeypatch.setitem(sys.modules, "seugado.jobs.ciclo", ciclo.modulo())
    transacoes = emular_transacoes(conn_banco)
    return _Bot(
        conn_banco, CanalFalso(), fazenda, vigente, planos, ciclo, transacoes, hoje, fazenda.chat_id
    )


def _codigo(conn: psycopg.Connection[Any], fazenda_id: uuid.UUID) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT codigo_vinculo_telegram FROM fazenda WHERE id = %s", (fazenda_id,))
        linha = cur.fetchone()
    assert linha is not None
    return str(linha[0])


def _chat_da_fazenda(conn: psycopg.Connection[Any], fazenda_id: uuid.UUID) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT telegram_chat_id FROM fazenda WHERE id = %s", (fazenda_id,))
        linha = cur.fetchone()
    assert linha is not None
    return linha[0]  # type: ignore[no-any-return]


@requer_banco
def test_start_vincula_o_chat(bot: _Bot) -> None:
    livre = criar_fazenda(bot.conn, com_chat=False)
    bot.chat_id = _novo_chat()
    bot.escrever(f"/start {_codigo(bot.conn, livre.id)}")
    assert bot.canal.textos == [
        "Pronto! A Fazenda Exemplo está conectada. Você vai receber o plano da semana aqui."
    ]
    assert _chat_da_fazenda(bot.conn, livre.id) == bot.chat_id
    assert bot.transacoes.commits == 1


@requer_banco
def test_start_com_codigo_invalido_ou_de_outra_fazenda(bot: _Bot) -> None:
    outra = criar_fazenda(bot.conn, com_chat=False)
    bot.escrever("/start 0000000000000000")
    bot.escrever(f"/start {_codigo(bot.conn, outra.id)}")
    bot.escrever("/start")
    bot.escrever(f"/start@SeuGadoBot {_codigo(bot.conn, bot.fazenda.id)}")
    ja_ligado = texto_ja_vinculado("Fazenda Exemplo")
    assert bot.canal.textos[:3] == [CODIGO_INVALIDO, ja_ligado, ja_ligado]
    assert bot.canal.textos[3].startswith("Pronto! A Fazenda Exemplo está conectada.")
    assert _chat_da_fazenda(bot.conn, outra.id) is None


@requer_banco
def test_chat_sem_fazenda_so_aceita_start(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[0]
    bot.chat_id = _novo_chat()
    bot.escrever("/plano")
    bot.tocar(f"f:{mov.id}")
    assert bot.canal.textos == [NAO_VINCULADO, NAO_VINCULADO]
    assert bot.canal.cliques == [("q1", None)]
    assert all(e["entidade_id"] != str(mov.id) for e in bot.eventos("manejo_confirmado"))


@requer_banco
def test_plano_e_alturas(bot: _Bot) -> None:
    bot.escrever("/plano")
    assert bot.ultimo == Enviado(
        bot.chat_id, texto_plano(bot.plano, "Fazenda Exemplo"), botoes_plano(bot.plano)
    )
    bot.tocar("h:")
    assert bot.ultimo == Enviado(bot.chat_id, texto_alturas(bot.plano), botoes_alturas(bot.plano))
    bot.planos.status[bot.plano.id] = "substituido"
    bot.escrever("/alturas")
    assert bot.ultimo.texto == SEM_PLANO


@requer_banco
def test_m_mostra_a_movimentacao(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[0]
    bot.tocar(f"m:{mov.id}")
    assert bot.canal.ordem == ["clique", "texto"]  # responder_clique always comes first
    assert bot.ultimo == Enviado(bot.chat_id, texto_movimentacao(mov), botoes_movimentacao(mov))
    bot.tocar(f"m:{uuid.uuid4()}")
    bot.tocar("m:nao-e-um-id")
    assert bot.canal.textos[-2:] == [MOVIMENTACAO_ANTIGA, MOVIMENTACAO_ANTIGA]


@requer_banco
def test_f_gera_manejo_confirmado(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[0]  # Recria: Piquete 2 -> Piquete 6
    bot.tocar(f"f:{mov.id}")
    assert bot.eventos("manejo_confirmado")[-1] == {
        "entidade_id": str(mov.id),
        "lote_id": str(RECRIA),
        "piquete_destino_id": str(piquete(6)),
        "data_execucao": min(mov.data, bot.hoje).isoformat(),
    }
    assert bot.ultimo.texto == "✅ Anotado: Recria no Piquete 6."
    assert bot.transacoes.commits == 1
    assert bot.ciclo.chamadas == []
    bot.tocar(f"f:{mov.id}")
    bot.tocar(f"m:{mov.id}")
    assert bot.canal.textos[-2:] == [JA_RESPONDIDA, JA_RESPONDIDA]
    respostas = [e for e in bot.eventos("manejo_confirmado") if e["entidade_id"] == str(mov.id)]
    assert len(respostas) == 1


@requer_banco
def test_n_registra_recusa_e_recalcula(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[1]
    bot.tocar(f"n:{mov.id}")
    assert bot.eventos("manejo_recusado") == [{"entidade_id": str(mov.id), "motivo": None}]
    assert bot.ultimo.texto == NAO_FIZ
    assert bot.ciclo.chamadas == [(bot.fazenda.id, RECALCULO)]


@requer_banco
def test_d_o1_o0_gera_divergente_e_recalcula(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[0]  # Recria, recommended Piquete 2 -> Piquete 6
    bot.tocar(f"d:{mov.id}")
    livres = [f"Piquete {n}" for n in (1, 3, 4, 6, 7, 8)]  # not 2/5 (occupied) nor 9 (inactive)
    assert bot.ultimo == Enviado(
        bot.chat_id, "Para qual piquete o Recria foi?", botoes_opcoes(livres)
    )
    bot.tocar("o:1")  # Piquete 3
    assert bot.ultimo == Enviado(bot.chat_id, QUANDO, botoes_quando())
    bot.tocar("o:0")  # today
    assert bot.eventos("manejo_divergente") == [
        {
            "entidade_id": str(mov.id),
            "lote_id": str(RECRIA),
            "piquete_real_id": str(piquete(3)),
            "data_execucao": bot.hoje.isoformat(),
            "observacao": None,
        }
    ]
    assert bot.ultimo.texto == "✅ Anotado: Recria no Piquete 3. Recalculando o plano…"
    assert bot.ciclo.chamadas == [(bot.fazenda.id, RECALCULO)]
    assert bot.conversa() is None


@requer_banco
def test_a_28_gera_altura_e_r_recalcula(bot: _Bot) -> None:
    bot.tocar(f"a:{piquete(4)}")
    assert bot.ultimo.texto == "Digite a altura do Piquete 4 em centímetros (só o número)."
    bot.escrever("28")
    assert bot.eventos("altura_medida")[-1] == {
        "entidade_id": bot.eventos("altura_medida")[-1]["entidade_id"],
        "piquete_id": str(piquete(4)),
        "data": bot.hoje.isoformat(),
        "altura_cm": 28.0,
        "meio": "bot",
    }
    assert bot.canal.textos[-2] == "Anotado: Piquete 4 com 28 cm hoje."
    medidas = {piquete(4): 28.0}
    assert bot.ultimo == Enviado(
        bot.chat_id, texto_alturas(bot.plano, medidas), botoes_alturas(bot.plano)
    )
    assert "• Piquete 4: 28 cm (medida com régua)" in bot.ultimo.texto
    assert bot.conversa() is None
    bot.tocar("r:")
    assert bot.ultimo.texto == REFAZENDO
    assert bot.ciclo.chamadas == [(bot.fazenda.id, RECALCULO)]


@requer_banco
def test_altura_invalida_pede_de_novo(bot: _Bot) -> None:
    bot.tocar(f"a:{piquete(4)}")
    for texto in ("abc", "500", "0"):
        bot.escrever(texto)
    assert bot.canal.textos[-3:] == [NUMERO_INVALIDO, ALTURA_FORA_DA_FAIXA, ALTURA_FORA_DA_FAIXA]
    assert bot.eventos("altura_medida") == []
    bot.escrever("30,5 cm")
    assert bot.eventos("altura_medida")[-1]["altura_cm"] == 30.5
    assert "Anotado: Piquete 4 com 30,5 cm hoje." in bot.canal.textos


@requer_banco
def test_mover_registra_avulsa_e_recalcula(bot: _Bot) -> None:
    bot.escrever("/mover")
    assert bot.ultimo == Enviado(
        bot.chat_id, QUAL_LOTE, botoes_opcoes(["Recria", "Vacas com bezerro"])
    )
    bot.tocar("o:1")  # Vacas com bezerro
    assert bot.ultimo.texto == "Para qual piquete o Vacas com bezerro foi?"
    bot.tocar("o:0")  # Piquete 1
    bot.tocar("o:1")  # yesterday
    avulsa = bot.eventos("manejo_confirmado")[-1]
    assert avulsa["lote_id"] == str(VACAS)
    assert avulsa["piquete_destino_id"] == str(piquete(1))
    assert avulsa["data_execucao"] == (bot.hoje - timedelta(days=1)).isoformat()
    assert avulsa["entidade_id"] not in {str(mov.id) for mov in bot.plano.movimentacoes}
    assert bot.ultimo.texto == "✅ Anotado: Vacas com bezerro no Piquete 1. Recalculando o plano…"
    assert bot.ciclo.chamadas == [(bot.fazenda.id, RECALCULO)]


@requer_banco
def test_comando_ou_outro_botao_encerra_a_conversa(bot: _Bot) -> None:
    bot.tocar(f"a:{piquete(4)}")
    bot.escrever("/plano")
    bot.escrever("28")
    bot.tocar(f"a:{piquete(4)}")
    bot.tocar("h:")
    bot.escrever("28")
    assert bot.canal.textos.count(NAO_ENTENDI) == 2
    assert bot.eventos("altura_medida") == []


@requer_banco
def test_opcao_sem_conversa_ou_fora_da_lista(bot: _Bot) -> None:
    bot.tocar("o:0")
    bot.tocar(f"d:{bot.plano.movimentacoes[0].id}")
    bot.tocar("o:99")
    bot.tocar("o:abc")
    assert bot.canal.textos.count(OPCAO_VENCIDA) == 3
    assert bot.conversa() is not None  # a wrong option does not end the step


@requer_banco
def test_texto_qualquer_e_ajuda(bot: _Bot) -> None:
    for texto in ("bom dia", "/ajuda", "/qualquer", "35"):
        bot.escrever(texto)
    assert bot.canal.textos == [NAO_ENTENDI, AJUDA, NAO_ENTENDI, NAO_ENTENDI]


@requer_banco
def test_recalculo_que_falha_avisa_e_guarda_a_resposta(
    bot: _Bot, caplog: pytest.LogCaptureFixture
) -> None:
    bot.ciclo.erro = RuntimeError("clima fora do ar")
    mov = bot.plano.movimentacoes[1]
    with caplog.at_level(logging.ERROR, logger="seugado.delivery.bot"):
        bot.tocar(f"n:{mov.id}")
    assert bot.canal.textos[-2:] == [NAO_FIZ, RECALCULO_FALHOU]
    assert bot.eventos("manejo_recusado") == [{"entidade_id": str(mov.id), "motivo": None}]
    assert bot.transacoes.rollbacks == 1
    assert "recalculation failed" in caplog.text


@requer_banco
def test_divergente_para_piquete_que_ficou_ocupado(bot: _Bot) -> None:
    mov = bot.plano.movimentacoes[0]
    bot.tocar(f"d:{mov.id}")
    bot.tocar("o:2")  # Piquete 4
    registrar_avulsa(bot.conn, bot.fazenda.id, VACAS, piquete(4), bot.hoje, "equipe")
    bot.conn.commit()
    bot.tocar("o:0")
    assert bot.ultimo.texto == (
        "Piquete 4 está com o lote Vacas com bezerro. Dois lotes não podem dividir um piquete."
    )
    assert bot.eventos("manejo_divergente") == []
    assert bot.conversa() is None
    assert bot.ciclo.chamadas == []


@requer_banco
def test_piquete_de_outra_fazenda_nao_e_aceito(bot: _Bot) -> None:
    bot.tocar(f"a:{uuid.uuid4()}")
    assert bot.ultimo.texto == "Não encontrei esse piquete."
    assert bot.conversa() is None


@requer_banco
def test_plano_candidato_pelo_telegram(bot: _Bot) -> None:
    candidato = replace(bot.plano, id=uuid.uuid4())
    bot.planos.guardar(candidato, "candidato")
    bot.tocar("pv:nao-e-um-id")
    bot.tocar(f"pk:{candidato.id}")
    assert bot.canal.textos == [CANDIDATO_VENCIDO, PLANO_MANTIDO]
    assert bot.planos.status[candidato.id] == "descartado"
