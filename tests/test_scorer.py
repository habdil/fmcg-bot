from datetime import datetime, timedelta, timezone

from crawling_bot.processors.scorer import confidence_score, freshness_score, impact_score, urgency
from crawling_bot.schemas.signal_schema import ExtractedSignal


def test_freshness_score_mapping() -> None:
    now = datetime(2026, 5, 1, tzinfo=timezone.utc)

    assert freshness_score(now - timedelta(hours=12), now) == 1.0
    assert freshness_score(now - timedelta(days=2), now) == 0.8
    assert freshness_score(now - timedelta(days=5), now) == 0.6
    assert freshness_score(now - timedelta(days=10), now) == 0.3
    assert freshness_score(None, now) == 0.5


def test_impact_and_urgency_for_shortage() -> None:
    signal = ExtractedSignal(signal_type="shortage", severity=4, evidence_text="stok kosong")
    impact = impact_score(
        source_credibility_score=0.8,
        severity=signal.severity,
        relevance_score=0.85,
        published_at=datetime.now(timezone.utc),
    )
    confidence = confidence_score(
        source_credibility_score=0.8,
        clean_content="x" * 800,
        signals=[signal],
        reason="Pasokan terbatas karena distribusi terhambat.",
        evidence_text=signal.evidence_text,
    )

    assert impact >= 0.75
    assert confidence > 0.7
    assert urgency(impact, [signal]) == "high"
