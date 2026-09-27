"""T3: sending the weekly plan and the candidate-plan notice."""

import os
import random
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import date
from typing import Any, cast

import httpx
import psycopg
import pytest

from seugado.contratos import DiferencaLote, PassoPlano, PlanoManejo
from seugado.delivery.envio import avisar_plano_candidato, enviar_plano
from seugado.delivery.mensagem import (
    botoes_candidato,
    botoes_plano,
    texto_candidato,
    texto_plano,
)
from tests.delivery.falsos import CanalFalso, Enviado

CHAT_ID = 123456789


class _CursorFalso:
    def __init__(self, conexao: "_ConexaoFalsa") -> None:
        self._conexao = conexao

    def __enter__(self) -> "_CursorFalso":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self._conexao.consultas.append((sql, params))

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._conexao.linha


class _ConexaoFalsa:
    """Answers the fazenda SELECT with one fixed row (or none) and records the query."""

    def __init__(self, linha: tuple[Any, ...] | None) -> None:
        self.linha = linha
        self.consultas: list[tuple[str, tuple[Any, ...]]] = []

    def cursor(self) -> _CursorFalso:
        return _CursorFalso(self)


def _conexao(linha: tuple[Any, ...] | None) -> tuple[psycopg.Connection[Any], _ConexaoFalsa]:
    falsa = _ConexaoFalsa(linha)
    return cast("psycopg.Connection[Any]", falsa), falsa


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
    conn, falsa = _conexao(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    assert enviar_plano(conn, plano, canal=canal) is True
    assert falsa.consultas == [
        ("SELECT nome, telegram_chat_id FROM fazenda WHERE id = %s", (plano.fazenda_id,))
    ]
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_plano(plano, "Fazenda Exemplo"), botoes_plano(plano))
    ]


def test_enviar_plano_atualizado(plano: PlanoManejo) -> None:
    conn, _ = _conexao(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    enviar_plano(conn, plano, atualizado=True, canal=canal)
    assert canal.enviados[0].texto.startswith("🔄 <b>Plano atualizado — Fazenda Exemplo</b>")


def test_sem_chat_vinculado_nao_envia_nem_cria_canal(
    plano: PlanoManejo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a token canal_padrao() would raise, and the conftest guard blocks any HTTP."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    conn, _ = _conexao(("Fazenda Exemplo", None))
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
    conn, _ = _conexao(("Fazenda Exemplo", CHAT_ID))
    assert enviar_plano(conn, plano) is True
    ((url, corpo),) = chamadas
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert corpo["chat_id"] == CHAT_ID
    assert corpo["text"] == texto_plano(plano, "Fazenda Exemplo")
    assert len(corpo["reply_markup"]["inline_keyboard"]) == len(botoes_plano(plano))


def test_fazenda_inexistente_da_erro(plano: PlanoManejo) -> None:
    conn, _ = _conexao(None)
    with pytest.raises(ValueError, match="unknown fazenda"):
        enviar_plano(conn, plano, canal=CanalFalso())


def test_avisar_plano_candidato(plano: PlanoManejo) -> None:
    conn, _ = _conexao(("Fazenda Exemplo", CHAT_ID))
    canal = CanalFalso()
    diferencas = _diferencas()
    assert avisar_plano_candidato(conn, plano, diferencas, canal=canal) is True
    assert canal.enviados == [
        Enviado(CHAT_ID, texto_candidato(diferencas), botoes_candidato(plano.id))
    ]
    assert "mudou para 2 lotes" in canal.enviados[0].texto


banco = pytest.mark.skipif(
    not os.environ.get("SEUGADO_TEST_DATABASE_URL"), reason="needs SEUGADO_TEST_DATABASE_URL"
)


@pytest.fixture
def conn_banco() -> Iterator[psycopg.Connection[Any]]:
    """Real connection; everything is rolled back, nothing is committed to the shared DB."""
    conn = psycopg.connect(os.environ["SEUGADO_TEST_DATABASE_URL"])
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _fazenda(conn: psycopg.Connection[Any], chat_id: int | None) -> uuid.UUID:
    fazenda_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fazenda (id, nome, telegram_chat_id) VALUES (%s, %s, %s)",
            (fazenda_id, "Fazenda Teste", chat_id),
        )
    return fazenda_id


@banco
def test_banco_enviar_plano(conn_banco: psycopg.Connection[Any], plano: PlanoManejo) -> None:
    chat_id = -random.randint(10**12, 10**13)  # far from real chat ids; unique index on it
    com_chat = replace(plano, fazenda_id=_fazenda(conn_banco, chat_id))
    sem_chat = replace(plano, fazenda_id=_fazenda(conn_banco, None))
    canal = CanalFalso()
    assert enviar_plano(conn_banco, sem_chat, canal=canal) is False
    assert enviar_plano(conn_banco, com_chat, canal=canal) is True
    assert canal.enviados == [
        Enviado(chat_id, texto_plano(com_chat, "Fazenda Teste"), botoes_plano(com_chat))
    ]
