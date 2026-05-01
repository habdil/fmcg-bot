from __future__ import annotations

from dataclasses import dataclass

from crawling_bot.ai.query_parser import AnalystQueryParser
from crawling_bot.main import SourceStats, run_crawler
from crawling_bot.services.signal_service import search_insights_for_terms
from crawling_bot.schemas.analyst_schema import AnalystQuery
from telegram_bot.services.insight_service import product_deep_analysis_message


@dataclass(frozen=True)
class AnalystResult:
    query: AnalystQuery
    answer: str
    crawl_stats: list[SourceStats]
    evidence_count: int


def analyze_question(
    question: str,
    *,
    crawl_first: bool = True,
    max_sources: int = 8,
    max_articles_per_source: int = 2,
    evidence_limit: int = 20,
) -> AnalystResult:
    parser = AnalystQueryParser()
    query = parser.parse(question)

    stats: list[SourceStats] = []
    if crawl_first:
        stats = run_crawler(
            max_articles_per_source=max_articles_per_source,
            source_limit=max_sources,
        )

    rows = _filter_rows_for_query(query, search_insights_for_terms(query.search_terms, limit=evidence_limit))
    answer = product_deep_analysis_message(
        query.normalized_keyword,
        period_days=7,
        crawl_stats=stats,
        rows=rows,
    )
    return AnalystResult(
        query=query,
        answer=answer,
        crawl_stats=stats,
        evidence_count=len(rows),
    )


def _filter_rows_for_query(query: AnalystQuery, rows: list[dict]) -> list[dict]:
    if query.product != "minyak goreng":
        return rows

    filtered = [row for row in rows if _is_cooking_oil_context(row)]
    return filtered or rows


def _is_cooking_oil_context(row: dict) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ["product", "title", "reason", "evidence_text", "ai_polished_summary"]
    ).lower()
    positive_terms = ["minyak goreng", "minyak kita", "migor", "sawit", "cpo", "kelapa sawit"]
    petroleum_terms = ["minyak mentah", "minyak dunia", "minyak bumi", "bbm", "bahan bakar", "barel", "brent", "wti", "opec", "hormuz"]
    if any(term in text for term in positive_terms):
        return True
    if any(term in text for term in petroleum_terms):
        return False
    return True
