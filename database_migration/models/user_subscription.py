from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("channel", "channel_chat_id", name="uq_user_subscriptions_channel_chat"),
        Index("ix_user_subscriptions_user_id", "user_id"),
        Index("ix_user_subscriptions_is_active", "is_active"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    channel_chat_id: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_products: Mapped[Optional[str]] = mapped_column(Text)
    subscribed_locations: Mapped[Optional[str]] = mapped_column(Text)
    minimum_urgency: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
    scheduled_brief_times_json: Mapped[Optional[list]] = mapped_column(JSONB)
