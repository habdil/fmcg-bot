from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.subscription_service import subscribe_chat, unsubscribe_chat
from telegram_bot.services.telegram_service import reject_if_not_allowed


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    chat = update.effective_chat
    user = update.effective_user
    subscribe_chat(chat.id, user.username if user else None)
    await update.effective_message.reply_text("Chat ini sudah subscribe high urgency alerts.")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    chat = update.effective_chat
    unsubscribe_chat(chat.id)
    await update.effective_message.reply_text("Subscription chat ini sudah dinonaktifkan.")
