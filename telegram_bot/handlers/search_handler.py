from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.insight_service import search_message
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    keyword = " ".join(context.args).strip()
    if not keyword:
        await update.effective_message.reply_text("Gunakan format: /search <keyword>")
        return
    message = await asyncio.to_thread(search_message, keyword)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)
