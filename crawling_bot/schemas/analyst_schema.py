from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AnalystQuery(BaseModel):
    original_question: str
    normalized_keyword: str
    product: str | None = None
    pack_size: str | None = None
    location: str | None = None
    intent: Literal["analysis", "trend", "price", "supply", "demand", "sentiment", "forecast"] = "analysis"
    output_format: Literal["report", "news", "brief"] = "report"
    search_terms: list[str] = Field(default_factory=list)


class GroundedAnalystReport(BaseModel):
    title: str
    executive_summary: str
    trend_analysis: str
    price_signal: str
    supply_signal: str
    demand_signal: str
    sentiment_signal: str
    business_impact: str
    recommended_actions: list[str]
    confidence_level: Literal["low", "medium", "high"]
    limitations: list[str]
    source_notes: list[str]


def format_grounded_report(report: GroundedAnalystReport) -> str:
    actions = "\n".join(f"- {item}" for item in report.recommended_actions)
    limitations = "\n".join(f"- {item}" for item in report.limitations)
    sources = "\n".join(f"- {item}" for item in report.source_notes)
    return (
        f"{report.title}\n\n"
        f"Executive Summary:\n{report.executive_summary}\n\n"
        f"Trend:\n{report.trend_analysis}\n\n"
        f"Harga:\n{report.price_signal}\n\n"
        f"Supply/Distribusi:\n{report.supply_signal}\n\n"
        f"Demand:\n{report.demand_signal}\n\n"
        f"Sentiment:\n{report.sentiment_signal}\n\n"
        f"Business Impact:\n{report.business_impact}\n\n"
        f"Recommended Action:\n{actions}\n\n"
        f"Confidence: {report.confidence_level.upper()}\n\n"
        f"Limitasi:\n{limitations}\n\n"
        f"Sumber:\n{sources}"
    )
