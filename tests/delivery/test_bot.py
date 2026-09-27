"""Conversation tests. T5: see, use or keep a candidate plan."""

import sys
import uuid
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

import pytest

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo
from seugado.delivery.bot import Contexto, tratar_plano_candidato
from seugado.delivery.canais.base import Botao
from seugado.delivery.mensagem import (
    CANDIDATO_JA_EM_USO,
    CANDIDATO_VENCIDO,
    PLANO_MANTIDO,
    botoes_diferencas,
    botoes_plano,
    texto_diferencas,
    texto_plano,
)
from tests.delivery.falsos import (
    CanalFalso,
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
