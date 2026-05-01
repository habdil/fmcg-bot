from __future__ import annotations

import hashlib
import re
from html import unescape

from bs4 import BeautifulSoup


WHITESPACE_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(text or "")).strip()


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript", "iframe"]):
        tag.decompose()
    return normalize_whitespace(soup.get_text(" "))


def generate_content_hash(text: str) -> str:
    normalized = normalize_whitespace(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fallback_summary(title: str, content: str, max_chars: int = 420) -> str:
    body = normalize_whitespace(content)
    if len(body) <= max_chars:
        return body or title
    return f"{body[:max_chars].rsplit(' ', 1)[0]}..."
