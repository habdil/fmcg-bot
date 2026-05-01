from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from crawling_bot.processors.relevance_filter import FMCG_ENTITIES, find_hits
from crawling_bot.schemas.entity_schema import EntityItem


PRODUCTS = [
    "minyak goreng",
    "gula",
    "beras",
    "tepung",
    "susu",
    "mie instan",
    "sabun",
    "deterjen",
    "kopi",
    "teh",
    "air mineral",
    "personal care",
    "household product",
]

COMMODITIES = [
    "cpo",
    "crude palm oil",
    "gandum",
    "kedelai",
    "jagung",
    "beras",
    "gula",
    "minyak sawit",
]

LOCATIONS = [
    "indonesia",
    "jakarta",
    "jawa barat",
    "jawa tengah",
    "jawa timur",
    "banten",
    "sumatera",
    "kalimantan",
    "sulawesi",
    "bali",
    "ntt",
    "ntb",
    "papua",
]


def normalize_entity_name(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _items(names: list[str], entity_type: str, relevance_score: float) -> list[EntityItem]:
    return [
        EntityItem(
            name=name,
            entity_type=entity_type,
            normalized_name=normalize_entity_name(name),
            relevance_score=relevance_score,
        )
        for name in names
    ]


def extract_entities(title: str, content: str) -> Dict[str, List[EntityItem]]:
    text = f"{title} {content}"
    result: dict[str, list[EntityItem]] = defaultdict(list)
    result["product"].extend(_items(find_hits(text, PRODUCTS), "product", 0.75))
    result["company"].extend(_items(find_hits(text, FMCG_ENTITIES), "company", 0.7))
    result["brand"].extend(_items(find_hits(text, FMCG_ENTITIES), "brand", 0.65))
    result["location"].extend(_items(find_hits(text, LOCATIONS), "location", 0.65))
    result["commodity"].extend(_items(find_hits(text, COMMODITIES), "commodity", 0.7))
    return dict(result)


def flatten_entities(entities: Dict[str, List[EntityItem]]) -> list[EntityItem]:
    seen: set[tuple[str, str]] = set()
    flattened: list[EntityItem] = []
    for items in entities.values():
        for item in items:
            key = (item.normalized_name, item.entity_type)
            if key not in seen:
                flattened.append(item)
                seen.add(key)
    return flattened
