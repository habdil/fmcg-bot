from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, or_, select

from crawling_bot.database import session_scope
from database_migration.models.article import Article
from database_migration.models.entity import ArticleEntity, Entity
from database_migration.models.signal import Signal
from database_migration.models.source import Source


def _signal_row(signal: Signal, article: Article, source: Source) -> dict[str, Any]:
    return {
        "signal_id": str(signal.id),
        "article_id": str(article.id),
        "signal_type": signal.signal_type,
        "product": signal.product,
        "company": signal.company,
        "location": signal.location,
        "value": signal.value,
        "severity": signal.severity,
        "confidence_score": signal.confidence_score,
        "reason": signal.reason,
        "evidence_text": signal.evidence_text,
        "explanation": signal.explanation,
        "urgency": article.urgency,
        "impact_score": article.impact_score,
        "title": article.title,
        "article_url": article.url,
        "source_name": source.name,
        "source_url": source.url,
        "published_at": article.published_at,
        "created_at": signal.created_at,
        "crawled_at": article.crawled_at,
        "ai_polished_summary": article.ai_polished_summary,
    }


def get_high_urgency_alerts(limit: int = 5) -> list[dict[str, Any]]:
    with session_scope() as session:
        statement = (
            select(Signal, Article, Source)
            .join(Article, Signal.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(or_(Article.urgency == "high", Signal.severity >= 4))
            .order_by(desc(Article.impact_score), desc(Signal.created_at))
            .limit(limit)
        )
        return [_signal_row(signal, article, source) for signal, article, source in session.execute(statement)]


def search_insights(keyword: str, limit: int = 10, period_days: int | None = None) -> list[dict[str, Any]]:
    pattern = f"%{keyword}%"
    since = datetime.now(timezone.utc) - timedelta(days=period_days) if period_days else None
    with session_scope() as session:
        filters = [
            or_(
                Article.title.ilike(pattern),
                Article.clean_content.ilike(pattern),
                Signal.product.ilike(pattern),
                Signal.company.ilike(pattern),
                Signal.location.ilike(pattern),
            )
        ]
        if since is not None:
            filters.append(or_(Signal.created_at >= since, Article.published_at >= since))
        statement = (
            select(Signal, Article, Source)
            .join(Article, Signal.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(*filters)
            .order_by(desc(Article.impact_score), desc(Signal.created_at))
            .limit(limit)
        )
        return [_signal_row(signal, article, source) for signal, article, source in session.execute(statement)]


def search_insights_for_terms(terms: list[str], limit: int = 20) -> list[dict[str, Any]]:
    cleaned_terms = [term.strip() for term in terms if term and term.strip()]
    if not cleaned_terms:
        return []

    conditions = []
    for term in cleaned_terms:
        pattern = f"%{term}%"
        conditions.extend(
            [
                Article.title.ilike(pattern),
                Article.clean_content.ilike(pattern),
                Article.reason.ilike(pattern),
                Article.evidence_text.ilike(pattern),
                Signal.product.ilike(pattern),
                Signal.company.ilike(pattern),
                Signal.location.ilike(pattern),
                Signal.evidence_text.ilike(pattern),
                Signal.reason.ilike(pattern),
            ]
        )

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    with session_scope() as session:
        statement = (
            select(Signal, Article, Source)
            .join(Article, Signal.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(or_(*conditions))
            .order_by(desc(Article.impact_score), desc(Signal.created_at))
            .limit(limit * 2)
        )
        for signal, article, source in session.execute(statement):
            key = str(signal.id)
            if key in seen:
                continue
            rows.append(_signal_row(signal, article, source))
            seen.add(key)
            if len(rows) >= limit:
                break
    return rows


def recent_signal_rows(period_days: int = 1, limit: int = 100) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    with session_scope() as session:
        statement = (
            select(Signal, Article, Source)
            .join(Article, Signal.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(or_(Signal.created_at >= since, Article.published_at >= since))
            .order_by(desc(Article.impact_score), desc(Signal.severity), desc(Signal.created_at))
            .limit(limit)
        )
        return [_signal_row(signal, article, source) for signal, article, source in session.execute(statement)]


def period_signal_rows(
    *,
    start_at: datetime,
    end_at: datetime,
    limit: int = 200,
) -> list[dict[str, Any]]:
    with session_scope() as session:
        statement = (
            select(Signal, Article, Source)
            .join(Article, Signal.article_id == Article.id)
            .join(Source, Article.source_id == Source.id)
            .where(
                or_(
                    Signal.created_at.between(start_at, end_at),
                    Article.published_at.between(start_at, end_at),
                )
            )
            .order_by(desc(Article.impact_score), desc(Signal.severity), desc(Signal.created_at))
            .limit(limit)
        )
        return [_signal_row(signal, article, source) for signal, article, source in session.execute(statement)]


def daily_report() -> dict[str, list[dict[str, Any]]]:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    groups = {
        "price": ["price_increase", "price_decrease"],
        "shortage": ["shortage", "oversupply"],
        "demand": ["demand_increase", "demand_decrease"],
        "sentiment": ["negative_sentiment", "positive_sentiment"],
    }
    report: dict[str, list[dict[str, Any]]] = {}
    with session_scope() as session:
        for name, signal_types in groups.items():
            statement = (
                select(Signal, Article, Source)
                .join(Article, Signal.article_id == Article.id)
                .join(Source, Article.source_id == Source.id)
                .where(Signal.signal_type.in_(signal_types), Signal.created_at >= since)
                .order_by(desc(Article.impact_score), desc(Signal.severity))
                .limit(5)
            )
            report[name] = [
                _signal_row(signal, article, source)
                for signal, article, source in session.execute(statement)
            ]
    return report


def trending(limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    with session_scope() as session:
        signal_count = func.count(Signal.id).label("count")
        signal_rows = session.execute(
            select(Signal.signal_type, signal_count)
            .where(Signal.created_at >= since)
            .group_by(Signal.signal_type)
            .order_by(signal_count.desc())
            .limit(limit)
        ).all()
        entity_count = func.count(ArticleEntity.id).label("count")
        entity_rows = session.execute(
            select(Entity.name, Entity.entity_type, entity_count)
            .join(ArticleEntity, ArticleEntity.entity_id == Entity.id)
            .join(Article, ArticleEntity.article_id == Article.id)
            .where(Article.created_at >= since)
            .group_by(Entity.name, Entity.entity_type)
            .order_by(entity_count.desc())
            .limit(limit)
        ).all()

    return {
        "signals": [{"signal_type": row[0], "count": row[1]} for row in signal_rows],
        "entities": [{"name": row[0], "entity_type": row[1], "count": row[2]} for row in entity_rows],
    }
