from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from crawling_bot.processors.entity_extractor import flatten_entities
from crawling_bot.schemas.article_schema import ProcessedArticle
from crawling_bot.schemas.entity_schema import EntityItem
from crawling_bot.schemas.signal_schema import ExtractedSignal
from database_migration.models.article import Article
from database_migration.models.entity import ArticleEntity, Entity
from database_migration.models.signal import Signal
from database_migration.models.source import Source


def article_url_exists(session: Session, url: str) -> bool:
    return session.scalar(select(Article.id).where(Article.url == url)) is not None


def content_hash_exists(session: Session, content_hash: str) -> bool:
    return session.scalar(select(Article.id).where(Article.content_hash == content_hash)) is not None


def _get_or_create_entity(session: Session, item: EntityItem) -> Entity:
    entity = session.scalar(
        select(Entity).where(
            Entity.normalized_name == item.normalized_name,
            Entity.entity_type == item.entity_type,
        )
    )
    if entity is None:
        entity = Entity(
            name=item.name,
            entity_type=item.entity_type,
            normalized_name=item.normalized_name,
        )
        session.add(entity)
        session.flush()
    return entity


def save_processed_article(
    session: Session,
    *,
    source: Source,
    article_data: ProcessedArticle,
    entities: dict[str, list[EntityItem]],
    signals: list[ExtractedSignal],
) -> Article:
    article = Article(
        source_id=source.id,
        title=article_data.title,
        url=article_data.url,
        raw_content=article_data.raw_content,
        clean_content=article_data.clean_content,
        summary=article_data.summary,
        reason=article_data.reason,
        evidence_text=article_data.evidence_text,
        ai_polished_summary=article_data.ai_polished_summary,
        published_at=article_data.published_at,
        language=article_data.language,
        category=article_data.category,
        relevance_score=article_data.relevance_score,
        impact_score=article_data.impact_score,
        confidence_score=article_data.confidence_score,
        urgency=article_data.urgency,
        content_hash=article_data.content_hash,
    )
    session.add(article)
    session.flush()

    for item in flatten_entities(entities):
        entity = _get_or_create_entity(session, item)
        session.add(
            ArticleEntity(
                article_id=article.id,
                entity_id=entity.id,
                relevance_score=item.relevance_score,
            )
        )

    for signal in signals:
        session.add(
            Signal(
                article_id=article.id,
                signal_type=signal.signal_type,
                product=signal.product,
                company=signal.company,
                location=signal.location,
                value=signal.value,
                severity=signal.severity,
                confidence_score=signal.confidence_score,
                reason=signal.reason,
                evidence_text=signal.evidence_text,
                explanation=signal.explanation,
                source_count=signal.source_count,
                related_article_count=signal.related_article_count,
            )
        )

    session.flush()
    return article
