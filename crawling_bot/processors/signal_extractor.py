from __future__ import annotations

import re
from typing import Dict, Iterable, List

from crawling_bot.processors.reason_extractor import extract_evidence_text, extract_reason
from crawling_bot.schemas.entity_schema import EntityItem
from crawling_bot.schemas.signal_schema import ExtractedSignal


SIGNAL_RULES: dict[str, list[str]] = {
    "price_increase": [
        "harga naik",
        "kenaikan harga",
        "harga melonjak",
        "semakin mahal",
        "inflasi",
        "biaya bahan baku naik",
    ],
    "price_decrease": [
        "harga turun",
        "penurunan harga",
        "diskon besar",
        "harga melemah",
        "deflasi",
    ],
    "shortage": [
        "langka",
        "kelangkaan",
        "stok kosong",
        "stok habis",
        "sulit ditemukan",
        "pasokan terbatas",
    ],
    "oversupply": [
        "stok melimpah",
        "kelebihan pasokan",
        "oversupply",
        "persediaan tinggi",
    ],
    "demand_increase": [
        "permintaan meningkat",
        "demand naik",
        "penjualan naik",
        "banyak dicari",
        "konsumsi meningkat",
    ],
    "demand_decrease": [
        "permintaan turun",
        "penjualan turun",
        "daya beli melemah",
        "konsumsi menurun",
    ],
    "negative_sentiment": [
        "boikot",
        "keluhan",
        "viral negatif",
        "ditarik dari peredaran",
        "protes konsumen",
        "isu keamanan produk",
    ],
    "positive_sentiment": [
        "viral",
        "banyak diminati",
        "tren positif",
        "disukai konsumen",
        "penjualan laris",
    ],
    "regulation_change": [
        "aturan baru",
        "regulasi",
        "pajak",
        "larangan",
        "pembatasan",
        "kebijakan pemerintah",
    ],
    "distribution_disruption": [
        "banjir",
        "kemacetan distribusi",
        "gangguan logistik",
        "pelabuhan terganggu",
        "pengiriman terhambat",
        "jalan putus",
    ],
}

CATEGORY_BY_SIGNAL = {
    "price_increase": "price",
    "price_decrease": "price",
    "shortage": "supply",
    "oversupply": "supply",
    "demand_increase": "demand",
    "demand_decrease": "demand",
    "negative_sentiment": "brand",
    "positive_sentiment": "brand",
    "regulation_change": "regulation",
    "distribution_disruption": "logistics",
}

EXPLANATION_BY_SIGNAL = {
    "price_increase": "This may require distributor price monitoring and margin adjustment planning.",
    "price_decrease": "This may affect promo planning, inventory valuation, and competitive pricing.",
    "shortage": "This may affect product availability and buffer stock planning.",
    "oversupply": "This may create promo or inventory rotation opportunities.",
    "demand_increase": "This may require inventory allocation and supplier availability checks.",
    "demand_decrease": "This may require tighter purchasing and inventory rotation controls.",
    "negative_sentiment": "This may affect brand demand and retailer sell-through.",
    "positive_sentiment": "This may create near-term demand opportunities.",
    "regulation_change": "This may affect procurement, pricing, compliance, or distribution rules.",
    "distribution_disruption": "This may require route monitoring and alternative supply planning.",
}

HIGH_IMPACT_SIGNALS = {"shortage", "price_increase", "distribution_disruption", "regulation_change"}


def _first_entity(entities: Dict[str, List[EntityItem]], entity_type: str) -> str | None:
    values = entities.get(entity_type, [])
    return values[0].name if values else None


def _matching_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    lowered = text.lower()
    matches = [keyword for keyword in keywords if keyword.lower() in lowered]
    if "harga naik" in keywords and re.search(r"\bharga\b.{0,60}\bnaik\b", lowered):
        matches.append("harga naik")
    if "harga turun" in keywords and re.search(r"\bharga\b.{0,60}\bturun\b", lowered):
        matches.append("harga turun")
    return sorted(set(matches))


def _severity(signal_type: str, matches: list[str], evidence: str | None) -> int:
    severity = 1 + min(len(matches), 3)
    if signal_type in HIGH_IMPACT_SIGNALS:
        severity += 1
    if evidence:
        lowered = evidence.lower()
        if any(term in lowered for term in ["melonjak", "darurat", "besar", "terbatas", "terhambat"]):
            severity += 1
    return max(1, min(severity, 5))


def _confidence(matches: list[str], evidence: str | None, entities: Dict[str, List[EntityItem]]) -> float:
    entity_count = sum(len(items) for items in entities.values())
    score = 0.45 + min(len(matches) * 0.1, 0.25)
    if evidence:
        score += 0.15
    if entity_count:
        score += min(entity_count * 0.03, 0.15)
    return round(min(score, 0.95), 4)


def extract_signals(title: str, content: str, entities: Dict[str, List[EntityItem]]) -> list[ExtractedSignal]:
    text = f"{title} {content}"
    extracted: list[ExtractedSignal] = []

    for signal_type, keywords in SIGNAL_RULES.items():
        matches = _matching_keywords(text, keywords)
        if not matches:
            continue

        evidence = extract_evidence_text(content, matches)
        reason = extract_reason(signal_type, content, evidence)
        extracted.append(
            ExtractedSignal(
                signal_type=signal_type,
                product=_first_entity(entities, "product"),
                company=_first_entity(entities, "company"),
                location=_first_entity(entities, "location"),
                severity=_severity(signal_type, matches, evidence),
                confidence_score=_confidence(matches, evidence, entities),
                reason=reason,
                evidence_text=evidence,
                explanation=EXPLANATION_BY_SIGNAL.get(signal_type),
            )
        )

    return extracted


def infer_category(signals: list[ExtractedSignal]) -> str | None:
    if not signals:
        return None
    return CATEGORY_BY_SIGNAL.get(signals[0].signal_type)
