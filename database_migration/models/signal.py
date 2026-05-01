from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, UUIDPrimaryKeyMixin, utc_now


class Signal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint("severity >= 1 AND severity <= 5", name="severity_range"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    product: Mapped[Optional[str]] = mapped_column(String(255))
    company: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    value: Mapped[Optional[str]] = mapped_column(String(255))
    severity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    related_article_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    article: Mapped["Article"] = relationship(back_populates="signals")
