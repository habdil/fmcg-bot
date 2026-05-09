from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_channel_chat_id", "channel_chat_id"),
        Index("ix_chat_sessions_status", "status"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    channel_chat_id: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class ChatMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_channel_chat_id", "channel_chat_id"),
        Index("ix_chat_messages_created_at", "created_at"),
        Index("ix_chat_messages_normalized_intent", "normalized_intent"),
    )

    chat_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    channel_chat_id: Mapped[Optional[str]] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_intent: Mapped[Optional[str]] = mapped_column(String(80))
    entities_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    evidence_ids_json: Mapped[Optional[list]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_memories"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "channel_user_id",
            "memory_type",
            "memory_key",
            name="uq_user_memories_channel_key",
        ),
        Index("ix_user_memories_user_id", "user_id"),
        Index("ix_user_memories_memory_type", "memory_type"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    channel_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    memory_type: Mapped[str] = mapped_column(String(80), nullable=False)
    memory_key: Mapped[str] = mapped_column(String(120), nullable=False)
    memory_text: Mapped[Optional[str]] = mapped_column(Text)
    memory_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    source: Mapped[Optional[str]] = mapped_column(String(80))
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_user_id", "user_id"),
        Index("ix_recommendations_intent", "intent"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    business_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
    )
    chat_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    intent: Mapped[Optional[str]] = mapped_column(String(80))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_items_json: Mapped[Optional[list]] = mapped_column(JSONB)
    basis_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)


class ScheduledBriefRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scheduled_brief_runs"
    __table_args__ = (
        UniqueConstraint("brief_key", name="uq_scheduled_brief_runs_brief_key"),
        Index("ix_scheduled_brief_runs_status", "status"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    channel_chat_id: Mapped[str] = mapped_column(String(128), nullable=False)
    brief_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_slot: Mapped[str] = mapped_column(String(20), nullable=False)
    brief_key: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    message_text: Mapped[Optional[str]] = mapped_column(Text)
    evidence_ids_json: Mapped[Optional[list]] = mapped_column(JSONB)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)


# Compatibility alias for old imports while services are migrated.
ChatMemory = UserMemory
