from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import logging
from statistics import mean
from threading import Lock
from typing import Any, Iterable

from crawling_bot.ai.gemini_report_polisher import GeminiReportPolisher
from crawling_bot.main import run_crawler
from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary
from crawling_bot.services.price_analysis_service import get_availability_summary, get_price_movement
from crawling_bot.services.signal_service import (
    get_high_urgency_alerts,
    period_signal_rows,
    recent_signal_rows,
    search_insights,
    trending,
)
from telegram_bot.services.response_template_service import (
    build_source_coverage,
    format_comparative_analysis,
    format_daily_trend_brief,
    format_early_warning_alert,
    format_product_deep_analysis,
    format_search_results,
    format_weekly_intelligence_report,
)

logger = logging.getLogger(__name__)

CRAWL_FIRST_LOCK = Lock()
DEFAULT_CRAWL_FIRST_SOURCE_LIMIT = 8
DEFAULT_CRAWL_FIRST_MAX_ARTICLES = 2


def alert_messages(
    limit: int = 5,
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
) -> list[str]:
    _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    rows = get_high_urgency_alerts(limit=limit)
    if not rows:
        return ["Belum ada high urgency FMCG alert."]
    return [format_early_warning_alert(row) for row in rows]


def report_message() -> str:
    return daily_trend_brief_message()


def search_message(
    keyword: str,
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
) -> str:
    crawl_stats = _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    rows = search_insights(keyword, limit=10)
    coverage = build_source_coverage(rows, crawl_stats=crawl_stats)
    return format_search_results(query=keyword, rows=rows, source_coverage=coverage)


def _signal_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("signal_type") or "unknown") for row in rows)


def _average(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return round(mean(values), 2) if values else 0.0


def _latest_rows(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    return rows[:limit]


def _direction(up_count: int, down_count: int, neutral_label: str = "belum jelas") -> str:
    if up_count > down_count:
        return "cenderung naik"
    if down_count > up_count:
        return "cenderung turun"
    if up_count or down_count:
        return "campuran"
    return neutral_label


def build_keyword_trend_summary(keyword: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            f"Belum ada insight untuk: {keyword}\n\n"
            "Jalankan /crawl dulu, lalu coba lagi. Contoh: /crawl 3"
        )

    counts = _signal_counts(rows)
    price_direction = _direction(counts["price_increase"], counts["price_decrease"])
    demand_direction = _direction(counts["demand_increase"], counts["demand_decrease"])
    sentiment_direction = _direction(
        counts["positive_sentiment"],
        counts["negative_sentiment"],
        neutral_label="belum kuat",
    )
    shortage_risk_count = counts["shortage"] + counts["distribution_disruption"]
    high_urgency_count = sum(1 for row in rows if row.get("urgency") == "high")
    avg_impact = _average(rows, "impact_score")
    avg_confidence = _average(rows, "confidence_score")

    if shortage_risk_count >= 2 or high_urgency_count >= 2:
        outlook = "risiko perlu dipantau ketat"
    elif counts["price_increase"] > counts["price_decrease"]:
        outlook = "ada tekanan kenaikan harga"
    elif counts["demand_increase"] > counts["demand_decrease"]:
        outlook = "ada peluang kenaikan permintaan"
    else:
        outlook = "belum ada arah kuat"

    lines = [
        f"Insight untuk: {keyword}",
        "",
        f"Jumlah signal: {len(rows)}",
        f"Rata-rata impact: {avg_impact}",
        f"Rata-rata confidence: {avg_confidence}",
        f"High urgency: {high_urgency_count}",
        "",
        "Arah signal:",
        f"- Harga: {price_direction}",
        f"- Supply/distribusi: {shortage_risk_count} signal risiko",
        f"- Demand: {demand_direction}",
        f"- Sentiment: {sentiment_direction}",
        "",
        f"Outlook: {outlook}",
        "",
        "Signal terbanyak:",
    ]
    lines.extend(f"- {signal_type}: {count}" for signal_type, count in counts.most_common(6))

    lines.append("")
    lines.append("Referensi terbaru:")
    for row in _latest_rows(rows):
        title = str(row.get("title") or "-")
        if len(title) > 110:
            title = f"{title[:107]}..."
        source = row.get("source_name") or "-"
        signal = row.get("signal_type") or "-"
        lines.append(f"- {signal} | {source} | {title}")

    lines.append("")
    lines.append("Catatan: outlook ini rule-based dari artikel publik yang sudah tersimpan, bukan forecast numerik.")
    return "\n".join(lines)


def keyword_insight_message(keyword: str) -> str:
    return product_deep_analysis_message(keyword, crawl_first=True)


def keyword_trend_message(keyword: str) -> str:
    return product_deep_analysis_message(keyword, crawl_first=True)


def keyword_forecast_message(
    keyword: str,
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
) -> str:
    _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    rows = search_insights(keyword, limit=30)
    if not rows:
        return (
            f"Belum ada data untuk membuat outlook: {keyword}\n\n"
            "Jalankan /crawl dulu, lalu coba lagi. Contoh: /crawl 3"
        )

    counts = _signal_counts(rows)
    actions: list[str] = []
    if counts["price_increase"] > counts["price_decrease"]:
        actions.append("pantau update harga supplier dan siapkan skenario adjustment margin")
    if counts["shortage"] or counts["distribution_disruption"]:
        actions.append("cek ketersediaan supplier dan siapkan buffer stock")
    if counts["demand_increase"] > counts["demand_decrease"]:
        actions.append("prioritaskan alokasi stok untuk area/channel dengan demand kuat")
    if counts["negative_sentiment"] > counts["positive_sentiment"]:
        actions.append("monitor risiko brand dan sell-through di retailer")
    if counts["regulation_change"]:
        actions.append("cek implikasi regulasi ke procurement, pricing, dan distribusi")
    if not actions:
        actions.append("lanjutkan monitoring karena arah signal belum kuat")

    lines = [
        f"Rule-based outlook untuk: {keyword}",
        "",
        build_keyword_trend_summary(keyword, rows),
        "",
        "Recommended action:",
    ]
    lines.extend(f"- {action}" for action in actions[:5])
    return "\n".join(lines)


def trending_message(
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
) -> str:
    _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    data = trending()
    lines = ["Trending FMCG Signals"]
    lines.append("\nSignals")
    if data["signals"]:
        lines.extend(f"- {row['signal_type']}: {row['count']}" for row in data["signals"])
    else:
        lines.append("- Belum ada data.")
    lines.append("\nEntities")
    if data["entities"]:
        lines.extend(
            f"- {row['name']} ({row['entity_type']}): {row['count']}"
            for row in data["entities"]
        )
    else:
        lines.append("- Belum ada data.")
    return "\n".join(lines)


def product_deep_analysis_message(
    keyword: str,
    *,
    period_days: int = 7,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
    crawl_stats: Iterable[Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    polish: bool = True,
) -> str:
    stats = list(crawl_stats) if crawl_stats is not None else _crawl_before_response(
        crawl_first and rows is None,
        max_sources,
        max_articles_per_source,
    )
    signal_rows = rows if rows is not None else search_insights(keyword, limit=40, period_days=period_days)
    price_summary = _safe_price_movement(keyword, period_days)
    availability_summary = _safe_availability_summary(keyword, period_days)
    coverage = build_source_coverage(signal_rows, price_summary=price_summary, crawl_stats=stats)
    structured = format_product_deep_analysis(
        product=keyword,
        rows=signal_rows,
        price_summary=price_summary,
        availability_summary=availability_summary,
        source_coverage=coverage,
        period_days=period_days,
    )
    return _polish(structured) if polish else structured


def daily_trend_brief_message(
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
    polish: bool = True,
) -> str:
    crawl_stats = _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    rows = recent_signal_rows(period_days=1, limit=100)
    coverage = build_source_coverage(rows, crawl_stats=crawl_stats)
    structured = format_daily_trend_brief(rows=rows, source_coverage=coverage)
    return _polish(structured) if polish else structured


def weekly_intelligence_report_message(
    *,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
    polish: bool = True,
) -> str:
    crawl_stats = _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)
    rows = period_signal_rows(start_at=current_start, end_at=now, limit=200)
    previous_rows = period_signal_rows(start_at=previous_start, end_at=current_start, limit=200)
    coverage = build_source_coverage(rows, crawl_stats=crawl_stats)
    structured = format_weekly_intelligence_report(
        rows=rows,
        previous_rows=previous_rows,
        source_coverage=coverage,
        period_label="Last 7 Days",
    )
    return _polish(structured) if polish else structured


def compare_message(
    product_a: str,
    product_b: str,
    *,
    period_days: int = 7,
    crawl_first: bool = True,
    max_sources: int = DEFAULT_CRAWL_FIRST_SOURCE_LIMIT,
    max_articles_per_source: int = DEFAULT_CRAWL_FIRST_MAX_ARTICLES,
    polish: bool = True,
) -> str:
    _crawl_before_response(crawl_first, max_sources, max_articles_per_source)
    rows_a = search_insights(product_a, limit=40, period_days=period_days)
    rows_b = search_insights(product_b, limit=40, period_days=period_days)
    price_a = _safe_price_movement(product_a, period_days)
    price_b = _safe_price_movement(product_b, period_days)
    availability_a = _safe_availability_summary(product_a, period_days)
    availability_b = _safe_availability_summary(product_b, period_days)
    structured = format_comparative_analysis(
        product_a=product_a,
        product_b=product_b,
        rows_a=rows_a,
        rows_b=rows_b,
        price_a=price_a,
        price_b=price_b,
        availability_a=availability_a,
        availability_b=availability_b,
        period_days=period_days,
    )
    return _polish(structured) if polish else structured


def _safe_price_movement(keyword: str, period_days: int) -> PriceMovementSummary:
    try:
        return get_price_movement(keyword, period_days=period_days)
    except Exception as exc:  # pragma: no cover - defensive fallback for missing DB/migration
        logger.warning("Price movement unavailable for %s: %s", keyword, exc)
        return PriceMovementSummary(product=keyword, period_days=period_days)


def _safe_availability_summary(keyword: str, period_days: int) -> AvailabilitySummary:
    try:
        return get_availability_summary(keyword, period_days=period_days)
    except Exception as exc:  # pragma: no cover - defensive fallback for missing DB/migration
        logger.warning("Availability summary unavailable for %s: %s", keyword, exc)
        return AvailabilitySummary(product=keyword, period_days=period_days)


def _polish(structured: str) -> str:
    return GeminiReportPolisher().polish(structured).final_text


def _crawl_before_response(
    crawl_first: bool,
    max_sources: int,
    max_articles_per_source: int,
) -> list[Any]:
    if not crawl_first:
        return []
    with CRAWL_FIRST_LOCK:
        return run_crawler(
            max_articles_per_source=max_articles_per_source,
            source_limit=max_sources,
        )
