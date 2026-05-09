"""sorota v2 reset baseline

Revision ID: 20260509_0001
Revises:
Create Date: 2026-05-09 00:00:00.000000

This revision is a reset-only baseline. The project intentionally drops old
development data before applying it, so the SQLAlchemy metadata is the source
of truth for the v2 schema.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from database_migration.models import Base

revision: str = "20260509_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
