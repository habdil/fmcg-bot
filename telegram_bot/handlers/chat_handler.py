from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from chat_engine import ChatEngine
from chat_engine.schemas import UserContext
from telegram_bot.services.memory_service import (
    extract_style_instruction,
    get_chat_memory,
    save_response_style,
)
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message

CHAT_LOCK = asyncio.Lock()


async def free_text_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    message = update.effective_message
    if not message or not message.text:
        return

    question = message.text.strip()
    if len(question) < 4:
        await message.reply_text("Tulis pertanyaan bisnis yang lebih spesifik, atau gunakan /menu.")
        return

    chat = update.effective_chat
    if chat is None:
        return
    if CHAT_LOCK.locked():
        await message.reply_text("Analisis lain sedang berjalan. Tunggu sampai selesai dulu.")
        return

    username = update.effective_user.username if update.effective_user else None
    style_instruction = extract_style_instruction(question)
    if style_instruction:
        try:
            saved = await asyncio.to_thread(save_response_style, chat.id, username, style_instruction)
        except Exception as exc:
            await message.reply_text(str(exc))
            return
        await message.reply_text(f"Siap, gaya jawaban disimpan:\n{saved}")
        return

    context.application.create_task(_run_chat_and_notify(context, chat.id, question, username))


async def _run_chat_and_notify(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    question: str,
    username: str | None,
) -> None:
    try:
        async with CHAT_LOCK:
            memory = await asyncio.to_thread(get_chat_memory, chat_id)
            user_context = UserContext(
                chat_id=str(chat_id),
                username=username,
                style_instructions=memory.response_style_notes if memory else None,
                business_context=memory.business_context if memory else None,
            )
            result = await asyncio.to_thread(
                ChatEngine().handle_message,
                question,
                user_context=user_context,
                crawl_first=True,
                max_sources=8,
                max_articles_per_source=2,
            )
        for chunk in split_long_message(result.answer):
            await context.bot.send_message(chat_id=chat_id, text=chunk)
    except Exception as exc:
        await context.bot.send_message(chat_id=chat_id, text=f"Maaf, analisis belum berhasil diproses: {exc}")
