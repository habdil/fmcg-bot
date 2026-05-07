from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from statistics import mean
from typing import Any, Iterable

from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary, SourceCoverage

MONTHS_ID = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}

DETAILED_PRICE_MISSING = (
    "Data harga detail belum tersedia. Analisis ini memakai berita dan signal publik yang dicrawl, "
    "bukan time-series harga marketplace/retail."
)


def build_source_coverage(
    rows: list[dict[str, Any]],
    *,
    price_summary: PriceMovementSummary | None = None,
    crawl_stats: Iterable[Any] | None = None,
) -> SourceCoverage:
    source_names = sorted({str(row.get("source_name")) for row in rows if row.get("source_name")})
    article_ids = {str(row.get("article_id") or row.get("article_url")) for row in rows if row.get("article_id") or row.get("article_url")}
    strong_signals = [
        row
        for row in rows
        if str(row.get("urgency") or "").lower() == "high"
        or int(row.get("severity") or 0) >= 4
        or float(row.get("impact_score") or 0) >= 0.75
    ]
    latest_dates = [_row_datetime(row) for row in rows]
    if price_summary and price_summary.latest_observed_at:
        latest_dates.append(price_summary.latest_observed_at)
    latest_observed_at = max((item for item in latest_dates if item is not None), default=None)

    crawled_sources = len(source_names)
    crawled_articles = len(article_ids)
    relevant_articles = len(article_ids)
    if crawl_stats is not None:
        stats = list(crawl_stats)
        crawled_sources = len(stats)
        crawled_articles = sum(int(getattr(item, "total_crawled", 0) or 0) for item in stats)
        processed = sum(int(getattr(item, "total_processed", 0) or 0) for item in stats)
        saved = sum(int(getattr(item, "total_saved", 0) or 0) for item in stats)
        relevant_articles = max(len(article_ids), processed, saved)

    return SourceCoverage(
        total_crawled_sources=crawled_sources,
        total_articles_crawled=crawled_articles,
        total_relevant_articles=relevant_articles,
        total_strong_signals=len(strong_signals),
        total_price_snapshots=price_summary.snapshot_count if price_summary else 0,
        latest_observed_at=latest_observed_at,
        source_names=source_names,
    )


def format_product_deep_analysis(
    *,
    product: str,
    rows: list[dict[str, Any]],
    price_summary: PriceMovementSummary,
    availability_summary: AvailabilitySummary,
    source_coverage: SourceCoverage,
    period_days: int = 7,
) -> str:
    counts = _signal_counts(rows)
    confidence = _confidence_percent(rows, price_summary, source_coverage)
    data_quality = _data_quality_label(rows, price_summary, source_coverage)
    status = _status_label(counts, price_summary, source_coverage)
    limitations = _limitations(rows, price_summary, availability_summary, source_coverage)

    lines = [
        f"📊 Brief Intelijen FMCG: {_title(product)}",
        f"Periode: {period_days} hari terakhir",
        f"Status: {status} | Confidence: {confidence}% | Data: {data_quality}",
        "",
        "🧠 Ringkasan untuk BA",
        _executive_summary(product, rows, price_summary, availability_summary, data_quality),
        "",
        "📌 Signal Utama",
        _format_key_signals(counts),
        "",
        "💰 Harga",
        _format_price_movement(price_summary),
        "",
        "📦 Pasokan / Availability",
        _format_availability(availability_summary, counts),
        "",
        "📈 Demand & Sentiment",
        "- Demand: "
        + _format_direction(counts["demand_increase"], counts["demand_decrease"], "belum ada arah kuat dari evidence tersimpan."),
        "- Sentiment: "
        + _format_direction(
            counts["positive_sentiment"],
            counts["negative_sentiment"],
            "belum ada arah kuat dari evidence tersimpan.",
        ),
        "",
        "🔎 Kenapa Ini Terjadi",
        _format_reason_analysis(rows),
        "",
        "💼 Dampak untuk Sub-Distributor",
        _format_business_impact(counts, price_summary, availability_summary),
        "",
        "🎯 Rekomendasi",
        _format_recommendations(counts, price_summary, availability_summary, data_quality),
        "",
        "📚 Sumber & Coverage",
        _format_source_coverage(source_coverage),
        _format_source_links(rows),
        "",
        "⚠️ Batasan",
        _format_bullets(limitations),
    ]
    return "\n".join(lines)


def format_daily_trend_brief(
    *,
    rows: list[dict[str, Any]],
    source_coverage: SourceCoverage,
    report_date: date | None = None,
) -> str:
    report_date = report_date or datetime.now(timezone.utc).date()
    if not rows:
        return (
            "🔥 FMCG Daily Trend Brief\n"
            f"Date: {_format_date(report_date)}\n"
            "Data Coverage: belum ada signal hari ini.\n"
            "Confidence: LOW\n\n"
            "Top Products Today:\n"
            "- Belum ada produk dengan signal kuat.\n\n"
            "Analyst Note:\n"
            "Jalankan crawler atau perluas source untuk mendapatkan brief harian.\n\n"
            "Recommended Watchlist:\n- Belum tersedia."
        )

    grouped = _group_rows_by_product(rows)
    counts = _signal_counts(rows)
    quality = _data_quality_label(rows, None, source_coverage)
    lines = [
        "🔥 FMCG Daily Trend Brief",
        f"Date: {_format_date(report_date)}",
        f"Data Coverage: {source_coverage.total_relevant_articles} artikel relevan dari {_format_source_names(source_coverage.source_names)}",
        f"Confidence: {quality}",
        "",
        "Top Products Today:",
    ]
    for index, item in enumerate(grouped[:5], start=1):
        product_rows = item["rows"]
        product_counts = _signal_counts(product_rows)
        lines.extend(
            [
                f"{index}. {_title(item['product'])}",
                f"   Status: {_status_label(product_counts, None, build_source_coverage(product_rows))}",
                f"   Main Signals: {_top_signal_text(product_counts)}",
                f"   Why it matters: {_short_reason(product_rows)}",
                f"   Business implication: {_short_business_implication(product_counts)}",
                "",
            ]
        )

    lines.extend(
        [
            "Analyst Note:",
            _market_direction_note(counts),
            "",
            "Recommended Watchlist:",
        ]
    )
    lines.extend(f"- {_title(item['product'])}" for item in grouped[:5])
    lines.extend(["", _format_source_links(rows, limit=3)])
    return "\n".join(lines).rstrip()


def format_weekly_intelligence_report(
    *,
    rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]],
    source_coverage: SourceCoverage,
    period_label: str = "Last 7 Days",
) -> str:
    quality = _data_quality_label(rows, None, source_coverage)
    if not rows:
        return (
            "📈 Weekly FMCG Intelligence Report\n"
            f"Period: {period_label}\n"
            "Confidence: LOW\n\n"
            "Executive Summary\n"
            "Belum ada signal mingguan yang cukup untuk membuat laporan source-grounded.\n\n"
            "Top Weekly Movements:\n- Belum tersedia.\n\n"
            "Week-over-Week Insight:\n"
            "Data pembanding belum tersedia.\n\n"
            "Recommended Actions for Next Week\n- Jalankan crawler berkala dan tambahkan source harga/stock resmi.\n\n"
            "Source Coverage\n"
            f"{_format_source_coverage(source_coverage)}"
        )

    grouped = _group_rows_by_product(rows)
    previous_counts = Counter(_row_product(row) for row in previous_rows)
    lines = [
        "📈 Weekly FMCG Intelligence Report",
        f"Period: {period_label}",
        f"Confidence: {quality}",
        "",
        "Executive Summary",
        _market_direction_note(_signal_counts(rows)),
        "",
        "Top Weekly Movements:",
    ]
    for index, item in enumerate(grouped[:5], start=1):
        product = item["product"]
        product_rows = item["rows"]
        counts = _signal_counts(product_rows)
        previous_count = previous_counts.get(product, 0)
        current_count = len(product_rows)
        direction = "naik" if current_count > previous_count else "turun" if current_count < previous_count else "stabil"
        lines.extend(
            [
                f"{index}. {_title(product)}",
                f"   Trend Direction: {direction} ({current_count} signal vs {previous_count} periode sebelumnya)",
                f"   Price Movement: {_signal_price_phrase(counts)}",
                f"   Availability: {_availability_phrase_from_counts(counts)}",
                f"   Demand: {_demand_phrase(counts)}",
                f"   Reason: {_short_reason(product_rows)}",
                f"   Business Impact: {_short_business_implication(counts)}",
                "",
            ]
        )

    lines.extend(
        [
            "Week-over-Week Insight:",
            _week_over_week_note(rows, previous_rows),
            "",
            "Recommended Actions for Next Week",
            _format_recommendations(_signal_counts(rows), None, None, quality),
            "",
            "Source Coverage",
            _format_source_coverage(source_coverage),
            _format_source_links(rows, limit=5),
        ]
    )
    return "\n".join(lines).rstrip()


def format_early_warning_alert(row: dict[str, Any]) -> str:
    product = _row_product(row)
    detected_at = _row_datetime(row)
    source = f"{row.get('source_name') or '-'} - {_clean_text(row.get('title') or '-', 120)}"
    return (
        "🚨 FMCG Early Warning Alert\n"
        f"Urgency: {str(row.get('urgency') or 'high').upper()}\n"
        f"Product: {_title(product)}\n"
        f"Signal: {row.get('signal_type') or '-'}\n"
        f"Detected At: {_format_datetime(detected_at)}\n"
        f"Confidence: {_as_percent(row.get('confidence_score'))}%\n\n"
        "What Happened:\n"
        f"{_clean_text(row.get('ai_polished_summary') or row.get('title') or '-', 220)}\n\n"
        "Why It Matters:\n"
        f"{row.get('explanation') or _short_business_implication(_signal_counts([row]))}\n\n"
        "Evidence:\n"
        f"{_clean_text(row.get('evidence_text') or 'Evidence text belum tersedia di record signal.', 260)}\n\n"
        "Potential Business Impact:\n"
        f"{_short_business_implication(_signal_counts([row]))}\n\n"
        "Recommended Action:\n"
        f"{_format_recommendations(_signal_counts([row]), None, None, 'MEDIUM')}\n\n"
        "Sources:\n"
        f"- {source}\n"
        f"- {_source_url(row)}\n\n"
        "Limitations:\n"
        "- Alert ini berasal dari artikel/signal tersimpan. Validasi stok, harga supplier, dan coverage wilayah sebelum tindakan operasional."
    )


def format_search_results(
    *,
    query: str,
    rows: list[dict[str, Any]],
    source_coverage: SourceCoverage | None = None,
) -> str:
    if not rows:
        return (
            "🔍 FMCG Insight Search Result\n"
            f"Query: {query}\n"
            "Results Found: 0\n\n"
            "Tidak ada strong data yang ditemukan. Jalankan crawler, gunakan keyword lebih umum, "
            "atau tambahkan source yang lebih relevan."
        )

    lines = [
        "🔍 FMCG Insight Search Result",
        f"Query: {query}",
        f"Results Found: {len(rows)}",
        "",
    ]
    for index, row in enumerate(rows[:10], start=1):
        lines.extend(
            [
                f"{index}. Product/Entity: {_title(_row_product(row))}",
                f"   Signal: {row.get('signal_type') or '-'}",
                f"   Summary: {_clean_text(row.get('ai_polished_summary') or row.get('title') or '-', 160)}",
                f"   Source: {row.get('source_name') or '-'}",
                f"   Link: {_source_url(row)}",
                f"   Date: {_format_datetime(_row_datetime(row))}",
                f"   Urgency: {str(row.get('urgency') or '-').upper()}",
                f"   Confidence: {_as_percent(row.get('confidence_score'))}%",
                "",
            ]
        )
    if source_coverage:
        lines.extend(["Source Coverage:", _format_source_coverage(source_coverage)])
    return "\n".join(lines).rstrip()


def format_comparative_analysis(
    *,
    product_a: str,
    product_b: str,
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    price_a: PriceMovementSummary,
    price_b: PriceMovementSummary,
    availability_a: AvailabilitySummary,
    availability_b: AvailabilitySummary,
    period_days: int = 7,
) -> str:
    counts_a = _signal_counts(rows_a)
    counts_b = _signal_counts(rows_b)
    risk_a = _risk_score(counts_a, price_a, availability_a)
    risk_b = _risk_score(counts_b, price_b, availability_b)
    higher_risk_text = (
        f"{_title(product_a)} membutuhkan perhatian lebih besar"
        if risk_a > risk_b
        else f"{_title(product_b)} membutuhkan perhatian lebih besar"
        if risk_b > risk_a
        else "Kedua produk relatif seimbang dan perlu dipantau paralel"
    )

    lines = [
        "⚖️ FMCG Comparative Analysis",
        f"Products: {_title(product_a)} vs {_title(product_b)}",
        f"Period: Last {period_days} Days",
        "",
        "Comparison Table:",
        f"- Price Movement: {_title(product_a)} = {_price_comparison_text(price_a)} | {_title(product_b)} = {_price_comparison_text(price_b)}",
        f"- Availability Risk: {_title(product_a)} = {_availability_compare_text(availability_a, counts_a)} | {_title(product_b)} = {_availability_compare_text(availability_b, counts_b)}",
        f"- Demand Signal: {_title(product_a)} = {_demand_phrase(counts_a)} | {_title(product_b)} = {_demand_phrase(counts_b)}",
        f"- Sentiment: {_title(product_a)} = {_sentiment_phrase(counts_a)} | {_title(product_b)} = {_sentiment_phrase(counts_b)}",
        f"- Urgency: {_title(product_a)} = {_urgency_summary(rows_a)} | {_title(product_b)} = {_urgency_summary(rows_b)}",
        f"- Confidence: {_title(product_a)} = {_confidence_percent(rows_a, price_a, build_source_coverage(rows_a, price_summary=price_a))}% | {_title(product_b)} = {_confidence_percent(rows_b, price_b, build_source_coverage(rows_b, price_summary=price_b))}%",
        "",
        "Winner / Higher Risk:",
        f"{higher_risk_text} berdasarkan kombinasi signal harga, availability, urgency, dan confidence.",
        "",
        "Business Recommendation:",
        _compare_recommendation(product_a, product_b, risk_a, risk_b),
        "",
        f"Sumber {_title(product_a)}:",
        _format_source_links(rows_a, limit=3),
        "",
        f"Sumber {_title(product_b)}:",
        _format_source_links(rows_b, limit=3),
        "",
        "Limitations:",
    ]
    if not price_a.has_price_data or not price_b.has_price_data:
        lines.append(f"- {DETAILED_PRICE_MISSING}")
    lines.append("- Perbandingan ini memakai data tersimpan; validasi dengan data sell-in, sell-out, stok gudang, dan harga supplier internal.")
    return "\n".join(lines)


def _format_price_movement(price_summary: PriceMovementSummary) -> str:
    if not price_summary.has_price_data:
        return DETAILED_PRICE_MISSING

    lines: list[str] = []
    for point in price_summary.price_points:
        change = ""
        if point.change_amount is not None and point.change_percent is not None:
            change = f" ({_format_money_change(point.change_amount, price_summary.currency)} / {_format_percent_change(point.change_percent)})"
        source_note = f" | {point.source_count} source"
        if point.locations:
            source_note += f" | {', '.join(point.locations[:3])}"
        lines.append(f"- {_format_date(point.date)}: {_format_money(point.average_price, price_summary.currency)}{change}{source_note}")

    if price_summary.total_change_amount is not None and price_summary.total_change_percent is not None:
        lines.extend(
            [
                "",
                "Total pergerakan:",
                f"{_format_money_change(price_summary.total_change_amount, price_summary.currency)} ({_format_percent_change(price_summary.total_change_percent)}) dalam {max(len(price_summary.price_points) - 1, 0)} hari",
            ]
        )
    lines.extend(
        [
            "",
            f"Arah trend: {price_summary.trend_direction}",
            f"Harga tertinggi: {_format_money(price_summary.highest_price, price_summary.currency)}",
            f"Harga terendah: {_format_money(price_summary.lowest_price, price_summary.currency)}",
            f"Rata-rata: {_format_money(price_summary.average_price, price_summary.currency)}",
            f"Jumlah source: {price_summary.source_count}",
            f"Kualitas data: {price_summary.data_quality.upper()}",
        ]
    )
    if price_summary.source_references:
        lines.extend(["", "Sumber harga:"])
        for reference in price_summary.source_references[:5]:
            label = reference.reference_label or reference.source_name
            observed = f" | Diambil: {_format_datetime(reference.observed_at)}" if reference.observed_at else ""
            lines.append(f"- {label}{observed}")
            url = reference.reference_url or reference.source_url
            if url:
                lines.append(f"  {url}")
    return "\n".join(lines)


def _format_availability(availability: AvailabilitySummary, counts: Counter[str]) -> str:
    if availability.has_availability_data:
        location = f" Lokasi: {', '.join(availability.locations[:5])}." if availability.locations else ""
        seller = f" Jumlah seller terbaru: {availability.seller_count_latest}." if availability.seller_count_latest is not None else ""
        return (
            f"Signal availability: {availability.availability_signal}.\n"
            f"Snapshot: in_stock={availability.in_stock_count}, low_stock={availability.low_stock_count}, "
            f"out_of_stock={availability.out_of_stock_count}, unknown={availability.unknown_count}."
            f"{seller}{location}"
        )

    risk_count = counts["shortage"] + counts["distribution_disruption"]
    if risk_count:
        return (
            f"Belum ada snapshot stok. Ada {risk_count} signal risiko pasokan/distribusi "
            "dari artikel publik, sehingga availability perlu dipantau."
        )
    return "Belum ada snapshot stok dan belum ada signal shortage kuat dari artikel tersimpan."


def _format_key_signals(counts: Counter[str]) -> str:
    if not counts:
        return "- Belum ada signal kuat."
    lines: list[str] = []
    for signal_type, count in counts.most_common(5):
        label = _signal_label(signal_type)
        lines.append(f"- {label}: {count} signal")
    return "\n".join(lines)


def _format_reason_analysis(rows: list[dict[str, Any]]) -> str:
    items: list[str] = []
    seen_snippets: set[str] = set()
    for row in _unique_article_rows(rows, limit=5):
        snippet = _evidence_snippet(row)
        if not snippet or snippet in seen_snippets:
            continue
        seen_snippets.add(snippet)
        source = row.get("source_name") or "source tidak diketahui"
        signal = _signal_label(str(row.get("signal_type") or "signal"))
        items.append(
            f"- {signal}: {snippet}\n"
            f"  Sumber: {source} | {_source_url(row)}"
        )
    if not items:
        return "Reason belum jelas dari evidence tersimpan. Sistem tidak menyimpulkan sebab tanpa sumber."
    return "\n".join(items)


def _format_business_impact(
    counts: Counter[str],
    price_summary: PriceMovementSummary | None,
    availability: AvailabilitySummary | None,
) -> str:
    impacts: list[str] = []
    if price_summary and price_summary.trend_direction == "increasing":
        impacts.append("Margin sub-distributor berpotensi tertekan jika harga supplier naik lebih cepat dari harga jual.")
    if counts["price_increase"] > counts["price_decrease"]:
        impacts.append("Perlu skenario adjustment margin dan komunikasi harga ke pelanggan prioritas.")
    if counts["shortage"] or counts["distribution_disruption"] or (availability and availability.availability_signal in {"limited", "out_of_stock"}):
        impacts.append("Stock planning dan alokasi distribusi perlu diprioritaskan untuk SKU fast-moving.")
    if counts["demand_increase"] > counts["demand_decrease"]:
        impacts.append("Demand positif bisa menjadi peluang sell-through, tetapi tetap perlu validasi stok.")
    if counts["negative_sentiment"] > counts["positive_sentiment"]:
        impacts.append("Sentiment negatif dapat memengaruhi perputaran barang dan prioritas promosi.")
    if not impacts:
        impacts.append("Belum ada impact operasional kuat; gunakan sebagai konteks monitoring.")
    return _format_bullets(impacts)


def _format_recommendations(
    counts: Counter[str],
    price_summary: PriceMovementSummary | None,
    availability: AvailabilitySummary | None,
    quality: str,
) -> str:
    actions: list[str] = []
    if price_summary and price_summary.trend_direction in {"increasing", "volatile"}:
        actions.append("Monitor harga supplier harian dan siapkan skenario adjustment margin.")
    if counts["price_increase"] > counts["price_decrease"]:
        actions.append("Bandingkan alternatif supplier sebelum menaikkan harga jual.")
    if counts["shortage"] or counts["distribution_disruption"] or (availability and availability.availability_signal in {"limited", "out_of_stock"}):
        actions.append("Siapkan buffer stock terbatas untuk SKU prioritas dan cek lead time distribusi.")
    if counts["demand_increase"] > counts["demand_decrease"]:
        actions.append("Prioritaskan alokasi stok ke area/channel dengan demand paling kuat.")
    if quality != "HIGH":
        actions.append("Perluas evidence dengan source harga/stock resmi sebelum keputusan besar.")
    if not actions:
        actions.append("Lanjutkan monitoring; belum ada signal yang cukup kuat untuk tindakan agresif.")
    return _format_bullets(actions[:5])


def _format_source_coverage(coverage: SourceCoverage) -> str:
    latest = _format_datetime(coverage.latest_observed_at)
    return (
        f"- Source dicrawl: {coverage.total_crawled_sources}\n"
        f"- Artikel dicrawl/relevan: {coverage.total_articles_crawled}/{coverage.total_relevant_articles}\n"
        f"- Signal kuat: {coverage.total_strong_signals}\n"
        f"- Snapshot harga: {coverage.total_price_snapshots}\n"
        f"- Update terbaru: {latest}\n"
        f"- Media/source: {_format_source_names(coverage.source_names)}"
    )


def _format_source_links(rows: list[dict[str, Any]], limit: int = 5) -> str:
    unique_rows = _unique_article_rows(rows, limit=limit)
    if not unique_rows:
        return "Link sumber utama: belum tersedia."

    lines = ["Link sumber utama:"]
    for index, row in enumerate(unique_rows, start=1):
        source = row.get("source_name") or "Source tidak diketahui"
        title = _clean_text(row.get("title") or row.get("ai_polished_summary") or "-", 110)
        date_text = _format_datetime(_row_datetime(row))
        lines.append(f"{index}. {source} | {date_text}")
        lines.append(f"   {title}")
        lines.append(f"   {_source_url(row)}")
    return "\n".join(lines)


def _unique_article_rows(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("article_url") or row.get("article_id") or row.get("title") or id(row))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
        if len(unique) >= limit:
            break
    return unique


def _evidence_snippet(row: dict[str, Any]) -> str:
    for key in ("evidence_text", "reason", "explanation", "ai_polished_summary", "title"):
        text = _clean_text(row.get(key), 240)
        if text and text != "-":
            return text
    return ""


def _source_url(row: dict[str, Any]) -> str:
    return str(row.get("article_url") or row.get("source_url") or "URL belum tersedia")


def _clean_text(value: Any, max_length: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return "-"
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _limitations(
    rows: list[dict[str, Any]],
    price_summary: PriceMovementSummary,
    availability: AvailabilitySummary,
    coverage: SourceCoverage,
) -> list[str]:
    items = ["Analisis hanya memakai data publik yang sudah dicrawl dan tersimpan."]
    if not price_summary.has_price_data:
        items.append(DETAILED_PRICE_MISSING)
    if not availability.has_availability_data:
        items.append("Snapshot stok/availability detail belum tersedia.")
    if not rows:
        items.append("Belum ada article signal yang relevan untuk produk ini.")
    if coverage.total_crawled_sources < 2:
        items.append("Coverage source masih rendah; confidence perlu ditingkatkan dengan source tambahan.")
    return items


def _group_rows_by_product(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_row_product(row)].append(row)
    ranked = []
    for product, product_rows in groups.items():
        score = sum(float(row.get("impact_score") or 0) for row in product_rows)
        score += sum(int(row.get("severity") or 0) for row in product_rows) * 0.25
        score += sum(1 for row in product_rows if str(row.get("urgency") or "").lower() == "high")
        ranked.append({"product": product, "rows": product_rows, "score": score})
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def _signal_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("signal_type") or "unknown") for row in rows)


def _row_product(row: dict[str, Any]) -> str:
    return str(row.get("product") or row.get("company") or row.get("location") or "FMCG general")


def _row_datetime(row: dict[str, Any]) -> datetime | None:
    for key in ("published_at", "created_at", "crawled_at", "observed_at"):
        value = row.get(key)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _confidence_percent(
    rows: list[dict[str, Any]],
    price_summary: PriceMovementSummary | None,
    coverage: SourceCoverage,
) -> int:
    values = [float(row.get("confidence_score")) for row in rows if row.get("confidence_score") is not None]
    if values:
        base = int(round(mean(values) * 100))
    elif price_summary and price_summary.data_quality == "high":
        base = 80
    elif price_summary and price_summary.has_price_data:
        base = 65
    else:
        base = 40
    if coverage.total_crawled_sources >= 3 and coverage.total_strong_signals >= 2:
        base += 5
    if price_summary and price_summary.has_price_data:
        base += 5
    return max(20, min(base, 95))


def _data_quality_label(
    rows: list[dict[str, Any]],
    price_summary: PriceMovementSummary | None,
    coverage: SourceCoverage,
) -> str:
    if (
        price_summary
        and price_summary.has_price_data
        and coverage.total_crawled_sources >= 3
        and coverage.total_strong_signals >= 2
    ):
        return "HIGH"
    if len(rows) >= 3 or coverage.total_crawled_sources >= 2 or (price_summary and price_summary.has_price_data):
        return "MEDIUM"
    return "LOW"


def _status_label(
    counts: Counter[str],
    price_summary: PriceMovementSummary | None,
    coverage: SourceCoverage,
) -> str:
    if coverage.total_strong_signals >= 2 or counts["shortage"] or counts["distribution_disruption"]:
        return "PERLU DIPANTAU"
    if price_summary and price_summary.trend_direction in {"increasing", "volatile"}:
        return "PERLU DIPANTAU"
    if sum(counts.values()):
        return "WATCHLIST"
    return "DATA TERBATAS"


def _executive_summary(
    product: str,
    rows: list[dict[str, Any]],
    price_summary: PriceMovementSummary,
    availability: AvailabilitySummary,
    data_quality: str,
) -> str:
    counts = _signal_counts(rows)
    if not rows and not price_summary.has_price_data:
        return (
            f"Belum ada evidence kuat untuk {_title(product)}. Analisis belum boleh menyimpulkan harga, "
            "pasokan, demand, atau sentiment tanpa data tambahan."
        )
    parts = [f"{_title(product)} perlu dipantau berdasarkan {len(rows)} signal tersimpan dengan kualitas data {data_quality}."]
    if price_summary.has_price_data:
        parts.append(
            f"Price snapshot menunjukkan arah {price_summary.trend_direction} dengan total movement "
            f"{_format_money_change(price_summary.total_change_amount, price_summary.currency) if price_summary.total_change_amount is not None else 'belum cukup data'}."
        )
    if counts:
        parts.append(f"Signal utama: {_top_signal_text(counts)}.")
    if availability.has_availability_data:
        parts.append(f"Availability signal: {availability.availability_signal}.")
    return " ".join(parts)


def _format_direction(up_count: int, down_count: int, neutral: str) -> str:
    if up_count > down_count:
        return f"Terindikasi naik: {up_count} signal naik vs {down_count} signal turun."
    if down_count > up_count:
        return f"Terindikasi turun: {down_count} signal turun vs {up_count} signal naik."
    if up_count or down_count:
        return f"Signal campuran: {up_count} naik vs {down_count} turun."
    return neutral


def _top_signal_text(counts: Counter[str]) -> str:
    if not counts:
        return "belum ada signal kuat"
    return ", ".join(f"{_signal_label(signal)} ({count})" for signal, count in counts.most_common(4))


def _signal_label(signal_type: str) -> str:
    labels = {
        "price_increase": "Harga naik",
        "price_decrease": "Harga turun",
        "shortage": "Risiko pasokan",
        "distribution_disruption": "Gangguan distribusi",
        "demand_increase": "Demand naik",
        "demand_decrease": "Demand turun",
        "positive_sentiment": "Sentiment positif",
        "negative_sentiment": "Sentiment negatif",
        "regulation_change": "Perubahan regulasi",
        "oversupply": "Oversupply",
    }
    return labels.get(signal_type, signal_type.replace("_", " ").title())


def _short_reason(rows: list[dict[str, Any]]) -> str:
    for row in _unique_article_rows(rows, limit=3):
        snippet = _evidence_snippet(row)
        if snippet:
            return _clean_text(snippet, 150)
    return "Reason belum eksplisit di evidence tersimpan."


def _short_business_implication(counts: Counter[str]) -> str:
    if counts["shortage"] or counts["distribution_disruption"]:
        return "Risiko supply dapat memengaruhi buffer stock, lead time, dan prioritas distribusi."
    if counts["price_increase"] > counts["price_decrease"]:
        return "Tekanan harga dapat memengaruhi margin dan negosiasi supplier."
    if counts["demand_increase"] > counts["demand_decrease"]:
        return "Peluang demand perlu diseimbangkan dengan ketersediaan stok."
    if counts["negative_sentiment"] > counts["positive_sentiment"]:
        return "Sentiment negatif perlu dipantau karena dapat menekan sell-through."
    return "Belum ada implikasi operasional kuat; tetap gunakan sebagai monitoring."


def _market_direction_note(counts: Counter[str]) -> str:
    pressure = []
    if counts["price_increase"] > counts["price_decrease"]:
        pressure.append("tekanan harga naik")
    if counts["shortage"] or counts["distribution_disruption"]:
        pressure.append("risiko availability")
    if counts["demand_increase"] > counts["demand_decrease"]:
        pressure.append("demand menguat")
    if counts["negative_sentiment"] > counts["positive_sentiment"]:
        pressure.append("sentiment negatif")
    if not pressure:
        return "Arah pasar belum kuat dari evidence hari ini; monitoring tetap diperlukan."
    return "Pasar FMCG terindikasi memiliki " + ", ".join(pressure) + "."


def _week_over_week_note(rows: list[dict[str, Any]], previous_rows: list[dict[str, Any]]) -> str:
    if not previous_rows:
        return "Previous period data belum tersedia, sehingga week-over-week comparison masih terbatas."
    delta = len(rows) - len(previous_rows)
    direction = "lebih tinggi" if delta > 0 else "lebih rendah" if delta < 0 else "relatif sama"
    return f"Jumlah signal minggu ini {direction} dibanding periode sebelumnya ({len(rows)} vs {len(previous_rows)} signal)."


def _signal_price_phrase(counts: Counter[str]) -> str:
    if counts["price_increase"] or counts["price_decrease"]:
        return _format_direction(counts["price_increase"], counts["price_decrease"], "Belum ada signal harga.")
    return "Belum ada exact price time-series; hanya tersedia signal berita jika ada."


def _availability_phrase_from_counts(counts: Counter[str]) -> str:
    risk = counts["shortage"] + counts["distribution_disruption"]
    if risk:
        return f"{risk} signal shortage/distribution risk."
    if counts["oversupply"]:
        return f"{counts['oversupply']} signal oversupply."
    return "Belum ada risk kuat."


def _demand_phrase(counts: Counter[str]) -> str:
    return _format_direction(counts["demand_increase"], counts["demand_decrease"], "Demand belum jelas.")


def _sentiment_phrase(counts: Counter[str]) -> str:
    return _format_direction(counts["positive_sentiment"], counts["negative_sentiment"], "Sentiment belum jelas.")


def _price_comparison_text(price: PriceMovementSummary) -> str:
    if not price.has_price_data:
        return "exact price unavailable"
    movement = _format_percent_change(price.total_change_percent) if price.total_change_percent is not None else "n/a"
    return f"{price.trend_direction}, {movement}"


def _availability_compare_text(availability: AvailabilitySummary, counts: Counter[str]) -> str:
    if availability.has_availability_data:
        return availability.availability_signal
    return _availability_phrase_from_counts(counts)


def _urgency_summary(rows: list[dict[str, Any]]) -> str:
    high = sum(1 for row in rows if str(row.get("urgency") or "").lower() == "high" or int(row.get("severity") or 0) >= 4)
    if high:
        return f"{high} high/severe signal"
    return f"{len(rows)} regular signal"


def _risk_score(
    counts: Counter[str],
    price: PriceMovementSummary,
    availability: AvailabilitySummary,
) -> float:
    score = 0.0
    score += counts["price_increase"] * 1.5
    score += counts["shortage"] * 2
    score += counts["distribution_disruption"] * 2
    score += counts["negative_sentiment"]
    if price.trend_direction in {"increasing", "volatile"}:
        score += 2
    if availability.availability_signal in {"limited", "out_of_stock"}:
        score += 2
    return score


def _compare_recommendation(product_a: str, product_b: str, risk_a: float, risk_b: float) -> str:
    if risk_a == risk_b:
        return (
            f"Pantau {_title(product_a)} dan {_title(product_b)} secara paralel. Jangan geser alokasi stok besar "
            "sebelum ada evidence harga/stock tambahan."
        )
    higher = product_a if risk_a > risk_b else product_b
    lower = product_b if risk_a > risk_b else product_a
    return (
        f"Prioritaskan monitoring {_title(higher)} untuk harga, availability, dan supplier lead time. "
        f"{_title(lower)} tetap dipantau sebagai pembanding demand dan margin."
    )


def _format_money(value: Decimal | None, currency: str = "IDR") -> str:
    if value is None:
        return "-"
    if currency.upper() == "IDR":
        amount = int(value.quantize(Decimal("1")))
        return f"Rp {amount:,}".replace(",", ".")
    return f"{currency} {value:,.2f}"


def _format_money_change(value: Decimal, currency: str = "IDR") -> str:
    sign = "+" if value > 0 else ""
    if currency.upper() == "IDR":
        amount = int(abs(value).quantize(Decimal("1")))
        prefix = "+Rp " if value > 0 else "-Rp " if value < 0 else "Rp "
        return f"{prefix}{amount:,}".replace(",", ".")
    return f"{sign}{currency} {value:,.2f}"


def _format_percent_change(value: Decimal | None) -> str:
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value}%"


def _format_date(value: date) -> str:
    return f"{value.day:02d} {MONTHS_ID[value.month]} {value.year}"


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return _format_date(value.date())


def _format_source_names(names: list[str]) -> str:
    if not names:
        return "-"
    visible = names[:5]
    suffix = f" +{len(names) - 5} more" if len(names) > 5 else ""
    return ", ".join(visible) + suffix


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _title(value: str) -> str:
    return value.strip().title() if value else "-"


def _as_percent(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(round(number * 100 if number <= 1 else number))
