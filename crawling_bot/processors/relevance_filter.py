from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


BUSINESS_KEYWORDS = [
    "umkm",
    "bisnis",
    "usaha",
    "harga",
    "harga jual",
    "hpp",
    "margin",
    "markup",
    "supplier",
    "kompetitor",
    "pesaing",
    "restock",
    "produk",
    "kuliner",
    "warung",
    "toko kelontong",
    "coffee shop",
    "laundry",
    "fashion",
    "reseller",
    "kemasan",
    "barang konsumsi",
    "makanan",
    "minuman",
    "ayam",
    "telur",
    "kopi",
    "cabe",
    "bawang",
    "sembako",
    "minyak goreng",
    "gula",
    "beras",
    "tepung",
    "susu",
    "mie instan",
    "sabun",
    "deterjen",
    "personal care",
    "household product",
    "retail",
    "minimarket",
    "supermarket",
    "distributor",
    "grosir",
    "stok",
    "pasokan",
    "distribusi",
    "logistik",
    "kelangkaan",
    "harga naik",
    "harga turun",
    "promo",
    "diskon",
    "inflasi",
    "daya beli",
    "konsumsi rumah tangga",
]

BUSINESS_ENTITIES = [
    "klikindogrosir",
    "tokopedia",
    "shopee",
    "indogrosir",
    "pasar induk",
    "pihps",
    "unilever",
    "indofood",
    "mayora",
    "wings",
    "nestle",
    "garudafood",
    "wilmar",
    "sinar mas",
    "alfamart",
    "indomaret",
    "hypermart",
    "aqua",
    "danone",
    "p&g",
    "frisian flag",
    "ajinomoto",
    "orang tua",
    "kapal api",
    "abc",
    "sasa",
    "sosro",
]


@dataclass(frozen=True)
class RelevanceResult:
    is_relevant: bool
    score: float
    keyword_hits: list[str]
    entity_hits: list[str]


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower())
    return re.search(rf"(?<!\w){escaped}(?!\w)", text.lower()) is not None


def find_hits(text: str, phrases: Iterable[str]) -> list[str]:
    return sorted({phrase for phrase in phrases if _contains_phrase(text, phrase)})


def score_relevance(title: str, content: str) -> RelevanceResult:
    title_hits = find_hits(title, BUSINESS_KEYWORDS)
    content_hits = find_hits(content, BUSINESS_KEYWORDS)
    entity_hits = find_hits(f"{title} {content}", BUSINESS_ENTITIES)

    keyword_hits = sorted(set(title_hits + content_hits))
    title_component = min(len(title_hits) * 0.18, 0.36)
    content_component = min(len(content_hits) * 0.07, 0.35)
    entity_component = min(len(entity_hits) * 0.08, 0.24)
    base_component = 0.05 if keyword_hits or entity_hits else 0

    score = min(title_component + content_component + entity_component + base_component, 1.0)
    return RelevanceResult(
        is_relevant=score >= 0.18,
        score=round(score, 4),
        keyword_hits=keyword_hits,
        entity_hits=entity_hits,
    )


def is_relevant(title: str, content: str) -> bool:
    return score_relevance(title, content).is_relevant
