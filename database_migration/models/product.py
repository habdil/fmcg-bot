from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(120))
    brand: Mapped[Optional[str]] = mapped_column(String(255))
    package_size: Mapped[Optional[str]] = mapped_column(String(80))
    unit: Mapped[Optional[str]] = mapped_column(String(40))

    price_snapshots: Mapped[List["ProductPriceSnapshot"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    availability_snapshots: Mapped[List["ProductAvailabilitySnapshot"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductPriceSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_price_snapshots"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_product_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    marketplace: Mapped[Optional[str]] = mapped_column(String(120))
    seller_name: Mapped[Optional[str]] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    stock_status: Mapped[Optional[str]] = mapped_column(String(40))
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    seller_count: Mapped[Optional[int]] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(back_populates="price_snapshots")


class ProductAvailabilitySnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_availability_snapshots"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
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
