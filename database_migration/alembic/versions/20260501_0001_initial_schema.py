"""initial schema

Revision ID: 20260501_0001
Revises:
Create Date: 2026-05-01 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260501_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("credibility_score", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )
    op.create_table(
        "entities",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
        sa.UniqueConstraint("normalized_name", "entity_type", name="uq_entities_normalized_type"),
    )
    op.create_table(
        "user_subscriptions",
        sa.Column("telegram_chat_id", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("subscribed_products", sa.Text(), nullable=True),
        sa.Column("subscribed_locations", sa.Text(), nullable=True),
        sa.Column("minimum_urgency", sa.String(length=20), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_subscriptions")),
        sa.UniqueConstraint("telegram_chat_id", name=op.f("uq_user_subscriptions_telegram_chat_id")),
    )
    op.create_table(
        "articles",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("clean_content", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("ai_polished_summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("impact_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("urgency", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_articles_source_id_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("content_hash", name=op.f("uq_articles_content_hash")),
        sa.UniqueConstraint("url", name=op.f("uq_articles_url")),
    )
    op.create_index(op.f("ix_articles_source_id"), "articles", ["source_id"], unique=False)
    op.create_table(
        "crawl_logs",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("total_found", sa.Integer(), nullable=False),
        sa.Column("total_crawled", sa.Integer(), nullable=False),
        sa.Column("total_processed", sa.Integer(), nullable=False),
        sa.Column("total_saved", sa.Integer(), nullable=False),
        sa.Column("total_skipped", sa.Integer(), nullable=False),
        sa.Column("total_failed", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_crawl_logs_source_id_sources"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crawl_logs")),
    )
    op.create_index(op.f("ix_crawl_logs_source_id"), "crawl_logs", ["source_id"], unique=False)
    op.create_table(
        "article_entities",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("fk_article_entities_article_id_articles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], name=op.f("fk_article_entities_entity_id_entities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_article_entities")),
        sa.UniqueConstraint("article_id", "entity_id", name="uq_article_entities_article_entity"),
    )
    op.create_index(op.f("ix_article_entities_article_id"), "article_entities", ["article_id"], unique=False)
    op.create_index(op.f("ix_article_entities_entity_id"), "article_entities", ["entity_id"], unique=False)
    op.create_table(
        "signals",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(length=80), nullable=False),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("related_article_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("severity >= 1 AND severity <= 5", name=op.f("ck_signals_severity_range")),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("fk_signals_article_id_articles"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signals")),
    )
    op.create_index(op.f("ix_signals_article_id"), "signals", ["article_id"], unique=False)
    op.create_index(op.f("ix_signals_signal_type"), "signals", ["signal_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_signals_signal_type"), table_name="signals")
    op.drop_index(op.f("ix_signals_article_id"), table_name="signals")
    op.drop_table("signals")
    op.drop_index(op.f("ix_article_entities_entity_id"), table_name="article_entities")
    op.drop_index(op.f("ix_article_entities_article_id"), table_name="article_entities")
    op.drop_table("article_entities")
    op.drop_index(op.f("ix_crawl_logs_source_id"), table_name="crawl_logs")
    op.drop_table("crawl_logs")
    op.drop_index(op.f("ix_articles_source_id"), table_name="articles")
    op.drop_table("articles")
    op.drop_table("user_subscriptions")
    op.drop_table("entities")
    op.drop_table("sources")
