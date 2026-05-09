from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_migration.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Business(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_businesses_owner_user_id", "owner_user_id"),
        Index("ix_businesses_business_type", "business_type"),
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[Optional[str]] = mapped_column(String(255))
    business_type: Mapped[Optional[str]] = mapped_column(String(80))
    business_scale: Mapped[Optional[str]] = mapped_column(String(80))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    province: Mapped[Optional[str]] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="Indonesia", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)

    profile: Mapped[Optional["BusinessProfile"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        uselist=False,
    )
    products: Mapped[List["BusinessProduct"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )
    suppliers: Mapped[List["Supplier"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )


class BusinessProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_profiles"

    business_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    target_margin_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    pricing_preference: Mapped[Optional[str]] = mapped_column(Text)
    risk_preference: Mapped[Optional[str]] = mapped_column(String(40))
    response_style: Mapped[Optional[str]] = mapped_column(String(40))
    main_products_json: Mapped[Optional[list]] = mapped_column(JSONB)
    profile_data_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    business: Mapped["Business"] = relationship(back_populates="profile")


class BusinessProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_products"
    __table_args__ = (
        UniqueConstraint("business_id", "normalized_name", name="uq_business_products_business_normalized"),
        Index("ix_business_products_category", "category"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(120))
    brand: Mapped[Optional[str]] = mapped_column(String(255))
    package_size: Mapped[Optional[str]] = mapped_column(String(80))
    unit: Mapped[Optional[str]] = mapped_column(String(40))
    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    target_margin_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    business: Mapped["Business"] = relationship(back_populates="products")
    costs: Mapped[List["ProductCost"]] = relationship(
        back_populates="business_product",
        cascade="all, delete-orphan",
    )


class ProductCost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_costs"

    business_product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("business_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cost_type: Mapped[str] = mapped_column(String(80), default="hpp", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="IDR", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    business_product: Mapped["BusinessProduct"] = relationship(back_populates="costs")


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("ix_suppliers_business_id", "business_id"),
        Index("ix_suppliers_location", "location"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    product_focus_json: Mapped[Optional[list]] = mapped_column(JSONB)
    reliability_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="suppliers")
