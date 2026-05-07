"""add chat memory table

Revision ID: 20260507_0003
Revises: 20260501_0002
Create Date: 2026-05-07 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_0003"
down_revision: Union[str, None] = "20260501_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_memories",
        sa.Column("telegram_chat_id", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("response_style_notes", sa.Text(), nullable=True),
        sa.Column("business_context", sa.Text(), nullable=True),
        sa.Column("preferred_topics", sa.Text(), nullable=True),
        sa.Column("feedback_notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_memories")),
        sa.UniqueConstraint("telegram_chat_id", name=op.f("uq_chat_memories_telegram_chat_id")),
    )


def downgrade() -> None:
    op.drop_table("chat_memories")
