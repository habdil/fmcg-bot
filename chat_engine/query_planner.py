from __future__ import annotations

import logging
import re

from chat_engine.ai.base import AIProvider
from chat_engine.ai.router import AIRouter
from chat_engine.schemas import ChatQueryPlan, UserContext
from crawling_bot.ai.query_parser import AnalystQueryParser

logger = logging.getLogger(__name__)

PRICE_TERMS = ["harga", "price", "berapa", "kisaran", "rp", "rupiah"]
CALCULATION_TERMS = ["hpp", "modal", "margin", "markup", "laba", "untung", "profit", "harga jual"]
SUPPLY_TERMS = ["stok", "stock", "pasokan", "supply", "kelangkaan", "langka"]
DEMAND_TERMS = ["demand", "permintaan", "ramai", "laris", "hype"]
REGULATION_TERMS = ["aturan", "regulasi", "kebijakan", "pemerintah", "larangan", "pajak"]
NEWS_TERMS = ["berita", "news", "headline", "headlines", "kabar", "update"]
LATEST_TERMS = ["terbaru", "hari ini", "sekarang", "latest", "terkini"]


class QueryPlanner:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or AIRouter().planner_provider()
        self.fallback_parser = AnalystQueryParser(api_key="")

    def plan(self, question: str, user_context: UserContext | None = None) -> ChatQueryPlan:
        fallback = self._fallback(question, user_context)
        # Fast path: skip AI call untuk query yang intentnya sudah jelas
        # dari keyword matching → hemat 1-3 detik per pesan
        if _is_latest_news_query(question) or _has_clear_intent(question):
            return fallback
        if not self.provider.is_configured:
            return fallback

        prompt = (
            "Parse this Indonesian business question into a crawl and response plan.\n"
            "Do not answer the question. Extract product, pack size, location, intent, "
            "search terms, and whether price data is needed.\n\n"
            f"User profile: {user_context}\n"
            f"Question: {question}"
        )
        try:
            result = self.provider.generate_json(prompt, ChatQueryPlan)
            if not result.search_terms:
                result.search_terms = fallback.search_terms
            if not result.normalized_question:
                result.normalized_question = fallback.normalized_question
            if _is_latest_news_query(question):
                result.intent = "daily_brief"
                result.crawl_needed = True
                if _is_generic_news_plan(fallback):
                    result.normalized_question = fallback.normalized_question
                    result.product = None
                    result.pack_size = None
                    result.search_terms = []
            return result
        except Exception as exc:  # pragma: no cover - provider fallback
            logger.warning("Query planner AI failed, using fallback: %s", exc)
            return fallback

    def _fallback(self, question: str, user_context: UserContext | None = None) -> ChatQueryPlan:
        parsed = self.fallback_parser.parse(question)
        lowered = question.lower()
        intent = _map_intent(parsed.intent)
        is_business_calculation = _looks_like_business_calculation(lowered)
        if is_business_calculation:
            intent = "recommendation"
        elif any(term in lowered for term in PRICE_TERMS):
            intent = "price"
        elif any(term in lowered for term in SUPPLY_TERMS):
            intent = "supply"
        elif any(term in lowered for term in DEMAND_TERMS):
            intent = "demand"
        elif any(term in lowered for term in REGULATION_TERMS):
            intent = "regulation"
        elif "banding" in lowered or " vs " in lowered or "compare" in lowered:
            intent = "comparison"
        elif _is_latest_news_query(lowered):
            intent = "daily_brief"

        terms = list(parsed.search_terms)
        if user_context:
            if user_context.location and user_context.location not in terms:
                terms.append(user_context.location)
            for product in user_context.product_focus:
                if product and product not in terms:
                    terms.append(product)

        if _is_latest_news_query(lowered) and not parsed.product and not parsed.location:
            terms = []
        normalized_question = parsed.normalized_keyword or question
        if _is_latest_news_query(lowered) and not parsed.product:
            normalized_question = "berita bisnis terbaru"

        return ChatQueryPlan(
            original_question=question,
            normalized_question=normalized_question,
            intent=intent,
            product=parsed.product,
            pack_size=parsed.pack_size,
            location=parsed.location or (user_context.location if user_context else None),
            search_terms=list(dict.fromkeys(term for term in terms if term)),
            crawl_needed=not is_business_calculation,
            price_snapshot_needed=intent == "price" and not is_business_calculation,
            response_style=(user_context.response_style if user_context and user_context.response_style in {"short", "normal", "detailed", "ba_report"} else "normal"),  # type: ignore[arg-type]
        )


def _map_intent(value: str) -> str:
    if value == "trend":
        return "daily_brief"
    if value == "forecast":
        return "recommendation"
    if value in {"analysis", "price", "supply", "demand", "sentiment"}:
        return value
    return "analysis"


def _has_clear_intent(question: str) -> bool:
    """Return True jika intent sudah jelas dari keyword — tidak perlu AI parse."""
    lowered = question.lower()
    has_price = any(t in lowered for t in PRICE_TERMS)
    has_calculation = _looks_like_business_calculation(lowered)
    has_supply = any(t in lowered for t in SUPPLY_TERMS)
    has_demand = any(t in lowered for t in DEMAND_TERMS)
    has_regulation = any(t in lowered for t in REGULATION_TERMS)
    return has_calculation or has_price or has_supply or has_demand or has_regulation


def _looks_like_business_calculation(lowered: str) -> bool:
    has_calc_term = any(term in lowered for term in CALCULATION_TERMS)
    money_like_count = len(re.findall(r"(?:rp\.?\s*)?\d[\d.,]{2,}", lowered))
    return has_calc_term and money_like_count >= 2


def _is_latest_news_query(value: str) -> bool:
    lowered = value.lower()
    has_news_term = any(term in lowered for term in NEWS_TERMS)
    has_latest_term = any(term in lowered for term in LATEST_TERMS)
    return has_news_term and (has_latest_term or "berita" in lowered or "news" in lowered)


def _is_generic_news_plan(plan: ChatQueryPlan) -> bool:
    return plan.intent == "daily_brief" and not plan.product and not plan.pack_size and not plan.location
