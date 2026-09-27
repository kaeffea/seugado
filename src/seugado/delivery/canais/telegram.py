"""Telegram Bot API adapter for Canal, over plain httpx (no bot library, ADR-022)."""

import os
from collections.abc import Sequence
from typing import Any

import httpx

from seugado.delivery.canais.base import Botao

URL_API = "https://api.telegram.org"
TIMEOUT_S = 15


class ErroTelegram(RuntimeError):
    """A Bot API call failed. The message never carries the URL, which embeds the token."""


def _descricao(resposta: httpx.Response) -> str:
    try:
        corpo = resposta.json()
    except ValueError:
        return ""
    return str(corpo.get("description", "")) if isinstance(corpo, dict) else ""


class CanalTelegram:
    """Canal backed by the Telegram Bot API."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("empty Telegram bot token")
        self._token = token

    def enviar_texto(
        self, chat_id: int, texto: str, botoes: Sequence[Sequence[Botao]] = ()
    ) -> None:
        """Send an HTML message; reply_markup only when there is at least one button."""
        corpo: dict[str, Any] = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}
        teclado = [
            [{"text": botao.texto, "callback_data": botao.dados} for botao in linha]
            for linha in botoes
            if linha
        ]
        if teclado:
            corpo["reply_markup"] = {"inline_keyboard": teclado}
        self._chamar("sendMessage", corpo)

    def responder_clique(self, id_clique: str, texto: str | None = None) -> None:
        """Answer a callback query so Telegram stops the button's loading spinner."""
        corpo: dict[str, Any] = {"callback_query_id": id_clique}
        if texto is not None:
            corpo["text"] = texto
        self._chamar("answerCallbackQuery", corpo)

    def _chamar(self, metodo: str, corpo: dict[str, Any]) -> None:
        # `from None` drops httpx's own exception, whose message and request carry the URL.
        try:
            resposta = httpx.post(
                f"{URL_API}/bot{self._token}/{metodo}", json=corpo, timeout=TIMEOUT_S
            )
            resposta.raise_for_status()
        except httpx.HTTPStatusError as e:
            codigo = e.response.status_code
            descricao = _descricao(e.response)
            raise ErroTelegram(f"Telegram {metodo}: HTTP {codigo} {descricao}".rstrip()) from None
        except httpx.HTTPError as e:
            raise ErroTelegram(f"Telegram {metodo}: {type(e).__name__}") from None


def canal_padrao() -> CanalTelegram:
    """Build the production channel from TELEGRAM_BOT_TOKEN."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return CanalTelegram(token)
