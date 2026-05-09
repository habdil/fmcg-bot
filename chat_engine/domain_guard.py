from __future__ import annotations

import logging
import re

from chat_engine.ai.base import AIProvider
from chat_engine.ai.router import AIRouter
from chat_engine.schemas import BusinessGuardResult, UserContext

logger = logging.getLogger(__name__)

BUSINESS_TERMS = [
    "bisnis",
    "usaha",
    "umkm",
    "dagang",
    "harga",
    "harga jual",
    "hpp",
    "margin",
    "markup",
    "laba",
    "profit",
    "omzet",
    "stok",
    "stock",
    "restock",
    "pasokan",
    "supply",
    "demand",
    "permintaan",
    "distribusi",
    "logistik",
    "supplier",
    "grosir",
    "retail",
    "toko",
    "warung",
    "market",
    "pasar",
    "produk",
    "kompetitor",
    "pesaing",
    "customer",
    "pelanggan",
    "kuliner",
    "laundry",
    "fashion",
    "coffee shop",
    "reseller",
    "kemasan",
    "komoditas",
    "inflasi",
    "daya beli",
    "regulasi",
    "aturan",
    "pangan",
    "sembako",
    "minyak goreng",
    "gula",
    "beras",
    "susu",
    "mie",
    "deterjen",
    "sabun",
    "indogrosir",
    "alfamart",
    "indomaret",
    "harga supplier",
]

NEWS_TERMS = [
    "berita",
    "news",
    "headline",
    "headlines",
    "kabar",
]

LATEST_TERMS = [
    "terbaru",
    "hari ini",
    "sekarang",
    "latest",
    "terkini",
]

NON_BUSINESS_PATTERNS = [
    r"\bpuisi\b",
    r"\bpantun\b",
    r"\bfilm\b",
    r"\blagu\b",
    r"\bgame\b",
    r"\bbola\b",
    r"\bsepak bola\b",
    r"\bolahraga\b",
    r"\bartis\b",
    r"\bcerita lucu\b",
    r"\bpacar artis\b",
]

REFUSAL_MESSAGE = (
    "Maaf, saya hanya bisa membantu pertanyaan terkait bisnis UMKM, harga, margin, "
    "HPP, supplier, kompetitor, stok, demand, supply, pasar, dan keputusan operasional."
)


class BusinessDomainGuard:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or AIRouter().guard_provider()

    def check(self, message: str, user_context: UserContext | None = None) -> BusinessGuardResult:
        fallback = fallback_guard(message)
        if fallback.is_business_related and fallback.category in {"business", "business_news"}:
            return fallback
        if not self.provider.is_configured:
            return fallback

        prompt = (
            "You are a strict domain guard for Sorota, an Indonesian MSME business decision assistant.\n"
            "Return whether the user message is related to MSME business, pricing, margin, COGS/HPP, "
            "retail, distribution, supplier search, stock, supply chain, demand, market intelligence, "
            "competitors, regulation, commodities, operational decisions, or business news.\n"
            "If the user asks generic 'berita terbaru', 'headline terbaru', or 'latest news' without "
            "another topic, treat it as a request for business news because this bot's default domain "
            "is business intelligence.\n"
            "Do not answer the user question.\n"
            "If unrelated, set is_business_related=false.\n\n"
            f"User profile: {user_context}\n"
            f"Message: {message}"
        )
        try:
            result = self.provider.generate_json(prompt, BusinessGuardResult)
            if not result.normalized_question:
                result.normalized_question = message.strip()
            if not result.is_business_related and not result.refusal_reason:
                result.refusal_reason = REFUSAL_MESSAGE
            return result
        except Exception as exc:  # pragma: no cover - provider fallback
            logger.warning("Business guard AI failed, using fallback: %s", exc)
            return fallback


def fallback_guard(message: str) -> BusinessGuardResult:
    normalized = " ".join((message or "").strip().split())
    lowered = normalized.lower()
    if not normalized:
        return BusinessGuardResult(
            is_business_related=False,
            category="unrelated",
            confidence="high",
            refusal_reason=REFUSAL_MESSAGE,
            normalized_question="",
        )
    if any(re.search(pattern, lowered) for pattern in NON_BUSINESS_PATTERNS):
        return BusinessGuardResult(
            is_business_related=False,
            category="unrelated",
            confidence="high",
            refusal_reason=REFUSAL_MESSAGE,
            normalized_question=normalized,
        )
    hits = [term for term in BUSINESS_TERMS if term in lowered]
    if hits:
        return BusinessGuardResult(
            is_business_related=True,
            category="business",
            confidence="high" if len(hits) >= 2 else "medium",
            normalized_question=normalized,
        )
    if _looks_like_news_request(lowered):
        return BusinessGuardResult(
            is_business_related=True,
            category="business_news",
            confidence="medium",
            normalized_question=normalized,
        )
    return BusinessGuardResult(
        is_business_related=False,
        category="unrelated",
        confidence="medium",
        refusal_reason=REFUSAL_MESSAGE,
        normalized_question=normalized,
    )


def looks_like_business_message(message: str) -> bool:
    return fallback_guard(message).is_business_related


def _looks_like_news_request(lowered: str) -> bool:
    has_news_term = any(term in lowered for term in NEWS_TERMS)
    has_latest_term = any(term in lowered for term in LATEST_TERMS)
    return has_news_term or ("terbaru" in lowered and "apa" in lowered) or ("update" in lowered and has_latest_term)
