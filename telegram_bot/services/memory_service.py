from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from crawling_bot.database import session_scope
from database_migration.models.chat_memory import ChatMemory


MAX_STYLE_CHARS = 800


@dataclass(frozen=True)
class ChatMemoryPreferences:
    response_style_notes: str | None = None
    business_context: str | None = None
    preferred_topics: str | None = None
    feedback_notes: str | None = None


STYLE_PATTERNS = [
    re.compile(
        r"^(?:ingat|simpan|catat)\s+(?:gaya|style|preferensi)(?:\s+jawaban)?\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:atur|set)\s+(?:gaya|style|preferensi)(?:\s+jawaban)?\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:mulai sekarang|kedepannya|ke depannya)\s+(?:jawab|respon|balas)\s+(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:saya|aku)\s+mau\s+(?:jawaban|respon|balasan)(?:nya)?\s+(.+)$",
        re.IGNORECASE,
    ),
]


def extract_style_instruction(message: str) -> str | None:
    normalized = " ".join((message or "").strip().split())
    if not normalized:
        return None
    for pattern in STYLE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return _clean_style_notes(match.group(1))
    return None


def get_chat_memory(chat_id: int | str) -> ChatMemoryPreferences | None:
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(ChatMemory).where(ChatMemory.telegram_chat_id == str(chat_id))
            )
            if memory is None:
                return None
            return ChatMemoryPreferences(
                response_style_notes=memory.response_style_notes,
                business_context=memory.business_context,
                preferred_topics=memory.preferred_topics,
                feedback_notes=memory.feedback_notes,
            )
    except SQLAlchemyError:
        return None


def save_response_style(chat_id: int | str, username: str | None, notes: str) -> str:
    cleaned = _clean_style_notes(notes)
    if not cleaned:
        raise ValueError("Instruksi gaya jawaban kosong.")
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(ChatMemory).where(ChatMemory.telegram_chat_id == str(chat_id))
            )
            if memory is None:
                memory = ChatMemory(telegram_chat_id=str(chat_id))
                session.add(memory)
            memory.username = username
            memory.response_style_notes = cleaned
        return cleaned
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory belum aktif. Jalankan migrasi database dulu.") from exc


def clear_response_style(chat_id: int | str) -> None:
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(ChatMemory).where(ChatMemory.telegram_chat_id == str(chat_id))
            )
            if memory is not None:
                memory.response_style_notes = None
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory belum aktif. Jalankan migrasi database dulu.") from exc


def _clean_style_notes(value: str) -> str:
    return " ".join(value.strip().split())[:MAX_STYLE_CHARS]
