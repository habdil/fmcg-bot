from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_subscriptions"

    telegram_chat_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_products: Mapped[Optional[str]] = mapped_column(Text)
    subscribed_locations: Mapped[Optional[str]] = mapped_column(Text)
    minimum_urgency: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
