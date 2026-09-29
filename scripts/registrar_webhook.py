"""Register the production Telegram webhook.

Run from the repository root:
    uv run --env-file .env python scripts/registrar_webhook.py --url https://api.onrender.com
"""

import argparse
import os
import sys
from urllib.parse import urlsplit

import httpx


def main() -> int:
    """Register the webhook and print Telegram's response without exposing credentials."""
    parser = argparse.ArgumentParser(description="Registrar webhook do Telegram")
    parser.add_argument("--url", required=True, help="URL pública HTTPS da API")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    partes = urlsplit(url)
    if partes.scheme != "https" or not partes.netloc or partes.query or partes.fragment:
        parser.error("--url deve ser uma URL HTTPS sem query ou fragmento")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    segredo = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if not token or not segredo:
        parser.error("Defina TELEGRAM_BOT_TOKEN e TELEGRAM_WEBHOOK_SECRET no ambiente")
    try:
        resposta = httpx.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": f"{url}/telegram/webhook", "secret_token": segredo},
            timeout=30.0,
        )
    except httpx.RequestError:
        print("Falha ao conectar ao Telegram para registrar o webhook.", file=sys.stderr)
        return 1
    print(resposta.text)
    if not resposta.is_success:
        return 1
    try:
        return 0 if resposta.json().get("ok") else 1
    except ValueError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
