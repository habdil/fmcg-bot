from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.insight_service import alert_messages
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message


async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    messages = await asyncio.to_thread(alert_messages)
    for message in messages:
        for chunk in split_long_message(message):
            await update.effective_message.reply_text(chunk)
