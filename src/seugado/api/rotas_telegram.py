"""Telegram routes (owner: Leo): the production bot's webhook."""

import hmac
import os
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from seugado.delivery.bot import hoje_local, processar_update_isolado
from seugado.delivery.canais.telegram import canal_padrao

router = APIRouter(tags=["telegram"])


def _segredo_confere(recebido: str | None) -> bool:
    esperado = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if not esperado or recebido is None:
        return False  # no secret configured means nobody gets in
    return hmac.compare_digest(recebido.encode(), esperado.encode())


def processar_em_segundo_plano(update: dict[str, Any]) -> None:
    """Runs after the response was sent, on its own connection (LEO.md, T7)."""
    processar_update_isolado(os.environ["DATABASE_URL"], update, canal_padrao(), hoje_local())


@router.post("/telegram/webhook")
async def webhook(
    request: Request,
    tarefas: BackgroundTasks,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    """Receive a Telegram Update, answer at once and process it in the background.

    The secret is checked before the body is even read, so strangers only ever get a 403.
    """
    if not _segredo_confere(x_telegram_bot_api_secret_token):
        raise HTTPException(status_code=403, detail="invalid secret token")
    try:
        update = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="body is not JSON") from None
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="body is not a Telegram Update")
    tarefas.add_task(processar_em_segundo_plano, update)
    return {"ok": True}
