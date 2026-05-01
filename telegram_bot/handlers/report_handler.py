from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.insight_service import report_message
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    await update.effective_message.reply_text(
        "Saya crawl source publik dulu, lalu susun daily trend brief terbaru."
    )
    message = await asyncio.to_thread(report_message)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)
