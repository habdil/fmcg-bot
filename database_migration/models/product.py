from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "market_products"
    __table_args__ = (
        Index("ix_market_products_category", "category"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(120))
    brand: Mapped[Optional[str]] = mapped_column(String(255))
    package_size: Mapped[Optional[str]] = mapped_column(String(80))
    unit: Mapped[Optional[str]] = mapped_column(String(40))
    market_scope: Mapped[str] = mapped_column(String(80), default="public_market", nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    price_snapshots: Mapped[List["ProductPriceSnapshot"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    availability_snapshots: Mapped[List["ProductAvailabilitySnapshot"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductPriceSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        Index("ix_market_prices_source_name", "source_name"),
        Index("ix_market_prices_location", "location"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_survey_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("price_surveys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_product_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    reference_label: Mapped[Optional[str]] = mapped_column(String(255))
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    capture_method: Mapped[Optional[str]] = mapped_column(String(50))
    raw_price_text: Mapped[Optional[str]] = mapped_column(Text)
    marketplace: Mapped[Optional[str]] = mapped_column(String(120))
    seller_name: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    stock_status: Mapped[Optional[str]] = mapped_column(String(40))
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    seller_count: Mapped[Optional[int]] = mapped_column(Integer)
    minimum_order_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="price_snapshots")


class ProductAvailabilitySnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "market_availability_snapshots"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    stock_status: Mapped[str] = mapped_column(String(40), nullable=False)
    available_count: Mapped[Optional[int]] = mapped_column(Integer)
    unavailable_count: Mapped[Optional[int]] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="availability_snapshots")


class PriceSurvey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "price_surveys"
    __table_args__ = (
        Index("ix_price_surveys_status", "status"),
        Index("ix_price_surveys_normalized_product_name", "normalized_product_name"),
    )

    requested_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
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
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    normalized_product_name: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    freshness_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    evidence_ids_json: Mapped[Optional[list]] = mapped_column(JSONB)

    price_snapshots: Mapped[List["ProductPriceSnapshot"]] = relationship()
    supplier_candidates: Mapped[List["SupplierCandidate"]] = relationship(
        back_populates="price_survey",
        cascade="all, delete-orphan",
    )


class SupplierCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_candidates"
    __table_args__ = (
        UniqueConstraint(
            "price_survey_id",
            "supplier_name",
            "reference_url",
            name="uq_supplier_candidates_survey_supplier_url",
        ),
    )

    price_survey_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("price_surveys.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("market_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    offered_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    minimum_order_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    price_survey: Mapped[Optional["PriceSurvey"]] = relationship(back_populates="supplier_candidates")
