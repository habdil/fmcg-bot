from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx
from dateutil import parser as date_parser

from crawling_bot.config import settings


@dataclass(frozen=True)
class RssEntry:
    title: str
    url: str
    published_at: Optional[datetime]
    summary: str | None = None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_rss_entries(feed_url: str, limit: int | None = None) -> list[RssEntry]:
    headers = {"User-Agent": settings.crawler_user_agent}
    response = httpx.get(
        feed_url,
        headers=headers,
        timeout=settings.crawler_timeout,
        follow_redirects=True,
    )
    response.raise_for_status()

    parsed = feedparser.parse(response.content)
    entries: list[RssEntry] = []
    for entry in parsed.entries[:limit]:
        url = getattr(entry, "link", "")
        title = getattr(entry, "title", "").strip()
        if not url or not title:
            continue
        entries.append(
            RssEntry(
                title=title,
                url=url,
                published_at=_parse_datetime(
                    getattr(entry, "published", None) or getattr(entry, "updated", None)
                ),
                summary=getattr(entry, "summary", None),
            )
        )
    return entries
