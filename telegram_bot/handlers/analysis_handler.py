from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.services.insight_service import (
    compare_message,
    daily_trend_brief_message,
    keyword_forecast_message,
    keyword_insight_message,
    weekly_intelligence_report_message,
)
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message


def _keyword(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args).strip()


async def insight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    keyword = _keyword(context)
    if not keyword:
        await update.effective_message.reply_text("Gunakan format: /insight <produk atau keyword>")
        return
    await _send_crawl_first_notice(update)
    message = await asyncio.to_thread(keyword_insight_message, keyword)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)


async def trend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    await _send_crawl_first_notice(update)
    message = await asyncio.to_thread(daily_trend_brief_message)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    await _send_crawl_first_notice(update)
    message = await asyncio.to_thread(weekly_intelligence_report_message)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)


async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    product_a, product_b = parse_compare_query(_keyword(context))
    if not product_a or not product_b:
        await update.effective_message.reply_text("Gunakan format: /compare minyak goreng | gula")
        return
    await _send_crawl_first_notice(update)
    message = await asyncio.to_thread(compare_message, product_a, product_b)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)


async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    keyword = _keyword(context)
    if not keyword:
        await update.effective_message.reply_text("Gunakan format: /forecast <produk atau keyword>")
        return
    await _send_crawl_first_notice(update)
    message = await asyncio.to_thread(keyword_forecast_message, keyword)
    for chunk in split_long_message(message):
        await update.effective_message.reply_text(chunk)


def parse_compare_query(text: str) -> tuple[str | None, str | None]:
    cleaned = text.strip()
    if "|" in cleaned:
        left, right = cleaned.split("|", 1)
        return left.strip() or None, right.strip() or None
    lowered = cleaned.lower()
    for separator in [" vs ", " versus ", " dibandingkan ", " dibanding "]:
        if separator in lowered:
            index = lowered.index(separator)
            left = cleaned[:index]
            right = cleaned[index + len(separator):]
            return left.strip() or None, right.strip() or None
    return None, None


async def _send_crawl_first_notice(update: Update) -> None:
    return None
