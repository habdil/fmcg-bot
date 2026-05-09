from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters

from crawling_bot.config import settings
from telegram_bot.handlers.analysis_handler import compare, forecast, insight, trend, weekly
from telegram_bot.handlers.alert_handler import alert
from telegram_bot.handlers.ask_handler import analyze
from telegram_bot.handlers.chat_handler import free_text_chat
from telegram_bot.handlers.crawl_handler import crawl, crawl_harga, status
from telegram_bot.handlers.menu_handler import menu
from telegram_bot.handlers.price_handler import price_add, price_check, price_collect
from telegram_bot.handlers.report_handler import report
from telegram_bot.handlers.search_handler import search
from telegram_bot.handlers.start_handler import start
from telegram_bot.handlers.style_handler import forget_style, style
from telegram_bot.handlers.subscription_handler import subscribe, unsubscribe
from telegram_bot.handlers.trending_handler import trending
from telegram_bot.services.reminder_service import reminder_loop

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def ensure_bot_initialized(application: Application) -> None:
    """Work around PTB start() accessing bot.id before the cached bot user exists."""
    try:
        _ = application.bot.id
    except RuntimeError:
        await application.bot.get_me()


async def setup_runtime(application: Application) -> None:
    await ensure_bot_initialized(application)
    if application.bot_data.get("reminder_task") is None:
        application.bot_data["reminder_task"] = asyncio.create_task(reminder_loop(application))


async def shutdown_runtime(application: Application) -> None:
    task = application.bot_data.pop("reminder_task", None)
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def build_application() -> Application:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start the Telegram bot.")

    application = (
        ApplicationBuilder()
        .token(settings.telegram_bot_token)
        .post_init(setup_runtime)
        .post_stop(shutdown_runtime)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("crawl", crawl))
    application.add_handler(CommandHandler("crawl_harga", crawl_harga))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("alert", alert))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("insight", insight))
    application.add_handler(CommandHandler("trend", trend))
    application.add_handler(CommandHandler("weekly", weekly))
    application.add_handler(CommandHandler("compare", compare))
    application.add_handler(CommandHandler("forecast", forecast))
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("ask", analyze))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("style", style))
    application.add_handler(CommandHandler("forget_style", forget_style))
    application.add_handler(CommandHandler("price_check", price_check))
    application.add_handler(CommandHandler("harga", price_check))
    application.add_handler(CommandHandler("price_add", price_add))
    application.add_handler(CommandHandler("price_collect", price_collect))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_chat))
    return application


def main() -> None:
    application = build_application()
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
