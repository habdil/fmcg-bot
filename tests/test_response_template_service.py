from datetime import datetime, timezone
from decimal import Decimal

from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary, PricePoint
from telegram_bot.services.response_template_service import (
    DETAILED_PRICE_MISSING,
    build_source_coverage,
    format_comparative_analysis,
    format_early_warning_alert,
    format_product_deep_analysis,
    format_search_results,
)


def test_product_template_states_missing_price_data() -> None:
    rows = [
        {
            "signal_type": "shortage",
            "product": "minyak goreng",
            "urgency": "high",
            "severity": 4,
            "confidence_score": 0.82,
            "impact_score": 0.88,
            "reason": "Pasokan disebut terbatas oleh sumber.",
            "evidence_text": "Stok minyak goreng menipis di beberapa wilayah.",
            "source_name": "Test Source",
            "title": "Stok minyak goreng menipis",
            "article_url": "https://example.com/a",
            "published_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        }
    ]
    price = PriceMovementSummary(product="minyak goreng", period_days=7)
    availability = AvailabilitySummary(product="minyak goreng", period_days=7)
    coverage = build_source_coverage(rows, price_summary=price)

    message = format_product_deep_analysis(
        product="minyak goreng",
        rows=rows,
        price_summary=price,
        availability_summary=availability,
        source_coverage=coverage,
    )

    assert "Brief Keputusan Bisnis Sorota" in message
    assert DETAILED_PRICE_MISSING in message
    assert "Kenapa Ini Terjadi" in message
    assert "Sumber & Coverage" in message
    assert "https://example.com/a" in message


def test_alert_format_contains_required_sections() -> None:
    row = {
        "signal_type": "price_increase",
        "product": "gula",
        "urgency": "high",
        "severity": 4,
        "confidence_score": 0.78,
        "evidence_text": "Harga gula naik karena pasokan terbatas.",
        "source_name": "Test Source",
        "title": "Harga gula naik",
        "article_url": "https://example.com/gula",
        "published_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
    }

    message = format_early_warning_alert(row)

    assert "Sorota Early Warning Alert" in message
    assert "Evidence:" in message
    assert "Recommended Action:" in message
    assert "Harga gula naik karena pasokan terbatas." in message


def test_search_template_formats_results() -> None:
    rows = [
        {
            "signal_type": "demand_increase",
            "product": "susu",
            "urgency": "medium",
            "confidence_score": 0.7,
            "source_name": "Test Source",
            "title": "Demand susu meningkat",
            "published_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        }
    ]

    message = format_search_results(query="susu", rows=rows, source_coverage=build_source_coverage(rows))

    assert "Sorota Insight Search Result" in message
    assert "Results Found: 1" in message
    assert "Demand susu meningkat" in message


def test_compare_template_formats_price_and_risk() -> None:
    price_a = PriceMovementSummary(
        product="minyak goreng",
        period_days=7,
        price_points=[
            PricePoint(date=datetime(2026, 4, 30).date(), average_price=Decimal("16000")),
            PricePoint(
                date=datetime(2026, 5, 1).date(),
                average_price=Decimal("16500"),
                change_amount=Decimal("500"),
                change_percent=Decimal("3.13"),
            ),
        ],
        total_change_amount=Decimal("500"),
        total_change_percent=Decimal("3.13"),
        trend_direction="increasing",
        snapshot_count=2,
    )
    price_b = PriceMovementSummary(product="gula", period_days=7)

    message = format_comparative_analysis(
        product_a="minyak goreng",
        product_b="gula",
        rows_a=[{"signal_type": "price_increase", "urgency": "high", "severity": 4}],
        rows_b=[{"signal_type": "demand_increase", "urgency": "medium", "severity": 2}],
        price_a=price_a,
        price_b=price_b,
        availability_a=AvailabilitySummary(product="minyak goreng", period_days=7),
        availability_b=AvailabilitySummary(product="gula", period_days=7),
    )

    assert "Sorota Comparative Analysis" in message
    assert "Price Movement" in message
    assert "Minyak Goreng" in message
    assert DETAILED_PRICE_MISSING in message
