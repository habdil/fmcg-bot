from telegram_bot.services.insight_service import build_keyword_trend_summary
from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary
from telegram_bot.services import insight_service


def test_keyword_trend_summary_builds_operational_outlook() -> None:
    rows = [
        {
            "signal_type": "price_increase",
            "urgency": "high",
            "impact_score": 0.82,
            "confidence_score": 0.76,
            "source_name": "Test Source",
            "title": "Harga gula naik karena pasokan terbatas",
        },
        {
            "signal_type": "shortage",
            "urgency": "high",
            "impact_score": 0.79,
            "confidence_score": 0.71,
            "source_name": "Test Source",
            "title": "Stok gula menipis di pasar ritel",
        },
    ]

    message = build_keyword_trend_summary("gula", rows)

    assert "Insight untuk: gula" in message
    assert "Harga: cenderung naik" in message
    assert "Jumlah temuan: 2" in message
    assert "Indikasi terbanyak:" in message


def test_product_deep_analysis_crawls_before_query(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run_crawler(max_articles_per_source=None, source_limit=None):
        calls.append("crawl")
        return []

    def fake_search_insights(keyword, limit=40, period_days=7):
        calls.append("query")
        return [
            {
                "signal_type": "price_increase",
                "product": keyword,
                "urgency": "medium",
                "severity": 3,
                "confidence_score": 0.7,
                "impact_score": 0.72,
                "source_name": "Test Source",
                "title": "Harga gula naik",
            }
        ]

    monkeypatch.setattr(insight_service, "run_crawler", fake_run_crawler)
    monkeypatch.setattr(insight_service, "search_insights", fake_search_insights)
    monkeypatch.setattr(
        insight_service,
        "_safe_price_movement",
        lambda keyword, period_days: PriceMovementSummary(product=keyword, period_days=period_days),
    )
    monkeypatch.setattr(
        insight_service,
        "_safe_availability_summary",
        lambda keyword, period_days: AvailabilitySummary(product=keyword, period_days=period_days),
    )

    message = insight_service.product_deep_analysis_message("gula", polish=False)

    assert calls == ["crawl", "query"]
    assert "Brief Keputusan Bisnis Sorota" in message
