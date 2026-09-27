"""T3: sending the weekly plan and the candidate-plan notice."""

import uuid
from dataclasses import replace
from datetime import date
from typing import Any

import httpx
import psycopg
import pytest

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo
from seugado.delivery.envio import avisar_plano_candidato, enviar_lembrete, enviar_plano
from seugado.delivery.mensagem import (
    botoes_candidato,
    botoes_lembrete,
    botoes_plano,
    texto_candidato,
    texto_lembrete,
    texto_plano,
)
from tests.delivery.banco import criar_fazenda, requer_banco
from tests.delivery.falsos import CanalFalso, Enviado, conexao_falsa

CHAT_ID = 123456789


def _diferencas() -> tuple[DiferencaLote, ...]:
    return (
        DiferencaLote(
            uuid.uuid4(),
            "Recria",
            (PassoPlano(date(2026, 10, 1), "Piquete 3"),),
            (PassoPlano(date(2026, 10, 1), "Piquete 4"),),
        ),
        DiferencaLote(uuid.uuid4(), "Vacas com bezerro", (), ()),
    )


def test_enviar_plano_manda_texto_e_botoes(plano: PlanoManejo) -> None:
    conn, falsa = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    assert enviar_plano(conn, plano, canal=canal) is True
    assert falsa.consultas == [
        ("SELECT nome, telegram_chat_id FROM fazenda WHERE id = %s", (plano.fazenda_id,))
    ]
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_plano(plano, "Fazenda Exemplo"), botoes_plano(plano))
    ]


def test_enviar_plano_atualizado(plano: PlanoManejo) -> None:
    conn, _ = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    enviar_plano(conn, plano, atualizado=True, canal=canal)
    assert canal.enviados[0].texto.startswith("🔄 <b>Plano atualizado — Fazenda Exemplo</b>")


def test_sem_chat_vinculado_nao_envia_nem_cria_canal(
    plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a token canal_padrao() would raise, and the conftest guard blocks any HTTP."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    conn, _ = conexao_falsa(("Fazenda Exemplo", None))
    assert enviar_plano(conn, plano) is False
    assert avisar_plano_candidato(conn, plano, _diferencas()) is False
    canal = CanalFalso()
    assert enviar_plano(conn, plano, canal=canal) is False
    assert avisar_plano_candidato(conn, plano, _diferencas(), canal=canal) is False
    assert canal.enviados == []


def test_sem_canal_usa_o_telegram(plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[tuple[str, dict[str, Any]]] = []

    def post_falso(url: str, *, json: dict[str, Any], timeout: float) -> httpx.Response:
        chamadas.append((url, json))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(httpx, "post", post_falso)
    conn, _ = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    assert enviar_plano(conn, plano) is True
    ((url, corpo),) = chamadas
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert corpo["chat_id"] == CHAT_ID
    assert corpo["text"] == texto_plano(plano, "Fazenda Exemplo")
    assert len(corpo["reply_markup"]["inline_keyboard"]) == len(botoes_plano(plano))


def test_fazenda_inexistente_da_erro(plano: PlanoManejo) -> None:
    conn, _ = conexao_falsa(None)
    with pytest.raises(ValueError, match="unknown fazenda"):
        enviar_plano(conn, plano, canal=CanalFalso())


def test_avisar_plano_candidato(plano: PlanoManejo) -> None:
    conn, _ = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    diferencas = _diferencas()
    assert avisar_plano_candidato(conn, plano, diferencas, canal=canal) is True
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_candidato(diferencas), botoes_candidato(plano.id))
    ]
    assert "mudou para 2 lotes" in canal.enviados[0].texto


def test_enviar_lembrete(plano: PlanoManejo) -> None:
    pendentes = plano.movimentacoes[:2]
    conn, _ = conexao_falsa(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    assert enviar_lembrete(conn, plano.fazenda_id, pendentes, canal=canal) is True
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_lembrete(pendentes), botoes_lembrete(pendentes))
    ]
    sem_chat, _ = conexao_falsa(("Fazenda Exemplo", None))
    assert enviar_lembrete(sem_chat, plano.fazenda_id, pendentes, canal=canal) is False
    assert len(canal.enviados) == 1


@requer_banco
def test_banco_enviar_plano(conn_banco: psycopg.Connection[Any], plano: PlanoManejo) -> None:
    fazenda = criar_fazenda(conn_banco)
    assert fazenda.chat_id is not None
    com_chat = replace(plano, fazenda_id=fazenda.id)
    sem_chat = replace(plano, fazenda_id=criar_fazenda(conn_banco, com_chat=False).id)
    canal = CanalFalso()
    assert enviar_plano(conn_banco, sem_chat, canal=canal) is False
    assert enviar_plano(conn_banco, com_chat, canal=canal) is True
    assert canal.enviados == [
        Enviado(fazenda.chat_id, texto_plano(com_chat, "Fazenda Exemplo"), botoes_plano(com_chat))
    ]
