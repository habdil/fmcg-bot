from __future__ import annotations

import json
import logging
import re
from typing import Any

from crawling_bot.config import settings
from crawling_bot.processors.cleaner import normalize_whitespace
from crawling_bot.schemas.analyst_schema import AnalystQuery

logger = logging.getLogger(__name__)

PACK_SIZE_RE = re.compile(r"\b\d+(?:[,.]\d+)?\s?(?:liter|litre|ltr|l|ml|kg|gram|gr|g)\b", re.IGNORECASE)

PRODUCT_SYNONYMS = {
    "minyak": "minyak goreng",
    "minyak goreng": "minyak goreng",
    "gula": "gula",
    "beras": "beras",
    "susu": "susu",
    "mie": "mie instan",
    "mie instan": "mie instan",
    "sabun": "sabun",
    "deterjen": "deterjen",
    "tepung": "tepung",
    "kopi": "kopi",
    "air mineral": "air mineral",
}

LOCATIONS = [
    "indonesia",
    "jakarta",
    "jawa barat",
    "jawa tengah",
    "jawa timur",
    "bali",
    "sumatera",
    "kalimantan",
    "sulawesi",
    "papua",
]


class AnalystQueryParser:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model

    def parse(self, question: str) -> AnalystQuery:
        fallback = self._fallback(question)
        if not self.api_key:
            return fallback

        try:
            from google import genai
            from google.genai import types

            prompt = (
                "Parse this Indonesian/English FMCG business question into structured fields. "
                "Return only the schema. Normalize product names for FMCG distribution. "
                "If user says 'minyak' in FMCG context, normalize to 'minyak goreng'. "
                "Do not invent exact pack size if absent.\n\n"
                f"Question: {question}"
            )
            with genai.Client(api_key=self.api_key) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AnalystQuery,
                    ),
                )
            parsed = response.parsed if getattr(response, "parsed", None) else json.loads(response.text)
            query = AnalystQuery.model_validate(parsed)
            if not query.search_terms:
                query.search_terms = fallback.search_terms
            return query
        except Exception as exc:  # pragma: no cover - API fallback path
            logger.warning("Gemini query parsing failed, using fallback parser: %s", exc)
            return fallback

    def _fallback(self, question: str) -> AnalystQuery:
        normalized_question = normalize_whitespace(question).lower()
        pack_size_match = PACK_SIZE_RE.search(normalized_question)
        pack_size = pack_size_match.group(0).replace(",", ".") if pack_size_match else None

        product = None
        for phrase, normalized in PRODUCT_SYNONYMS.items():
            if phrase in normalized_question:
                product = normalized
                break

        location = None
        for item in LOCATIONS:
            if item in normalized_question:
                location = item
                break

        output_format = "report"
        if any(term in normalized_question for term in ["berita", "news"]):
            output_format = "news"
        elif any(term in normalized_question for term in ["ringkas", "singkat", "brief"]):
            output_format = "brief"

        intent = "analysis"
        if any(term in normalized_question for term in ["prediksi", "forecast", "outlook"]):
            intent = "forecast"
        elif "harga" in normalized_question:
            intent = "price"
        elif any(term in normalized_question for term in ["trend", "tren"]):
            intent = "trend"
        elif any(term in normalized_question for term in ["stok", "pasokan", "supply"]):
            intent = "supply"

        keyword = product or normalize_whitespace(question)
        terms = [keyword]
        if product and product != "minyak goreng" and "minyak" in product:
            terms.append("minyak")
        if product == "minyak goreng":
            terms.extend(["minyak", "minyak goreng"])
        if pack_size:
            terms.append(pack_size)
            terms.append(f"{keyword} {pack_size}")
        if location:
            terms.append(location)

        deduped_terms = list(dict.fromkeys(term for term in terms if term))
        return AnalystQuery(
            original_question=question,
            normalized_keyword=keyword,
            product=product,
            pack_size=pack_size,
            location=location,
            intent=intent,  # type: ignore[arg-type]
            output_format=output_format,  # type: ignore[arg-type]
            search_terms=deduped_terms,
        )
