from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.memory_service import (
    clear_response_style,
    get_chat_memory,
    save_response_style,
)
from telegram_bot.services.telegram_service import reject_if_not_allowed


RESET_TERMS = {"hapus", "reset", "forget", "clear", "kosongkan"}


async def style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    chat = update.effective_chat
    if chat is None:
        return

    raw_text = " ".join(context.args).strip()
    if not raw_text:
        memory = await asyncio.to_thread(get_chat_memory, chat.id)
        current = memory.response_style_notes if memory else None
        if current:
            await update.effective_message.reply_text(f"Gaya jawaban aktif:\n{current}")
            return
        await update.effective_message.reply_text(
            "Belum ada gaya jawaban tersimpan.\n"
            "Contoh: /style singkat, natural, tanpa kata headline, langsung ke inti dan sumber."
        )
        return

    if raw_text.lower() in RESET_TERMS:
        await _clear_style(update, chat.id)
        return

    username = update.effective_user.username if update.effective_user else None
    try:
        saved = await asyncio.to_thread(save_response_style, chat.id, username, raw_text)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await update.effective_message.reply_text(f"Siap, gaya jawaban disimpan:\n{saved}")


async def forget_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    chat = update.effective_chat
    if chat is None:
        return
    await _clear_style(update, chat.id)


async def _clear_style(update: Update, chat_id: int) -> None:
    try:
        await asyncio.to_thread(clear_response_style, chat_id)
    except Exception as exc:
        await update.effective_message.reply_text(str(exc))
        return
    await update.effective_message.reply_text("Gaya jawaban tersimpan sudah dihapus.")
