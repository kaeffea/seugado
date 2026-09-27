"""T1: Canal interface and the Telegram adapter, with a fake httpx.post."""

import traceback
import uuid
from typing import Any

import httpx
import pytest

from seugado.delivery.canais.base import Botao, Canal
from seugado.delivery.canais.telegram import CanalTelegram, ErroTelegram, canal_padrao

TOKEN = "123456:TOKEN-DE-TESTE"
URL_BASE = f"https://api.telegram.org/bot{TOKEN}"


class _PostFalso:
    """Records each call and answers with a fixed status and JSON body."""

    def __init__(self) -> None:
        self.chamadas: list[dict[str, Any]] = []
        self.status = 200
        self.corpo: dict[str, Any] = {"ok": True, "result": {}}
        self.erro: httpx.HTTPError | None = None

    def __call__(self, url: str, *, json: dict[str, Any], timeout: float) -> httpx.Response:
        self.chamadas.append({"url": url, "json": json, "timeout": timeout})
        if self.erro is not None:
            raise self.erro
        return httpx.Response(self.status, json=self.corpo, request=httpx.Request("POST", url))


@pytest.fixture
def post(monkeypatch: pytest.MonkeyPatch) -> _PostFalso:
    falso = _PostFalso()
    monkeypatch.setattr(httpx, "post", falso)
    return falso


def test_canal_telegram_cumpre_o_protocolo() -> None:
    """Static check (mypy): CanalTelegram is usable wherever a Canal is expected."""
    canal: Canal = CanalTelegram(TOKEN)
    assert isinstance(canal, CanalTelegram)


def test_enviar_texto_sem_botoes(post: _PostFalso) -> None:
    CanalTelegram(TOKEN).enviar_texto(123456789, "<b>Oi</b>")
    assert post.chamadas == [
        {
            "url": f"{URL_BASE}/sendMessage",
            "json": {"chat_id": 123456789, "text": "<b>Oi</b>", "parse_mode": "HTML"},
            "timeout": 15,
        }
    ]


def test_enviar_texto_com_botoes_monta_teclado(post: _PostFalso) -> None:
    botoes = [
        [Botao("✅ Fiz", "f:1"), Botao("❌ Não fiz", "n:1")],
        [Botao("🔄 Fiz diferente", "d:1")],
    ]
    CanalTelegram(TOKEN).enviar_texto(42, "Movimentação", botoes)
    (chamada,) = post.chamadas
    assert chamada["url"] == f"{URL_BASE}/sendMessage"
    assert chamada["json"] == {
        "chat_id": 42,
        "text": "Movimentação",
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Fiz", "callback_data": "f:1"},
                    {"text": "❌ Não fiz", "callback_data": "n:1"},
                ],
                [{"text": "🔄 Fiz diferente", "callback_data": "d:1"}],
            ]
        },
    }


def test_linhas_vazias_nao_viram_teclado(post: _PostFalso) -> None:
    CanalTelegram(TOKEN).enviar_texto(42, "texto", [[], []])
    assert "reply_markup" not in post.chamadas[0]["json"]


def test_responder_clique(post: _PostFalso) -> None:
    canal = CanalTelegram(TOKEN)
    canal.responder_clique("4382")
    canal.responder_clique("4383", "Anotado")
    assert post.chamadas == [
        {
            "url": f"{URL_BASE}/answerCallbackQuery",
            "json": {"callback_query_id": "4382"},
            "timeout": 15,
        },
        {
            "url": f"{URL_BASE}/answerCallbackQuery",
            "json": {"callback_query_id": "4383", "text": "Anotado"},
            "timeout": 15,
        },
    ]


def test_botao_aceita_ate_64_bytes() -> None:
    assert Botao("Ver", f"pv:{uuid.uuid4()}").dados.startswith("pv:")
    Botao("x", "x" * 64)
    Botao("é", "é" * 32)  # 2 bytes each in UTF-8


@pytest.mark.parametrize("dados", ["x" * 65, "é" * 33, ""])
def test_botao_fora_de_1_a_64_bytes_da_erro(dados: str) -> None:
    with pytest.raises(ValueError, match="1 to 64 bytes"):
        Botao("texto", dados)


def test_erro_http_vira_erro_telegram_sem_token(post: _PostFalso) -> None:
    post.status = 400
    post.corpo = {"ok": False, "error_code": 400, "description": "Bad Request: chat not found"}
    with pytest.raises(ErroTelegram) as info:
        CanalTelegram(TOKEN).enviar_texto(1, "oi")
    assert str(info.value) == "Telegram sendMessage: HTTP 400 Bad Request: chat not found"
    assert TOKEN not in "".join(traceback.format_exception(info.value))


def test_erro_de_rede_vira_erro_telegram_sem_token(post: _PostFalso) -> None:
    url = f"{URL_BASE}/answerCallbackQuery"
    post.erro = httpx.ConnectError(f"cannot reach {url}", request=httpx.Request("POST", url))
    with pytest.raises(ErroTelegram) as info:
        CanalTelegram(TOKEN).responder_clique("1")
    assert str(info.value) == "Telegram answerCallbackQuery: ConnectError"
    assert TOKEN not in "".join(traceback.format_exception(info.value))


def test_canal_padrao_le_o_token_do_ambiente(
    monkeypatch: pytest.MonkeyPatch, post: _PostFalso
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    canal_padrao().enviar_texto(7, "oi")
    assert post.chamadas[0]["url"] == f"{URL_BASE}/sendMessage"


def test_canal_padrao_sem_token_da_erro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        canal_padrao()


def test_token_vazio_da_erro() -> None:
    with pytest.raises(ValueError, match="token"):
        CanalTelegram("")


def test_guarda_bloqueia_rede_real() -> None:
    """The autouse guard in conftest makes an unpatched call fail instead of hitting Telegram."""
    with pytest.raises(AssertionError, match="must not call the network"):
        CanalTelegram(TOKEN).enviar_texto(1, "oi")
