from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_status", "status"),
    )

    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    primary_channel: Mapped[str] = mapped_column(String(40), default="telegram", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="id", nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Jakarta", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)

    channel_accounts: Mapped[List["UserChannelAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserChannelAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_channel_accounts"
    __table_args__ = (
        UniqueConstraint("channel", "channel_user_id", name="uq_user_channel_accounts_channel_user"),
        Index("ix_user_channel_accounts_channel", "channel"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    channel_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="channel_accounts")
