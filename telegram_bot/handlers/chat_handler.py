"""Telegram free-text chat handler with human-in-the-loop feedback loop.

Normal flow
-----------
User sends a business question
  -> ChatEngine crawls + composes an answer
  -> Bot sends the answer and caches it in ``_session``

Feedback flow (training the bot through chat)
---------------------------------------------
User sends a correction (e.g. "terlalu panjang, sederhanakan")
  OR replies directly to the bot's previous message
  -> Bot detects this as feedback
  -> Re-runs the composer with the feedback injected as an override instruction
     (no new crawl – uses stored evidence)
  -> Sends the improved answer
  -> Persists the (question, old answer, feedback, new answer) tuple to DB
     so future questions benefit from few-shot examples of good/bad style

The session cache (``_session``) is in-process memory only and resets on
restart.  It only needs to survive the immediate feedback round-trip, so
persistence is not required here.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from chat_engine import ChatEngine
from chat_engine.schemas import UserContext
from telegram_bot.services.feedback_service import (
    FeedbackExample,
    get_few_shot_examples,
    is_feedback_message,
    save_feedback,
)
from telegram_bot.services.memory_service import (
    ChatMemoryPreferences,
    extract_business_facts,
    extract_style_instruction,
    get_chat_memory,
    save_business_facts,
    save_response_style,
)
from telegram_bot.services.personal_brief_service import build_personalized_brief
from telegram_bot.services.reminder_service import parse_reminder_request, save_reminder
from telegram_bot.services.telegram_service import is_admin_chat, reject_if_not_allowed, split_long_message

logger = logging.getLogger(__name__)

_chat_locks: dict[str, asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# Per-chat session cache (in-process, resets on restart)
# ---------------------------------------------------------------------------

@dataclass
class _SessionEntry:
    question: str
    answer: str
    intent: str | None
    timestamp: datetime


# chat_id (str) -> most recent bot answer
_session: dict[str, _SessionEntry] = {}

_SESSION_TTL_SECONDS = 1800  # 30 minutes – after that, treat as new question


def _lock_for(chat_id: str) -> asyncio.Lock:
    lock = _chat_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[chat_id] = lock
    return lock


def _get_session(chat_id: str) -> _SessionEntry | None:
    entry = _session.get(chat_id)
    if entry is None:
        return None
    age = (datetime.now(timezone.utc) - entry.timestamp).total_seconds()
    if age > _SESSION_TTL_SECONDS:
        _session.pop(chat_id, None)
        return None
    return entry


def _set_session(chat_id: str, question: str, answer: str, intent: str | None) -> None:
    _session[chat_id] = _SessionEntry(
        question=question,
        answer=answer,
        intent=intent,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Main handler (entry point registered in telegram_bot/main.py)
# ---------------------------------------------------------------------------

async def free_text_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    message = update.effective_message
    if not message or not message.text:
        return

    question = message.text.strip()
    if len(question) < 4:
        await message.reply_text("Tulis sedikit lebih lengkap ya. Contoh: margin kopi saya aman nggak?")
        return

    chat = update.effective_chat
    if chat is None:
        return

    # ---------- style instruction override (e.g. "ingat gaya: singkat") ----------
    style_instruction = extract_style_instruction(question)
    if style_instruction:
        username = update.effective_user.username if update.effective_user else None
        try:
            saved = await asyncio.to_thread(save_response_style, chat.id, username, style_instruction)
        except Exception as exc:
            await message.reply_text(str(exc))
            return
        await message.reply_text(f"Siap, aku ingat gaya jawaban ini:\n{saved}")
        return

    username = update.effective_user.username if update.effective_user else None
    chat_id_str = str(chat.id)

    # ---------- fast assistant utilities ----------
    reminder_request = parse_reminder_request(question)
    if reminder_request is not None:
        try:
            ack = await asyncio.to_thread(save_reminder, chat.id, username, reminder_request)
        except Exception as exc:
            await message.reply_text(str(exc))
            return
        await message.reply_text(ack)
        return

    if _is_personal_brief_request(question):
        answer = await asyncio.to_thread(build_personalized_brief, chat.id)
        await message.reply_text(answer)
        return

    if _is_light_greeting(question):
        memory = await asyncio.to_thread(get_chat_memory, chat.id)
        await message.reply_text(_greeting_response(memory))
        return

    profile_memory = None
    profile_facts = {}
    if _looks_like_user_profile_statement(question):
        profile_facts = extract_business_facts(question)
        if profile_facts:
            try:
                profile_memory = await asyncio.to_thread(save_business_facts, chat.id, username, profile_facts)
            except Exception as exc:
                if _is_profile_only_message(question):
                    await message.reply_text(str(exc))
                    return
                logger.warning("Failed saving business profile for chat %s: %s", chat.id, exc)
            if profile_memory is not None and _is_profile_only_message(question):
                await message.reply_text(_profile_saved_response(profile_memory))
                return

    # ---------- detect if this is feedback on the previous answer ----------
    replied_to_bot = _is_reply_to_bot(update)
    last = _get_session(chat_id_str)
    lock = _lock_for(chat_id_str)

    if last is not None and is_feedback_message(question, replied_to_bot=replied_to_bot):
        if lock.locked():
            await message.reply_text("Aku masih menyelesaikan jawaban sebelumnya. Tunggu sebentar ya.")
            return
        context.application.create_task(
            _run_feedback_and_notify(context, chat.id, question, username, last)
        )
        return

    # ---------- normal chat flow ----------
    if lock.locked():
        await message.reply_text("Aku masih menyelesaikan jawaban sebelumnya. Tunggu sebentar ya.")
        return

    context.application.create_task(
        _run_chat_and_notify(context, chat.id, question, username)
    )


_LIGHT_GREETINGS = {
    "halo",
    "halo sorota",
    "hai",
    "hai sorota",
    "hi",
    "pagi",
    "siang",
    "sore",
    "malam",
    "assalamualaikum",
    "salam",
}
_BRIEF_TERMS = {
    "brief",
    "daily brief",
    "ringkasan hari ini",
    "rencana hari ini",
    "prioritas hari ini",
    "agenda hari ini",
}
_PROFILE_ANCHORS = {
    "saya",
    "aku",
    "kami",
    "bisnis saya",
    "usaha saya",
    "warung saya",
    "toko saya",
    "supplier saya",
    "target margin saya",
}
_PROFILE_HINTS = {
    "jual",
    "jualan",
    "menjual",
    "produk utama",
    "menu utama",
    "target margin",
    "supplier",
    "pemasok",
    "lokasi",
    "domisili",
    "usaha",
    "bisnis",
}
_ACTION_HINTS = {
    "aman",
    "berapa",
    "gimana",
    "bagaimana",
    "hitung",
    "cek",
    "analisis",
    "rekomendasi",
    "saran",
    "mending",
    "boleh",
    "profit",
    "untung",
    "rugi",
}
_MONEY_RE = re.compile(r"(?:rp\.?\s*)?\d[\d.]{2,}(?:,\d+)?", re.IGNORECASE)


def _is_light_greeting(text: str) -> bool:
    normalized = " ".join(text.lower().strip(" .,!?\n\t").split())
    return len(normalized) <= 24 and normalized in _LIGHT_GREETINGS


def _is_personal_brief_request(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _BRIEF_TERMS)


def _looks_like_user_profile_statement(text: str) -> bool:
    lowered = text.lower()
    return any(anchor in lowered for anchor in _PROFILE_ANCHORS) and any(
        hint in lowered for hint in _PROFILE_HINTS
    )


def _is_profile_only_message(text: str) -> bool:
    lowered = text.lower()
    if "?" in text:
        return False
    return not any(hint in lowered for hint in _ACTION_HINTS)


def _looks_like_fast_local_query(text: str) -> bool:
    lowered = text.lower()
    has_business_math = any(term in lowered for term in ["hpp", "modal", "margin", "untung", "jual"])
    return has_business_math and len(_MONEY_RE.findall(lowered)) >= 2


def _greeting_response(memory: ChatMemoryPreferences | None) -> str:
    if memory and (memory.product_focus or memory.business_type or memory.business_context):
        focus = ", ".join(memory.product_focus[:2]) if memory.product_focus else memory.business_type or "bisnismu"
        return (
            "Halo, aku siap bantu. "
            f"Kita bisa cek margin {focus}, harga bahan, stok, atau bikin reminder supplier."
        )
    return (
        "Halo, aku siap bantu. Kamu bisa langsung tanya margin, HPP, harga bahan, stok, "
        "atau ceritakan dulu bisnismu biar jawabanku lebih nyambung."
    )


def _profile_saved_response(memory: ChatMemoryPreferences) -> str:
    parts = []
    if memory.business_type:
        parts.append(f"jenis usaha {memory.business_type}")
    if memory.location:
        parts.append(f"lokasi {memory.location}")
    if memory.product_focus:
        parts.append("produk " + ", ".join(memory.product_focus[:3]))
    if memory.target_margin_percent is not None:
        parts.append(f"target margin {memory.target_margin_percent}%")
    if memory.known_supplier:
        parts.append(f"supplier {memory.known_supplier}")
    detail = "; ".join(parts) if parts else "konteks bisnismu"
    return f"Siap, aku catat {detail}. Jawaban berikutnya akan aku sesuaikan dengan konteks itu."


# ---------------------------------------------------------------------------
# Normal answer task
# ---------------------------------------------------------------------------

_PRICE_KEYWORDS = {
    "harga",
    "berapa",
    "price",
    "mahal",
    "murah",
    "kisaran",
    "bandrol",
    "tarif",
    "hpp",
    "margin",
    "jual",
    "modal",
    "untung",
}


def _looks_like_price_query(text: str) -> bool:
    words = set(text.lower().split())
    return bool(words & _PRICE_KEYWORDS)


def _progress_message(question: str, *, is_admin: bool) -> str:
    if _looks_like_price_query(question):
        return "Sebentar, aku cek pembanding harga dan hitung konteksnya dulu."
    if is_admin:
        return "Sebentar, aku cek bahan terbaru yang relevan dulu."
    return "Sebentar, aku susun jawaban bisnisnya dulu."


async def _run_chat_and_notify(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    question: str,
    username: str | None,
) -> None:
    chat_id_str = str(chat_id)
    # Admin boleh trigger crawl otomatis kalau DB kosong.
    # User biasa selalu DB-first, tidak pernah auto-crawl ke internet.
    is_admin = is_admin_chat(chat_id)

    try:
        if not _looks_like_fast_local_query(question):
            await context.bot.send_message(
                chat_id=chat_id,
                text=_progress_message(question, is_admin=is_admin),
            )

        async with _lock_for(chat_id_str):
            memory = await asyncio.to_thread(get_chat_memory, chat_id)
            few_shot: list[FeedbackExample] = await asyncio.to_thread(
                get_few_shot_examples, chat_id
            )
            user_context = UserContext(
                chat_id=chat_id_str,
                username=username,
                business_type=memory.business_type if memory else None,
                location=memory.location if memory else None,
                product_focus=memory.product_focus if memory and memory.product_focus else [],
                style_instructions=memory.response_style_notes if memory else None,
                business_context=memory.business_context if memory else None,
                risk_preference=memory.risk_preference if memory else None,
            )
            engine = ChatEngine()
            # Patch the composer to pass few_shot_examples (via closure)
            original_compose = engine.composer.compose

            def _compose_with_examples(**kwargs):  # type: ignore[override]
                kwargs.setdefault("few_shot_examples", few_shot)
                return original_compose(**kwargs)

            engine.composer.compose = _compose_with_examples  # type: ignore[method-assign]

            result = await asyncio.to_thread(
                engine.handle_message,
                question,
                user_context=user_context,
                # Admin: crawl_first=True → boleh crawl kalau DB kosong
                # User : crawl_first=False → DB only, cepat
                crawl_first=is_admin,
                max_sources=5,
                max_articles_per_source=2,
            )

        _set_session(
            chat_id_str,
            question,
            result.answer,
            result.plan.intent if result.plan else None,
        )
        for chunk in split_long_message(result.answer):
            await context.bot.send_message(chat_id=chat_id, text=chunk)

    except Exception as exc:
        logger.exception("ChatEngine error for chat %s", chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Maaf, jawabannya belum berhasil aku proses. Coba ulang sebentar lagi ya.",
        )


# ---------------------------------------------------------------------------
# Feedback / re-generation task
# ---------------------------------------------------------------------------

async def _run_feedback_and_notify(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    feedback_text: str,
    username: str | None,
    last: _SessionEntry,
) -> None:
    chat_id_str = str(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Oke, aku rapikan jawabannya sesuai masukanmu.",
    )
    try:
        async with _lock_for(chat_id_str):
            memory = await asyncio.to_thread(get_chat_memory, chat_id)
            few_shot: list[FeedbackExample] = await asyncio.to_thread(
                get_few_shot_examples, chat_id
            )
            # Inject feedback as an override style instruction
            base_style = memory.response_style_notes if memory else None
            feedback_style = (
                f"{base_style}\n[Koreksi saat ini]: {feedback_text}"
                if base_style
                else f"[Koreksi saat ini]: {feedback_text}"
            )
            user_context = UserContext(
                chat_id=chat_id_str,
                username=username,
                business_type=memory.business_type if memory else None,
                location=memory.location if memory else None,
                product_focus=memory.product_focus if memory and memory.product_focus else [],
                style_instructions=feedback_style,
                business_context=memory.business_context if memory else None,
                risk_preference=memory.risk_preference if memory else None,
                feedback_instruction=feedback_text,
            )
            engine = ChatEngine()
            original_compose = engine.composer.compose

            def _compose_with_examples(**kwargs):  # type: ignore[override]
                kwargs.setdefault("few_shot_examples", few_shot)
                return original_compose(**kwargs)

            engine.composer.compose = _compose_with_examples  # type: ignore[method-assign]

            # Re-run without crawl – use stored evidence
            result = await asyncio.to_thread(
                engine.handle_message,
                last.question,
                user_context=user_context,
                crawl_first=False,
            )

        improved_answer = result.answer

        # Persist feedback example for future few-shot learning
        await asyncio.to_thread(
            save_feedback,
            chat_id=chat_id_str,
            original_question=last.question,
            original_answer=last.answer,
            feedback_text=feedback_text,
            improved_answer=improved_answer,
            intent=last.intent,
        )

        # Update session with improved answer so further corrections work
        _set_session(chat_id_str, last.question, improved_answer, last.intent)

        for chunk in split_long_message(improved_answer):
            await context.bot.send_message(chat_id=chat_id, text=chunk)

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Sudah aku perbaiki dan catat.\n"
                "Jawaban berikutnya akan mengikuti preferensi itu."
            ),
        )

    except Exception as exc:
        logger.exception("Feedback re-generation error for chat %s", chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Maaf, aku belum berhasil memperbaiki jawaban itu. Coba kirim koreksinya sekali lagi.",
        )


# ---------------------------------------------------------------------------
# Telegram helper
# ---------------------------------------------------------------------------

def _is_reply_to_bot(update: Update) -> bool:
    """Return True when the user's message is a reply to a bot message."""
    message = update.effective_message
    if message is None:
        return False
    reply_to = getattr(message, "reply_to_message", None)
    if reply_to is None:
        return False
    sender = getattr(reply_to, "from_user", None)
    return bool(sender and sender.is_bot)
