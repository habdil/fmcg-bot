from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_memories"

    telegram_chat_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    response_style_notes: Mapped[Optional[str]] = mapped_column(Text)
    business_context: Mapped[Optional[str]] = mapped_column(Text)
    preferred_topics: Mapped[Optional[str]] = mapped_column(Text)
    feedback_notes: Mapped[Optional[str]] = mapped_column(Text)
