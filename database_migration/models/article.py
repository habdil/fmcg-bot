from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Article(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crawled_documents"
    __table_args__ = (
        Index("ix_crawled_documents_published_at", "published_at"),
        Index("ix_crawled_documents_crawled_at", "crawled_at"),
        Index("ix_crawled_documents_category", "category"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), default="article", nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    raw_content: Mapped[Optional[str]] = mapped_column(Text)
    clean_content: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    evidence_text: Mapped[Optional[str]] = mapped_column(Text)
    ai_polished_summary: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String(10), default="id", nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    relevance_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    source: Mapped["Source"] = relationship(back_populates="articles")
    article_entities: Mapped[List["ArticleEntity"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    signals: Mapped[List["Signal"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
