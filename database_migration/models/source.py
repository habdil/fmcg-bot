from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Boolean, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_sources"
    __table_args__ = (
        Index("ix_market_sources_source_type", "source_type"),
        Index("ix_market_sources_is_active", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_category: Mapped[str] = mapped_column(String(80), default="market_intelligence", nullable=False)
    credibility_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    config_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    articles: Mapped[List["Article"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )
    crawl_logs: Mapped[List["CrawlLog"]] = relationship(back_populates="source")
