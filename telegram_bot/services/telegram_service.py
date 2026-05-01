from __future__ import annotations

from html import escape
from typing import Any

from telegram import Update

from crawling_bot.config import settings


def is_allowed_chat(chat_id: int | str | None) -> bool:
    if chat_id is None:
        return False
    allowed = settings.allowed_chat_ids
    return not allowed or str(chat_id) in allowed


async def reject_if_not_allowed(update: Update) -> bool:
    chat = update.effective_chat
    if chat and is_allowed_chat(chat.id):
        return False
    if update.effective_message:
        await update.effective_message.reply_text("Chat ini belum diizinkan untuk memakai bot.")
    return True


def format_alert(row: dict[str, Any]) -> str:
    product = row.get("product") or "-"
    reason = row.get("reason") or "Direct cause is not clearly stated in the article."
    evidence = row.get("evidence_text") or "-"
    impact = row.get("explanation") or "Monitor this signal before making operational decisions."
    summary = row.get("ai_polished_summary") or "-"
    source = f"{row.get('source_name')} - {row.get('title')}"
    return (
        "<b>FMCG Business Alert</b>\n\n"
        f"Product: {escape(product)}\n"
        f"Urgency: {escape(str(row.get('urgency', '-')).upper())}\n"
        f"Signal: {escape(str(row.get('signal_type', '-')))}\n\n"
        f"<b>Reason</b>\n{escape(reason)}\n\n"
        f"<b>Evidence</b>\n{escape(evidence)}\n\n"
        f"<b>Business Impact</b>\n{escape(impact)}\n\n"
        f"<b>Sources</b>\n1. {escape(source)}\n{escape(str(row.get('article_url')))}\n\n"
        f"<b>Generated Summary</b>\n{escape(summary)}"
    )


def format_compact_row(row: dict[str, Any]) -> str:
    product = row.get("product") or row.get("company") or row.get("location") or "-"
    return (
        f"- {row.get('signal_type')} | {product} | "
        f"{str(row.get('urgency', '-')).upper()} | {row.get('source_name')}"
    )


def split_long_message(message: str, max_length: int = 3900) -> list[str]:
    if len(message) <= max_length:
        return [message]

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for line in message.splitlines():
        line_length = len(line) + 1
        if current and current_length + line_length > max_length:
            chunks.append("\n".join(current))
            current = []
            current_length = 0
        current.append(line)
        current_length += line_length

    if current:
        chunks.append("\n".join(current))
    return chunks
