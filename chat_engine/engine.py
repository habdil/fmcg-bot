from __future__ import annotations

import logging
from typing import Any, Callable

from chat_engine.analyst_composer import AnalystComposer
from chat_engine.domain_guard import BusinessDomainGuard
from chat_engine.evidence_selector import EvidenceSelector
from chat_engine.query_planner import QueryPlanner
from chat_engine.schemas import ChatEngineResult, UserContext
from crawling_bot.main import run_crawler
from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary
from crawling_bot.services.price_analysis_service import get_availability_summary, get_price_movement
from crawling_bot.services.signal_service import recent_signal_rows, search_insights_for_terms

logger = logging.getLogger(__name__)


class ChatEngine:
    def __init__(
        self,
        *,
        guard: BusinessDomainGuard | None = None,
        planner: QueryPlanner | None = None,
        selector: EvidenceSelector | None = None,
        composer: AnalystComposer | None = None,
        run_crawler_func: Callable[..., list[Any]] = run_crawler,
        search_func: Callable[..., list[dict[str, Any]]] = search_insights_for_terms,
        recent_func: Callable[..., list[dict[str, Any]]] = recent_signal_rows,
        price_func: Callable[..., PriceMovementSummary] = get_price_movement,
        availability_func: Callable[..., AvailabilitySummary] = get_availability_summary,
    ) -> None:
        self.guard = guard or BusinessDomainGuard()
        self.planner = planner or QueryPlanner()
        self.selector = selector or EvidenceSelector()
        self.composer = composer or AnalystComposer()
        self.run_crawler = run_crawler_func
        self.search = search_func
        self.recent = recent_func
        self.get_price = price_func
        self.get_availability = availability_func

    def handle_message(
        self,
        message: str,
        *,
        user_context: UserContext | None = None,
        crawl_first: bool = True,
        max_sources: int = 8,
        max_articles_per_source: int = 2,
    ) -> ChatEngineResult:
        guard_result = self.guard.check(message, user_context)
        if not guard_result.is_business_related:
            return ChatEngineResult(answer=guard_result.refusal_reason or "", guard=guard_result)

        plan = self.planner.plan(guard_result.normalized_question or message, user_context)
        crawl_stats: list[Any] = []
        if crawl_first and plan.crawl_needed:
            crawl_max_sources = max_sources
            crawl_max_articles = max_articles_per_source
            if plan.intent == "daily_brief" and not plan.search_terms:
                crawl_max_sources = min(max_sources, 5)
                crawl_max_articles = min(max_articles_per_source, 1)
            try:
                crawl_stats = self.run_crawler(
                    max_articles_per_source=crawl_max_articles,
                    source_limit=crawl_max_sources,
                )
            except Exception as exc:
                logger.warning("ChatEngine crawl failed, continuing with stored evidence: %s", exc)

        is_latest_news = plan.intent == "daily_brief"
        rows = self._recent_rows() if is_latest_news and not plan.search_terms else self._search_rows(plan.search_terms)
        selected_rows = self.selector.select_latest(rows) if is_latest_news else self.selector.select(rows)
        price_summary = self._price_summary(plan.normalized_question)
        availability_summary = self._availability_summary(plan.normalized_question)
        answer = self.composer.compose(
            plan=plan,
            rows=selected_rows,
            price_summary=price_summary,
            availability_summary=availability_summary,
            user_context=user_context,
        )
        return ChatEngineResult(
            answer=answer,
            guard=guard_result,
            plan=plan,
            crawl_stats=crawl_stats,
            evidence_count=len(selected_rows),
            used_price_data=price_summary.snapshot_count > 0,
        )

    def _search_rows(self, search_terms: list[str]) -> list[dict[str, Any]]:
        if not search_terms:
            return []
        try:
            return self.search(search_terms, limit=40)
        except Exception as exc:
            logger.warning("ChatEngine evidence search failed: %s", exc)
            return []

    def _recent_rows(self) -> list[dict[str, Any]]:
        try:
            return self.recent(period_days=2, limit=80)
        except Exception as exc:
            logger.warning("ChatEngine recent news lookup failed: %s", exc)
            return []

    def _price_summary(self, keyword: str) -> PriceMovementSummary:
        try:
            return self.get_price(keyword, period_days=7)
        except Exception as exc:
            logger.warning("ChatEngine price lookup failed: %s", exc)
            return PriceMovementSummary(product=keyword, period_days=7)

    def _availability_summary(self, keyword: str) -> AvailabilitySummary:
        try:
            return self.get_availability(keyword, period_days=7)
        except Exception as exc:
            logger.warning("ChatEngine availability lookup failed: %s", exc)
            return AvailabilitySummary(product=keyword, period_days=7)
