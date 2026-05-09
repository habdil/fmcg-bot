from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from database_migration.models.source import Source


def list_active_sources(session: Session, limit: int | None = None) -> list[Source]:
    statement = (
        select(Source)
        .where(Source.is_active.is_(True))
        .order_by(desc(Source.credibility_score), Source.name.asc())
    )
    if limit:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def upsert_source(
    session: Session,
    *,
    name: str,
    url: str,
    source_type: str = "rss",
    source_category: str = "market_intelligence",
    credibility_score: float = 0.5,
    is_active: bool = True,
    notes: str | None = None,
    config_json: dict[str, Any] | None = None,
) -> Source:
    source = session.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name, url=url, source_type=source_type)
        session.add(source)
    source.url = url
    source.source_type = source_type
    source.source_category = source_category
    source.credibility_score = credibility_score
    source.is_active = is_active
    source.notes = notes
    source.config_json = config_json
    return source
