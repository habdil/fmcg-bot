"""Feedback service for human-in-the-loop few-shot learning.

Flow
----
1. User receives a bot answer and sends a correction (e.g. "terlalu panjang,
   buatkan lebih singkat").
2. chat_handler detects the message as feedback, re-generates the answer with
   the feedback injected as a style instruction, then calls
   ``save_feedback()`` to persist the example.
3. On future questions, ``get_few_shot_examples()`` fetches the most recent
   accepted examples for this chat (+ some global ones) and the composer
   injects them into the prompt so the model learns from past corrections.

No model fine-tuning is performed – this is prompt-level few-shot learning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from crawling_bot.database import session_scope
from database_migration.models.answer_feedback import AnswerFeedback

# ---------------------------------------------------------------------------
# Feedback detection
# ---------------------------------------------------------------------------

_FEEDBACK_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(r"\bperbaiki\b", re.I),
    re.compile(r"\bulang\b", re.I),
    re.compile(r"\bcoba lagi\b", re.I),
    re.compile(r"\bterlalu panjang\b", re.I),
    re.compile(r"\bterlalu pendek\b", re.I),
    re.compile(r"\bterlalu singkat\b", re.I),
    re.compile(r"\bkurang lengkap\b", re.I),
    re.compile(r"\bkurang jelas\b", re.I),
    re.compile(r"\bkurang detail\b", re.I),
    re.compile(r"\blebih singkat\b", re.I),
    re.compile(r"\blebih pendek\b", re.I),
    re.compile(r"\blebih detail\b", re.I),
    re.compile(r"\blebih lengkap\b", re.I),
    re.compile(r"\bsalah\b", re.I),
    re.compile(r"\btidak tepat\b", re.I),
    re.compile(r"\bubah formatnya\b", re.I),
    re.compile(r"\bganti formatnya\b", re.I),
    re.compile(r"\bformat berbeda\b", re.I),
    re.compile(r"\bjawabnya kurang\b", re.I),
    re.compile(r"\bjawaban kurang\b", re.I),
    re.compile(r"\bresponnya kurang\b", re.I),
    re.compile(r"\btambahin\b", re.I),
    re.compile(r"\btambahkan\b", re.I),
    re.compile(r"\bkurangin\b", re.I),
    re.compile(r"\bsederhanakan\b", re.I),
    re.compile(r"\bpersingkat\b", re.I),
    re.compile(r"\bringkaskan\b", re.I),
]

# Messages this short are almost certainly not feedback
_MIN_FEEDBACK_CHARS = 6


def is_feedback_message(text: str, *, replied_to_bot: bool = False) -> bool:
    """Return True if the message looks like feedback on the previous answer.

    A message is considered feedback when:
    - It is a Telegram reply aimed at a bot message (``replied_to_bot=True``), OR
    - It matches one of the feedback keyword patterns and is short enough to
      not be a new standalone business question (heuristic: < 180 chars).
    """
    stripped = (text or "").strip()
    if len(stripped) < _MIN_FEEDBACK_CHARS:
        return False

    if replied_to_bot:
        # Any reply to a bot message counts as potential feedback if it's not
        # clearly a new long question.
        return len(stripped) < 300

    for pattern in _FEEDBACK_KEYWORDS:
        if pattern.search(stripped):
            return True
    return False


# ---------------------------------------------------------------------------
# Data shape returned to callers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeedbackExample:
    question: str
    feedback: str
    improved_style_note: str  # A short description of what was improved


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

_SNIPPET_CHARS = 500


def save_feedback(
    *,
    chat_id: int | str,
    original_question: str,
    original_answer: str,
    feedback_text: str,
    improved_answer: str,
    intent: str | None = None,
) -> None:
    """Persist a feedback example to the database.

    Snippets are truncated to keep rows small.  The full answer is never
    stored – it's only needed at generation time.
    """
    try:
        with session_scope() as session:
            row = AnswerFeedback(
                telegram_chat_id=str(chat_id),
                original_question=original_question[:_SNIPPET_CHARS],
                original_answer_snippet=original_answer[:_SNIPPET_CHARS],
                feedback_text=feedback_text[:_SNIPPET_CHARS],
                improved_answer_snippet=improved_answer[:_SNIPPET_CHARS],
                intent=intent,
                accepted=True,
            )
            session.add(row)
    except SQLAlchemyError:
        # Non-critical – feedback logging should not break the main flow
        pass


def get_few_shot_examples(
    chat_id: int | str,
    *,
    per_chat_limit: int = 4,
    global_limit: int = 2,
) -> list[FeedbackExample]:
    """Return recent feedback examples to inject into the composer prompt.

    Fetches up to ``per_chat_limit`` rows specific to this chat and up to
    ``global_limit`` rows from other chats (global patterns).  Duplicates
    between the two sets are de-duplicated by feedback_text.
    """
    try:
        with session_scope() as session:
            chat_rows: Sequence[AnswerFeedback] = session.scalars(
                select(AnswerFeedback)
                .where(
                    AnswerFeedback.telegram_chat_id == str(chat_id),
                    AnswerFeedback.accepted.is_(True),
                )
                .order_by(desc(AnswerFeedback.created_at))
                .limit(per_chat_limit)
            ).all()

            global_rows: Sequence[AnswerFeedback] = session.scalars(
                select(AnswerFeedback)
                .where(
                    AnswerFeedback.telegram_chat_id != str(chat_id),
                    AnswerFeedback.accepted.is_(True),
                )
                .order_by(desc(AnswerFeedback.created_at))
                .limit(global_limit)
            ).all()

            seen_feedback: set[str] = set()
            examples: list[FeedbackExample] = []
            for row in list(chat_rows) + list(global_rows):
                key = row.feedback_text.lower()[:80]
                if key in seen_feedback:
                    continue
                seen_feedback.add(key)
                style_note = _derive_style_note(row.feedback_text, row.improved_answer_snippet)
                examples.append(
                    FeedbackExample(
                        question=row.original_question,
                        feedback=row.feedback_text,
                        improved_style_note=style_note,
                    )
                )
            return examples
    except SQLAlchemyError:
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_style_note(feedback: str, improved_snippet: str | None) -> str:
    """Create a short human-readable note describing the improvement."""
    fb = (feedback or "").lower()
    if any(k in fb for k in ["panjang", "singkat", "pendek", "ringkas", "persingkat"]):
        return "Jawaban dibuat lebih singkat dan padat sesuai permintaan."
    if any(k in fb for k in ["detail", "lengkap", "tambah"]):
        return "Jawaban diperlengkap dengan informasi tambahan sesuai permintaan."
    if any(k in fb for k in ["format", "struktur", "susunan"]):
        return "Format dan susunan jawaban diubah sesuai permintaan."
    if any(k in fb for k in ["salah", "tidak tepat", "koreksi"]):
        return "Jawaban dikoreksi setelah user menunjukkan kesalahan."
    if improved_snippet:
        return f"Jawaban diperbaiki: {improved_snippet[:120]}"
    return "Jawaban diperbaiki sesuai koreksi user."
