from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, UUIDPrimaryKeyMixin, utc_now


class Entity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "market_entities"
    __table_args__ = (
        UniqueConstraint("normalized_name", "entity_type", name="uq_market_entities_normalized_type"),
        Index("ix_market_entities_entity_type", "entity_type"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    article_entities: Mapped[List["ArticleEntity"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )


class ArticleEntity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_entities"
    __table_args__ = (
        UniqueConstraint("article_id", "entity_id", name="uq_document_entities_article_entity"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crawled_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    article: Mapped["Article"] = relationship(back_populates="article_entities")
    entity: Mapped["Entity"] = relationship(back_populates="article_entities")
