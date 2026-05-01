from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards.menu import main_menu_keyboard
from telegram_bot.services.telegram_service import reject_if_not_allowed


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    await update.effective_message.reply_text(
        "Menu:\n"
        "/crawl [max] - Crawl public sources from Telegram\n"
        "/analyze <produk> - Product deep analysis, crawl-first\n"
        "/alert - High urgency FMCG alerts\n"
        "/report - Daily trend brief\n"
        "/search <keyword> - Search product/company/location/commodity\n"
        "/insight <keyword> - Business insight for a product/topic\n"
        "/trend - Daily FMCG trend brief\n"
        "/weekly - Weekly intelligence report\n"
        "/compare <produk A> | <produk B> - Comparative analysis\n"
        "/forecast <keyword> - Rule-based outlook and action\n"
        "/trending - Frequent entities and signals\n"
        "/subscribe - Subscribe current chat\n"
        "/unsubscribe - Disable subscription",
        reply_markup=main_menu_keyboard(),
    )
