from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from crawling_bot.config import settings
from crawling_bot.processors.cleaner import clean_html, normalize_whitespace


@dataclass(frozen=True)
class ArticleDetail:
    url: str
    title: str | None
    raw_html: str
    raw_text: str
    published_at: Optional[datetime]


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


def _extract_title(soup: BeautifulSoup) -> str | None:
    for selector in [
        ("meta", {"property": "og:title"}),
        ("meta", {"name": "twitter:title"}),
    ]:
        tag = soup.find(*selector)
        if tag and tag.get("content"):
            return normalize_whitespace(tag["content"])
    if soup.title and soup.title.string:
        return normalize_whitespace(soup.title.string)
    h1 = soup.find("h1")
    if h1:
        return normalize_whitespace(h1.get_text(" "))
    return None


def _extract_published_at(soup: BeautifulSoup) -> datetime | None:
    meta_keys = [
        ("property", "article:published_time"),
        ("name", "pubdate"),
        ("name", "publishdate"),
        ("name", "date"),
        ("name", "DC.date.issued"),
    ]
    for attr, value in meta_keys:
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            parsed = _parse_datetime(tag["content"])
            if parsed:
                return parsed
    time_tag = soup.find("time")
    if time_tag:
        parsed = _parse_datetime(time_tag.get("datetime") or time_tag.get_text(" "))
        if parsed:
            return parsed
    return None


def fetch_article(url: str) -> ArticleDetail:
    headers = {"User-Agent": settings.crawler_user_agent}
    response = httpx.get(
        url,
        headers=headers,
        timeout=settings.crawler_timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "lxml")
    return ArticleDetail(
        url=str(response.url),
        title=_extract_title(soup),
        raw_html=html,
        raw_text=clean_html(html),
        published_at=_extract_published_at(soup),
    )
