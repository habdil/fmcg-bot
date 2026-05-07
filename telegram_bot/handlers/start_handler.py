from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.menu import main_menu_keyboard
from telegram_bot.services.telegram_service import reject_if_not_allowed


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    await update.effective_message.reply_text(
        "FMCG Business Intelligence Bot aktif.\n"
        "Gunakan /analyze <pertanyaan>, /crawl, /insight <keyword>, /trend <keyword>, /forecast <keyword>, "
        "/alert, /report, /search <keyword>, /trending, /price_check <produk>, /price_add, "
        "/subscribe, /style <instruksi>, atau /unsubscribe.",
        reply_markup=main_menu_keyboard(),
    )
