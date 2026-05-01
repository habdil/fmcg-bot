from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from crawling_bot.main import run_crawler
from telegram_bot.services.telegram_service import reject_if_not_allowed

CRAWL_LOCK = asyncio.Lock()


def _parse_max_articles(args: list[str]) -> int:
    if not args:
        return 3
    try:
        value = int(args[0])
    except ValueError:
        return 3
    return max(1, min(value, 10))


async def _run_crawl_and_notify(context: ContextTypes.DEFAULT_TYPE, chat_id: int, max_articles: int) -> None:
    try:
        async with CRAWL_LOCK:
            results = await asyncio.to_thread(run_crawler, max_articles)
        total_found = sum(item.total_found for item in results)
        total_processed = sum(item.total_processed for item in results)
        total_saved = sum(item.total_saved for item in results)
        total_failed = sum(item.total_failed for item in results)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Crawler selesai.\n"
                f"Found: {total_found}\n"
                f"Processed: {total_processed}\n"
                f"Saved: {total_saved}\n"
                f"Failed: {total_failed}\n\n"
                "Sekarang coba /insight <keyword>, /trend <keyword>, atau /forecast <keyword>."
            ),
        )
    except Exception as exc:
        await context.bot.send_message(chat_id=chat_id, text=f"Crawler gagal: {exc}")


async def crawl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    chat = update.effective_chat
    if chat is None:
        return
    if CRAWL_LOCK.locked():
        await update.effective_message.reply_text("Crawler sedang berjalan. Tunggu sampai selesai dulu.")
        return

    max_articles = _parse_max_articles(context.args)
    await update.effective_message.reply_text(
        f"Crawler mulai di background. Batas: {max_articles} artikel per source."
    )
    context.application.create_task(_run_crawl_and_notify(context, chat.id, max_articles))
