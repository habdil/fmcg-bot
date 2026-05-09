from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from chat_engine.ai.base import AIProvider, NoopAIProvider
from chat_engine.ai.router import AIRouter

logger = logging.getLogger(__name__)


class GeminiReportPolish(BaseModel):
    final_text: str
    headline: str = ""
    analyst_summary: str = ""
    limitations: list[str] = Field(default_factory=list)


class GeminiReportPolisher:
    """Report polisher routed through the active AI gateway."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        provider: AIProvider | None = None,
    ) -> None:
        # Passing api_key="" is supported for deterministic fallback tests.
        self.provider = provider or (NoopAIProvider() if api_key == "" else AIRouter().composer_provider())

    def polish(self, structured_markdown: str) -> GeminiReportPolish:
        fallback = GeminiReportPolish(
            final_text=structured_markdown,
            headline=_first_non_empty_line(structured_markdown),
            analyst_summary="Rule-based structured response.",
            limitations=[],
        )

        prompt = (
            "You are a business intelligence writing assistant for Indonesian UMKM owners.\n"
            "Rewrite the structured analysis into clear professional Bahasa Indonesia.\n"
            "Do not add new facts.\n"
            "Do not invent prices, sources, or causes.\n"
            "If data is missing, keep the limitation statement.\n"
            "Preserve numbers, dates, percentages, source counts, and confidence scores exactly.\n\n"
            "Structured analysis:\n"
            f"{structured_markdown}"
        )

        if self.provider.is_configured:
            try:
                return self.provider.generate_json(prompt, GeminiReportPolish)
            except Exception as exc:
                logger.warning("AI report polishing failed, using structured response: %s", exc)

        return fallback


def _first_non_empty_line(value: str) -> str:
    for line in value.splitlines():
        if line.strip():
            return line.strip()
    return ""
