from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, UUIDPrimaryKeyMixin, utc_now


class CrawlLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "crawl_runs"
    __table_args__ = (
        Index("ix_crawl_runs_status", "status"),
        Index("ix_crawl_runs_started_at", "started_at"),
    )

    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), default="news_crawl", nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    request_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    total_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    source: Mapped[Optional["Source"]] = relationship(back_populates="crawl_logs")
