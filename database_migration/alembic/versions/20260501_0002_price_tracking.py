"""add product price tracking tables

Revision ID: 20260501_0002
Revises: 20260501_0001
Create Date: 2026-05-01 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260501_0002"
down_revision: Union[str, None] = "20260501_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("package_size", sa.String(length=80), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("normalized_name", name=op.f("uq_products_normalized_name")),
    )
    op.create_index(op.f("ix_products_normalized_name"), "products", ["normalized_name"], unique=False)

    op.create_table(
        "product_price_snapshots",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_product_name", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("marketplace", sa.String(length=120), nullable=True),
        sa.Column("seller_name", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="IDR", nullable=False),
        sa.Column("stock_status", sa.String(length=40), nullable=True),
        sa.Column("stock_quantity", sa.Integer(), nullable=True),
        sa.Column("seller_count", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_price_snapshots_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_price_snapshots")),
    )
    op.create_index(
        op.f("ix_product_price_snapshots_normalized_product_name"),
        "product_price_snapshots",
        ["normalized_product_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_price_snapshots_observed_at"),
        "product_price_snapshots",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_price_snapshots_product_id"),
        "product_price_snapshots",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "product_availability_snapshots",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("stock_status", sa.String(length=40), nullable=False),
        sa.Column("available_count", sa.Integer(), nullable=True),
        sa.Column("unavailable_count", sa.Integer(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_availability_snapshots_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_availability_snapshots")),
    )
    op.create_index(
        op.f("ix_product_availability_snapshots_observed_at"),
        "product_availability_snapshots",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_availability_snapshots_product_id"),
        "product_availability_snapshots",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_product_availability_snapshots_product_id"), table_name="product_availability_snapshots")
    op.drop_index(op.f("ix_product_availability_snapshots_observed_at"), table_name="product_availability_snapshots")
    op.drop_table("product_availability_snapshots")
    op.drop_index(op.f("ix_product_price_snapshots_product_id"), table_name="product_price_snapshots")
    op.drop_index(op.f("ix_product_price_snapshots_observed_at"), table_name="product_price_snapshots")
    op.drop_index(op.f("ix_product_price_snapshots_normalized_product_name"), table_name="product_price_snapshots")
    op.drop_table("product_price_snapshots")
    op.drop_index(op.f("ix_products_normalized_name"), table_name="products")
    op.drop_table("products")
