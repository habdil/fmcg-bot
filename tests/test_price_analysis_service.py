from datetime import datetime, timezone
from decimal import Decimal

from crawling_bot.services.price_analysis_service import calculate_price_movement


def test_price_movement_calculates_daily_changes_and_summary() -> None:
    snapshots = [
        {
            "product_name": "Minyak Goreng",
            "price": Decimal("15200"),
            "source_name": "Source A",
            "location": "Jakarta",
            "observed_at": datetime(2026, 4, 28, tzinfo=timezone.utc),
        },
        {
            "product_name": "Minyak Goreng",
            "price": Decimal("15500"),
            "source_name": "Source A",
            "location": "Jakarta",
            "observed_at": datetime(2026, 4, 29, tzinfo=timezone.utc),
        },
        {
            "product_name": "Minyak Goreng",
            "price": Decimal("16100"),
            "source_name": "Source B",
            "location": "Bandung",
            "observed_at": datetime(2026, 4, 30, tzinfo=timezone.utc),
        },
        {
            "product_name": "Minyak Goreng",
            "price": Decimal("16500"),
            "source_name": "Source C",
            "location": "Bandung",
            "observed_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        },
    ]

    summary = calculate_price_movement("minyak goreng", snapshots, period_days=7)

    assert len(summary.price_points) == 4
    assert summary.price_points[1].change_amount == Decimal("300.00")
    assert summary.price_points[1].change_percent == Decimal("1.97")
    assert summary.total_change_amount == Decimal("1300.00")
    assert summary.total_change_percent == Decimal("8.55")
    assert summary.trend_direction == "increasing"
    assert summary.highest_price == Decimal("16500.00")
    assert summary.lowest_price == Decimal("15200.00")
    assert summary.source_count == 3
