"""T7: the webhook (secret check, immediate answer, own connection) and the polling loop."""

import asyncio
import importlib.util
import json
import time
from collections.abc import MutableMapping
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import pytest
from fastapi.testclient import TestClient

from seugado.api import rotas_telegram
from seugado.api.main import app
from seugado.delivery import bot
from seugado.delivery.canais.telegram import CanalTelegram
from seugado.delivery.mensagem import ERRO_INESPERADO
from tests.delivery.falsos import CanalFalso

SEGREDO = "um-segredo-de-teste-bem-longo"
CABECALHO = "X-Telegram-Bot-Api-Secret-Token"
UPDATE = {"update_id": 7, "message": {"message_id": 1, "chat": {"id": 123}, "text": "/plano"}}

cliente = TestClient(app)


@pytest.fixture
def agendados(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Webhook secret set; the background processing only records what it was given."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SEGREDO)
    lista: list[dict[str, Any]] = []
    monkeypatch.setattr(rotas_telegram, "processar_em_segundo_plano", lista.append)
    return lista


def test_sem_o_segredo_certo_da_403(
    agendados: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    for cabecalhos in ({}, {CABECALHO: "errado"}, {CABECALHO: SEGREDO + "x"}):
        assert cliente.post("/telegram/webhook", json=UPDATE, headers=cabecalhos).status_code == 403
    nao_ascii = cliente.post("/telegram/webhook", json=UPDATE, headers={CABECALHO: "ç".encode()})
    assert nao_ascii.status_code == 403  # compared as bytes: no TypeError from hmac
    lixo = cliente.post("/telegram/webhook", content=b"{nao e json", headers={CABECALHO: "x"})
    assert lixo.status_code == 403  # the secret is checked before the body is read
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET")
    vazio = cliente.post("/telegram/webhook", json=UPDATE, headers={CABECALHO: ""})
    assert vazio.status_code == 403  # no secret configured: nobody gets in
    assert agendados == []


def test_com_o_segredo_responde_ok_e_agenda(agendados: list[dict[str, Any]]) -> None:
    resposta = cliente.post("/telegram/webhook", json=UPDATE, headers={CABECALHO: SEGREDO})
    assert (resposta.status_code, resposta.json()) == (200, {"ok": True})
    assert agendados == [UPDATE]


def test_corpo_que_nao_e_update_da_400(agendados: list[dict[str, Any]]) -> None:
    for corpo in (b"{nao e json", b"[1, 2]"):
        resposta = cliente.post("/telegram/webhook", content=corpo, headers={CABECALHO: SEGREDO})
        assert resposta.status_code == 400
    assert agendados == []


def test_responde_em_menos_de_1s_mesmo_com_processamento_lento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drives the ASGI app directly: TestClient would wait for the background task."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SEGREDO)
    monkeypatch.setattr(rotas_telegram, "processar_em_segundo_plano", lambda _: time.sleep(1.5))
    corpo = json.dumps(UPDATE).encode()
    marcas: dict[str, Any] = {}

    async def chamar() -> None:
        pedidos = [{"type": "http.request", "body": corpo, "more_body": False}]

        async def receive() -> dict[str, Any]:
            if pedidos:
                return pedidos.pop()
            await asyncio.Event().wait()  # the client never disconnects on its own
            return {"type": "http.disconnect"}

        async def send(mensagem: MutableMapping[str, Any]) -> None:
            if mensagem["type"] == "http.response.start":
                marcas["status"] = mensagem["status"]
            elif not mensagem.get("more_body"):
                marcas["resposta_s"] = time.perf_counter() - inicio
                marcas["corpo"] = mensagem.get("body", b"")

        escopo = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/telegram/webhook",
            "raw_path": b"/telegram/webhook",
            "root_path": "",
            "query_string": b"",
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(corpo)).encode()),
                (CABECALHO.lower().encode(), SEGREDO.encode()),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
        inicio = time.perf_counter()
        await app(escopo, receive, send)
        marcas["total_s"] = time.perf_counter() - inicio

    asyncio.run(chamar())
    assert (marcas["status"], json.loads(marcas["corpo"])) == (200, {"ok": True})
    assert marcas["resposta_s"] < 1.0
    assert marcas["total_s"] >= 1.5  # the slow part did run, after the answer went out


class _ConexaoContada:
    fechadas = 0

    def close(self) -> None:
        self.fechadas += 1


def test_processamento_usa_conexao_propria_e_hoje_de_fortaleza(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://banco-do-teste")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    conexao = _ConexaoContada()
    abertas: list[str] = []
    chamadas: list[tuple[Any, ...]] = []

    def conectar(url: str, **opcoes: Any) -> _ConexaoContada:
        abertas.append(url)
        return conexao

    def processar(conn: Any, update: dict[str, Any], canal: Any, hoje: date) -> None:
        assert conexao.fechadas == 0  # still open while processing
        chamadas.append((conn, update, canal, hoje))

    monkeypatch.setattr(psycopg, "connect", conectar)
    monkeypatch.setattr(bot, "processar_update", processar)
    rotas_telegram.processar_em_segundo_plano(UPDATE)
    ((conn, update, canal, hoje),) = chamadas
    assert (abertas, conn, update) == (["postgresql://banco-do-teste"], conexao, UPDATE)
    assert isinstance(canal, CanalTelegram)
    assert hoje == datetime.now(ZoneInfo("America/Fortaleza")).date()
    assert conexao.fechadas == 1


def test_conexao_fecha_mesmo_se_o_processamento_explodir(monkeypatch: pytest.MonkeyPatch) -> None:
    conexao = _ConexaoContada()
    monkeypatch.setattr(psycopg, "connect", lambda url, **opcoes: conexao)

    def explodir(*args: Any) -> None:
        raise RuntimeError("inesperado")

    monkeypatch.setattr(bot, "processar_update", explodir)
    with pytest.raises(RuntimeError):
        bot.processar_update_isolado("postgresql://x", UPDATE, CanalFalso(), date(2026, 9, 30))
    assert conexao.fechadas == 1


def test_sem_banco_o_produtor_ainda_e_avisado(monkeypatch: pytest.MonkeyPatch) -> None:
    def sem_banco(url: str, **opcoes: Any) -> None:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(psycopg, "connect", sem_banco)
    canal = CanalFalso()
    bot.processar_update_isolado("postgresql://x", UPDATE, canal, date(2026, 9, 30))
    assert canal.textos == [ERRO_INESPERADO]


# --- scripts/telegram_polling.py ------------------------------------------------------------


def _script_de_polling() -> ModuleType:
    caminho = Path(__file__).resolve().parents[2] / "scripts" / "telegram_polling.py"
    spec = importlib.util.spec_from_file_location("telegram_polling", caminho)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class _ApiFalsa(CanalFalso):
    def __init__(self, respostas: list[list[dict[str, Any]]]) -> None:
        super().__init__()
        self.respostas = respostas
        self.chamadas: list[tuple[str, dict[str, Any], float]] = []

    def chamar_api(self, metodo: str, corpo: dict[str, Any], timeout: float = 15) -> Any:
        self.chamadas.append((metodo, corpo, timeout))
        return self.respostas.pop(0)


def test_polling_processa_cada_update_e_avanca_o_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    polling = _script_de_polling()
    processados: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        polling,
        "processar_update_isolado",
        lambda url, update, canal, hoje: processados.append((url, update["update_id"], hoje)),
    )
    api = _ApiFalsa([[UPDATE, {**UPDATE, "update_id": 8}], []])
    assert polling.uma_volta(api, "postgresql://x", None) == 9
    assert polling.uma_volta(api, "postgresql://x", 9) == 9  # nothing new: same offset
    permitidos = ["message", "callback_query"]
    assert api.chamadas == [
        ("getUpdates", {"timeout": 30, "allowed_updates": permitidos}, 40),
        ("getUpdates", {"timeout": 30, "allowed_updates": permitidos, "offset": 9}, 40),
    ]
    hoje = datetime.now(ZoneInfo("America/Fortaleza")).date()
    assert processados == [("postgresql://x", 7, hoje), ("postgresql://x", 8, hoje)]
