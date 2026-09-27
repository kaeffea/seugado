"""Development mode: pull updates from Telegram instead of receiving the webhook.

Run from the repo root, with the *Dev* bot's token in .env:
    uv run --env-file .env python scripts/telegram_polling.py

A bot cannot have a webhook and polling at the same time, so this removes the webhook first.
Never point it at the production bot. Stop with Ctrl+C.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seugado.delivery.bot import hoje_local, processar_update_isolado  # noqa: E402
from seugado.delivery.canais.telegram import CanalTelegram, ErroTelegram, canal_padrao  # noqa: E402

ESPERA_S = 30  # long polling: Telegram holds getUpdates open up to this long
PAUSA_APOS_ERRO_S = 5

log = logging.getLogger("telegram_polling")


def uma_volta(canal: CanalTelegram, url_banco: str, offset: int | None) -> int | None:
    """One getUpdates round; each update gets its own connection. Returns the next offset."""
    pedido: dict[str, Any] = {
        "timeout": ESPERA_S,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset is not None:
        pedido["offset"] = offset
    updates = canal.chamar_api("getUpdates", pedido, timeout=ESPERA_S + 10)
    for update in updates or []:
        offset = int(update["update_id"]) + 1  # confirmed on the next call, even if it failed
        processar_update_isolado(url_banco, update, canal, hoje_local())
    return offset


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    canal = canal_padrao()
    url_banco = os.environ["DATABASE_URL"]
    canal.chamar_api("deleteWebhook", {})
    log.info("polling started; send a message to the Dev bot (Ctrl+C stops)")
    offset: int | None = None
    while True:
        try:
            offset = uma_volta(canal, url_banco, offset)
        except ErroTelegram:
            log.exception("getUpdates failed; retrying in %s s", PAUSA_APOS_ERRO_S)
            time.sleep(PAUSA_APOS_ERRO_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("polling stopped")
