from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from crawling_bot.services.analysis_service import analyze_question
from telegram_bot.services.insight_service import (
    compare_message,
    daily_trend_brief_message,
    weekly_intelligence_report_message,
)
from telegram_bot.services.telegram_service import reject_if_not_allowed, split_long_message

ANALYZE_LOCK = asyncio.Lock()


def _question_from_command(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args).strip()


async def _run_analysis_and_notify(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    question: str,
) -> None:
    try:
        async with ANALYZE_LOCK:
            result = await asyncio.to_thread(
                analyze_question,
                question,
                crawl_first=True,
                max_sources=8,
                max_articles_per_source=2,
                evidence_limit=20,
            )

        header = f"Aku rangkum untuk: {result.query.normalized_keyword}\n\n"
        for chunk in split_long_message(header + result.answer):
            await context.bot.send_message(chat_id=chat_id, text=chunk)
    except Exception as exc:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Maaf, analisisnya belum berhasil aku proses. Coba ulang sebentar lagi ya.",
        )


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    question = _question_from_command(context)
    if not question:
        await update.effective_message.reply_text(
            "Gunakan format: /analyze <pertanyaan>\n"
            "Contoh: /analyze Tolong analisis produk minyak goreng 2 liter"
        )
        return
    await _start_analysis(update, context, question)


async def free_text_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    message = update.effective_message
    if not message or not message.text:
        return
    question = message.text.strip()
    if len(question) < 4:
        await message.reply_text("Tulis sedikit lebih lengkap ya. Contoh: produk mana yang perlu saya push minggu ini?")
        return
    lower = question.lower()
    if _is_daily_trend_query(lower):
        await _send_generated_message(update, daily_trend_brief_message)
        return
    if _is_weekly_query(lower):
        await _send_generated_message(update, weekly_intelligence_report_message)
        return
    if _is_compare_query(lower):
        product_a, product_b = _parse_compare_text(question)
        if product_a and product_b:
            await _send_generated_message(update, compare_message, product_a, product_b)
            return
    await _start_analysis(update, context, question)


async def _start_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    if ANALYZE_LOCK.locked():
        await update.effective_message.reply_text("Aku masih menyelesaikan analisis sebelumnya. Tunggu sebentar ya.")
        return

    await update.effective_message.reply_text("Sebentar, aku cek konteks pasar yang relevan dulu.")
    context.application.create_task(_run_analysis_and_notify(context, chat.id, question))


async def _send_generated_message(update: Update, func, *args) -> None:
    result = await asyncio.to_thread(func, *args)
    for chunk in split_long_message(result):
        await update.effective_message.reply_text(chunk)


def _is_daily_trend_query(lowered: str) -> bool:
    return (
        "trend hari ini" in lowered
        or "hype hari ini" in lowered
        or ("produk" in lowered and "hari ini" in lowered and "hype" in lowered)
    )


def _is_weekly_query(lowered: str) -> bool:
    return "minggu ini" in lowered or "laporan mingguan" in lowered or "weekly" in lowered


def _is_compare_query(lowered: str) -> bool:
    return "bandingkan" in lowered or "compare" in lowered or " vs " in lowered


def _parse_compare_text(text: str) -> tuple[str | None, str | None]:
    cleaned = text.strip()
    lowered = cleaned.lower()
    for prefix in ["bandingkan ", "compare "]:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            lowered = cleaned.lower()
            break
    if "|" in cleaned:
        left, right = cleaned.split("|", 1)
        return left.strip() or None, right.strip() or None
    for separator in [" vs ", " versus ", " dibandingkan ", " dibanding "]:
        if separator in lowered:
            index = lowered.index(separator)
            left = cleaned[:index]
            right = cleaned[index + len(separator):]
            return left.strip() or None, right.strip() or None
    return None, None
