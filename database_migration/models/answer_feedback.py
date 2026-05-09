from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnswerFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores user feedback on bot answers for few-shot learning.

    Each row captures: what was asked, what the bot said, what the user
    found wrong, and what the improved answer looked like.  These rows
    are later injected as few-shot examples into the composer prompt so
    the bot learns from past corrections without fine-tuning the model.
    """

    __tablename__ = "answer_feedback"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(128), nullable=False)
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    # Snippet only – we never store full answers to keep rows small
    original_answer_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    improved_answer_snippet: Mapped[Optional[str]] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(64))
    # False means the improved answer was also rejected (rare, for audit)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_answer_feedback_chat_id", "telegram_chat_id"),
        Index("ix_answer_feedback_intent", "intent"),
    )
