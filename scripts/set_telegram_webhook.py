from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.config import settings
from telegram import Bot


def _webhook_url() -> str:
    if not settings.telegram_webhook_url:
        raise RuntimeError("TELEGRAM_WEBHOOK_URL is required.")
    url = settings.telegram_webhook_url.rstrip("/")
    if url.endswith("/telegram/webhook"):
        return url
    return f"{url}/telegram/webhook"


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
    async with Bot(settings.telegram_bot_token) as bot:
        await bot.set_webhook(url=_webhook_url(), allowed_updates=["message"])
    print(f"Telegram webhook set to {_webhook_url()}")


if __name__ == "__main__":
    asyncio.run(main())
