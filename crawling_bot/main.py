from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from crawling_bot.ai.gemini_polisher import GeminiPolisher
from crawling_bot.config import settings
from crawling_bot.crawlers.article_crawler import fetch_article
from crawling_bot.crawlers.rss_crawler import fetch_rss_entries
from crawling_bot.database import session_scope
from crawling_bot.processors.cleaner import fallback_summary, generate_content_hash, normalize_whitespace
from crawling_bot.processors.entity_extractor import extract_entities
from crawling_bot.processors.relevance_filter import score_relevance
from crawling_bot.processors.signal_extractor import extract_signals, infer_category
from crawling_bot.processors.scorer import confidence_score, impact_score, urgency
from crawling_bot.schemas.article_schema import ProcessedArticle
from crawling_bot.schemas.insight_schema import SourceReference
from crawling_bot.services.article_service import (
    article_url_exists,
    content_hash_exists,
    save_processed_article,
)
from crawling_bot.services.crawl_log_service import finish_log, start_log
from crawling_bot.services.source_service import list_active_sources
from database_migration.models.source import Source

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SourceStats:
    total_found: int = 0
    total_crawled: int = 0
    total_processed: int = 0
    total_saved: int = 0
    total_skipped: int = 0
    total_failed: int = 0


def _source_references(source: Source, title: str, url: str, published_at) -> list[SourceReference]:
    return [
        SourceReference(
            title=title,
            source=source.name,
            url=url,
            published_at=published_at,
        )
    ]


def process_source(source: Source, max_articles: Optional[int] = None) -> SourceStats:
    stats = SourceStats()
    with session_scope() as session:
        source = session.get(Source, source.id)
        if source is None:
            return stats
        log = start_log(session, source)

        try:
            if source.source_type != "rss":
                finish_log(log, status="skipped", message=f"Unsupported source_type: {source.source_type}")
                return stats

            entries = fetch_rss_entries(source.url, limit=max_articles or settings.max_articles_per_source)
            stats.total_found = len(entries)

            polisher = GeminiPolisher()
            for entry in entries:
                stats.total_crawled += 1
                try:
                    if article_url_exists(session, entry.url):
                        stats.total_skipped += 1
                        continue

                    detail = fetch_article(entry.url)
                    title = normalize_whitespace(entry.title or detail.title or "Untitled article")
                    clean_content = normalize_whitespace(detail.raw_text or entry.summary or "")
                    if not clean_content:
                        stats.total_skipped += 1
                        continue

                    content_hash = generate_content_hash(f"{title} {clean_content}")
                    if content_hash_exists(session, content_hash):
                        stats.total_skipped += 1
                        continue

                    relevance = score_relevance(title, clean_content)
                    if not relevance.is_relevant:
                        stats.total_skipped += 1
                        continue

                    entity_groups = extract_entities(title, clean_content)
                    signals = extract_signals(title, clean_content, entity_groups)
                    stats.total_processed += 1

                    article_reason = signals[0].reason if signals else None
                    article_evidence = signals[0].evidence_text if signals else None
                    max_severity = max((signal.severity for signal in signals), default=1)
                    impact = impact_score(
                        source_credibility_score=source.credibility_score,
                        severity=max_severity,
                        relevance_score=relevance.score,
                        published_at=detail.published_at or entry.published_at,
                    )
                    confidence = confidence_score(
                        source_credibility_score=source.credibility_score,
                        clean_content=clean_content,
                        signals=signals,
                        reason=article_reason,
                        evidence_text=article_evidence,
                    )
                    article_urgency = urgency(impact, signals)
                    references = _source_references(
                        source,
                        title,
                        detail.url or entry.url,
                        detail.published_at or entry.published_at,
                    )
                    polished = polisher.polish(
                        title=title,
                        clean_content=clean_content,
                        signals=signals,
                        reason=article_reason,
                        evidence_text=article_evidence,
                        source_references=references,
                        urgency=article_urgency,
                    )

                    article_data = ProcessedArticle(
                        title=polished.polished_title or title,
                        url=detail.url or entry.url,
                        raw_content=detail.raw_html,
                        clean_content=clean_content,
                        summary=fallback_summary(title, clean_content),
                        reason=article_reason,
                        evidence_text=article_evidence,
                        ai_polished_summary=polished.polished_summary,
                        published_at=detail.published_at or entry.published_at,
                        category=infer_category(signals),
                        relevance_score=relevance.score,
                        impact_score=impact,
                        confidence_score=confidence,
                        urgency=article_urgency,
                        content_hash=content_hash,
                    )
                    save_processed_article(
                        session,
                        source=source,
                        article_data=article_data,
                        entities=entity_groups,
                        signals=signals,
                    )
                    stats.total_saved += 1
                except Exception as exc:
                    stats.total_failed += 1
                    logger.exception("Failed processing article from %s: %s", source.name, exc)

            status = "success"
            if stats.total_failed and stats.total_saved:
                status = "partial_success"
            elif stats.total_failed and not stats.total_saved:
                status = "failed"
            finish_log(
                log,
                status=status,
                message=f"Processed {stats.total_processed} relevant articles from {source.name}.",
                total_found=stats.total_found,
                total_crawled=stats.total_crawled,
                total_processed=stats.total_processed,
                total_saved=stats.total_saved,
                total_skipped=stats.total_skipped,
                total_failed=stats.total_failed,
            )
        except Exception as exc:
            logger.exception("Failed crawling source %s: %s", source.name, exc)
            stats.total_failed += 1
            finish_log(
                log,
                status="failed",
                message=str(exc),
                total_found=stats.total_found,
                total_crawled=stats.total_crawled,
                total_processed=stats.total_processed,
                total_saved=stats.total_saved,
                total_skipped=stats.total_skipped,
                total_failed=stats.total_failed,
            )

    return stats


def run_crawler(
    max_articles_per_source: Optional[int] = None,
    source_limit: Optional[int] = None,
) -> list[SourceStats]:
    with session_scope() as session:
        sources = list_active_sources(session, limit=source_limit)

    if not sources:
        logger.warning("No active sources found. Run scripts/seed_sources.py first.")
        return []

    # Proses sumber secara paralel agar tidak sequential (beda 30s vs 10s)
    max_workers = min(len(sources), 4)
    logger.info("Crawling %d sources with %d parallel workers", len(sources), max_workers)
    results: list[SourceStats] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(process_source, source, max_articles_per_source): source
            for source in sources
        }
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.error("Source crawl thread failed for %s: %s", source.name, exc)
    return results


if __name__ == "__main__":
    run_crawler()
