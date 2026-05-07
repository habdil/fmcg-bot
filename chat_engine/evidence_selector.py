from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crawling_bot.config import settings


class EvidenceSelector:
    def __init__(self, limit: int | None = None) -> None:
        self.limit = limit or settings.ai_max_evidence_items

    def select(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        ranked: list[dict[str, Any]] = []
        for row in sorted(rows, key=_score_row, reverse=True):
            key = str(row.get("signal_id") or row.get("article_id") or row.get("article_url") or id(row))
            if key in seen:
                continue
            ranked.append(row)
            seen.add(key)
            if len(ranked) >= self.limit:
                break
        return ranked

    def select_latest(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        ranked: list[dict[str, Any]] = []
        for row in sorted(rows, key=_row_datetime, reverse=True):
            key = str(row.get("article_id") or row.get("article_url") or row.get("signal_id") or id(row))
            if key in seen:
                continue
            ranked.append(row)
            seen.add(key)
            if len(ranked) >= self.limit:
                break
        return ranked


def _score_row(row: dict[str, Any]) -> float:
    impact = float(row.get("impact_score") or 0)
    confidence = float(row.get("confidence_score") or 0)
    severity = float(row.get("severity") or 0) / 5
    freshness = _freshness_component(row.get("published_at") or row.get("created_at") or row.get("crawled_at"))
    return 0.35 * impact + 0.25 * confidence + 0.25 * severity + 0.15 * freshness


def _row_datetime(row: dict[str, Any]) -> datetime:
    for key in ["published_at", "created_at", "crawled_at"]:
        value = row.get(key)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _freshness_component(value: Any) -> float:
    if not isinstance(value, datetime):
        return 0.4
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    age_hours = max((datetime.now(timezone.utc) - value).total_seconds() / 3600, 0)
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.8
    if age_hours <= 168:
        return 0.6
    return 0.3
