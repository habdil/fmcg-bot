from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from chat_engine.analyst_composer import AnalystComposer
from chat_engine.ai.base import NoopAIProvider
from chat_engine.domain_guard import BusinessDomainGuard, fallback_guard
from chat_engine import ChatEngine
from chat_engine.query_planner import QueryPlanner
from crawling_bot.schemas.price_schema import (
    AvailabilitySummary,
    PriceMovementSummary,
    PricePoint,
    PriceSourceReference,
)
from telegram_bot.services.memory_service import extract_style_instruction


def _engine(*, rows=None, recent_rows=None, price=None, crawl_calls=None) -> ChatEngine:
    crawl_calls = crawl_calls if crawl_calls is not None else []

    def fake_crawl(max_articles_per_source=None, source_limit=None):
        crawl_calls.append((max_articles_per_source, source_limit))
        return []

    def fake_search(terms, limit=40):
        return list(rows or [])

    def fake_recent(period_days=2, limit=80):
        return list(recent_rows or [])

    def fake_price(keyword, period_days=7):
        return price or PriceMovementSummary(product=keyword, period_days=period_days)

    def fake_availability(keyword, period_days=7):
        return AvailabilitySummary(product=keyword, period_days=period_days)

    noop = NoopAIProvider()
    return ChatEngine(
        guard=BusinessDomainGuard(provider=noop),
        planner=QueryPlanner(provider=noop),
        composer=AnalystComposer(provider=noop),
        run_crawler_func=fake_crawl,
        search_func=fake_search,
        recent_func=fake_recent,
        price_func=fake_price,
        availability_func=fake_availability,
    )


def test_chat_engine_rejects_non_business_without_crawl() -> None:
    crawl_calls: list[tuple[int | None, int | None]] = []
    engine = _engine(crawl_calls=crawl_calls)

    result = engine.handle_message("Bikinin puisi lucu dong")

    assert not result.guard.is_business_related
    assert "hanya bisa membantu pertanyaan terkait bisnis" in result.answer
    assert crawl_calls == []


def test_generic_latest_news_question_is_business_news() -> None:
    result = fallback_guard("Berita terbaru apa yahh?")

    assert result.is_business_related
    assert result.category == "business_news"


def test_extract_style_instruction_from_natural_message() -> None:
    instruction = extract_style_instruction(
        "ingat gaya jawaban: singkat, natural, tanpa kata headline, langsung ke sumber"
    )

    assert instruction == "singkat, natural, tanpa kata headline, langsung ke sumber"


def test_chat_engine_price_question_uses_price_not_found_fallback() -> None:
    engine = _engine(rows=[])

    result = engine.handle_message("Harga gula 1 kg hari ini berapa?", crawl_first=False)

    assert result.guard.is_business_related
    assert result.plan is not None
    assert result.plan.price_snapshot_needed
    assert "Aku belum menemukan harga gula 1 kg" in result.answer
    assert "quotation langsung" in result.answer
    assert "Marketplace B2B" not in result.answer


def test_chat_engine_margin_question_uses_local_calculator_without_crawl() -> None:
    crawl_calls: list[tuple[int | None, int | None]] = []
    engine = _engine(rows=[], crawl_calls=crawl_calls)

    result = engine.handle_message(
        "Kalau HPP ayam geprek Rp. 11.500 dan jual Rp. 18.000, masih aman??",
        crawl_first=True,
    )

    assert result.plan is not None
    assert result.plan.intent == "recommendation"
    assert result.plan.price_snapshot_needed is False
    assert crawl_calls == []
    assert "Margin kotornya sekitar 36,1%" in result.answer
    assert "laba kotor Rp 6.500" in result.answer


def test_chat_engine_business_answer_uses_natural_language_without_internal_terms() -> None:
    rows = [
        {
            "signal_id": "1",
            "signal_type": "price_increase",
            "product": "gula",
            "urgency": "high",
            "severity": 4,
            "confidence_score": 0.78,
            "impact_score": 0.82,
            "reason": "Harga gula naik karena pasokan terbatas.",
            "evidence_text": "Harga gula naik karena pasokan terbatas.",
            "source_name": "Test Source",
            "title": "Harga gula naik",
            "article_url": "https://example.com/gula",
            "published_at": datetime(2026, 5, 7, tzinfo=timezone.utc),
        }
    ]
    engine = _engine(rows=rows)

    result = engine.handle_message("Gula hari ini gimana buat grosir?", crawl_first=False)

    assert "tekanan harga naik" in result.answer
    assert "Sumber" in result.answer
    assert "Pasokan dan permintaan" not in result.answer
    assert "Kenapa ini penting" not in result.answer
    assert len([line for line in result.answer.splitlines() if line.strip()]) <= 5
    lowered = result.answer.lower()
    assert "signal" not in lowered
    assert "source coverage" not in lowered
    assert "evidence_text" not in lowered


def test_chat_engine_latest_news_formats_headlines_from_recent_rows() -> None:
    crawl_calls: list[tuple[int | None, int | None]] = []
    rows = [
        {
            "signal_id": "1",
            "article_id": "article-1",
            "signal_type": "price_increase",
            "product": "gula",
            "urgency": "medium",
            "severity": 3,
            "confidence_score": 0.75,
            "impact_score": 0.7,
            "reason": "Harga gula naik karena pasokan terbatas.",
            "evidence_text": "Harga gula naik karena pasokan terbatas di pasar tradisional.",
            "source_name": "Test Bisnis",
            "title": "Harga gula naik di pasar tradisional",
            "article_url": "https://example.com/gula-naik",
            "published_at": datetime(2026, 5, 7, 9, 0, tzinfo=timezone.utc),
        }
    ]
    engine = _engine(recent_rows=rows, crawl_calls=crawl_calls)

    result = engine.handle_message("Berita terbaru apa yahh?", crawl_first=True)

    assert result.guard.is_business_related
    assert result.plan is not None
    assert result.plan.intent == "daily_brief"
    assert result.plan.search_terms == []
    assert crawl_calls == [(1, 4)]
    assert "Update terbaru bisnis UMKM" in result.answer
    assert "Headline" not in result.answer
    assert "Harga gula naik di pasar tradisional" in result.answer
    assert "Harga gula naik karena pasokan terbatas." in result.answer
    assert "(Test Bisnis)" in result.answer


def test_chat_engine_price_answer_includes_observed_range_when_available() -> None:
    price = PriceMovementSummary(
        product="gula",
        period_days=7,
        price_points=[
            PricePoint(date=datetime(2026, 5, 7).date(), average_price=Decimal("16900")),
            PricePoint(date=datetime(2026, 5, 8).date(), average_price=Decimal("18200")),
        ],
        highest_price=Decimal("18200"),
        lowest_price=Decimal("16900"),
        average_price=Decimal("17550"),
        snapshot_count=2,
        latest_observed_at=datetime(2026, 5, 8, 8, 10, tzinfo=timezone.utc),
        source_references=[
            PriceSourceReference(
                source_name="Katalog Supplier",
                reference_label="Katalog Supplier - Gula",
                reference_url="https://example.com/gula",
                observed_at=datetime(2026, 5, 8, 8, 10, tzinfo=timezone.utc),
            )
        ],
    )
    engine = _engine(price=price)

    result = engine.handle_message("Harga gula hari ini?", crawl_first=False)

    assert "data harga pembanding" in result.answer
    assert "Rp 16.900" in result.answer
    assert "Rp 18.200" in result.answer
    assert "minta harga final ke supplier" in result.answer
    assert "https://example.com/gula" not in result.answer
