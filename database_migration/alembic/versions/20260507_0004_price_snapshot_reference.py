"""add price snapshot reference fields

Revision ID: 20260507_0004
Revises: 20260507_0003
Create Date: 2026-05-07 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507_0004"
down_revision: Union[str, None] = "20260507_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("product_price_snapshots", sa.Column("reference_label", sa.String(length=255), nullable=True))
    op.add_column("product_price_snapshots", sa.Column("reference_url", sa.Text(), nullable=True))
    op.add_column("product_price_snapshots", sa.Column("capture_method", sa.String(length=50), nullable=True))
    op.add_column("product_price_snapshots", sa.Column("raw_price_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("product_price_snapshots", "raw_price_text")
    op.drop_column("product_price_snapshots", "capture_method")
    op.drop_column("product_price_snapshots", "reference_url")
    op.drop_column("product_price_snapshots", "reference_label")
