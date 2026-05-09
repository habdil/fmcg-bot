from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_requests"
    __table_args__ = (
        Index("ix_ai_requests_task_name", "task_name"),
        Index("ix_ai_requests_provider_model", "provider", "model"),
        Index("ix_ai_requests_status", "status"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chat_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(80))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    request_metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
