from __future__ import annotations

import re

from crawling_bot.processors.cleaner import normalize_whitespace


FALLBACK_REASON = "The article indicates this signal, but the direct cause is not clearly stated."

CAUSE_MARKERS = [
    "karena",
    "akibat",
    "disebabkan",
    "dipicu",
    "terdorong",
    "seiring",
    "imbas",
]


def split_sentences(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", normalized)
        if sentence.strip()
    ]


def extract_evidence_text(content: str, keywords: list[str]) -> str | None:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for sentence in split_sentences(content):
        lowered_sentence = sentence.lower()
        if any(keyword in lowered_sentence for keyword in lowered_keywords):
            return sentence[:500]
        if "harga naik" in lowered_keywords and re.search(r"\bharga\b.{0,60}\bnaik\b", lowered_sentence):
            return sentence[:500]
        if "harga turun" in lowered_keywords and re.search(r"\bharga\b.{0,60}\bturun\b", lowered_sentence):
            return sentence[:500]
    return None


def extract_reason(signal_type: str, content: str, evidence_text: str | None = None) -> str:
    search_space = " ".join([evidence_text or "", content or ""])
    for sentence in split_sentences(search_space):
        lowered = sentence.lower()
        if any(marker in lowered for marker in CAUSE_MARKERS):
            return sentence[:500]
    return FALLBACK_REASON
