from __future__ import annotations

from datetime import datetime, timezone

from crawling_bot.schemas.signal_schema import ExtractedSignal


def clamp(value: float, minimum: float = 0, maximum: float = 1) -> float:
    return max(minimum, min(maximum, value))


def signal_severity_score(severity: int) -> float:
    return clamp(severity / 5)


def freshness_score(published_at: datetime | None, now: datetime | None = None) -> float:
    if published_at is None:
        return 0.5
    current = now or datetime.now(timezone.utc)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = max((current - published_at).total_seconds() / 3600, 0)
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.8
    if age_hours <= 168:
        return 0.6
    return 0.3


def impact_score(
    source_credibility_score: float,
    severity: int,
    relevance_score: float,
    published_at: datetime | None,
    now: datetime | None = None,
) -> float:
    score = (
        0.35 * clamp(source_credibility_score)
        + 0.25 * signal_severity_score(severity)
        + 0.20 * clamp(relevance_score)
        + 0.20 * freshness_score(published_at, now)
    )
    return round(clamp(score), 4)


def confidence_score(
    source_credibility_score: float,
    clean_content: str,
    signals: list[ExtractedSignal],
    reason: str | None,
    evidence_text: str | None,
) -> float:
    completeness = 1.0 if len(clean_content) >= 700 else 0.65 if len(clean_content) >= 250 else 0.35
    signal_support = min(len(signals) * 0.15, 0.3)
    evidence_support = 0.15 if evidence_text else 0
    reason_support = 0.15 if reason and "not clearly stated" not in reason.lower() else 0.05
    score = (
        0.30 * clamp(source_credibility_score)
        + 0.25 * completeness
        + signal_support
        + evidence_support
        + reason_support
    )
    return round(clamp(score), 4)


def urgency(impact: float, signals: list[ExtractedSignal]) -> str:
    if impact >= 0.75:
        return "high"
    for signal in signals:
        if signal.signal_type in {"shortage", "price_increase", "distribution_disruption"} and signal.severity >= 3:
            return "high"
    if impact >= 0.45:
        return "medium"
    return "low"
