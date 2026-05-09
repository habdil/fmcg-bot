from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


class BusinessGuardResult(BaseModel):
    is_business_related: bool
    category: str = "unrelated"
    confidence: Literal["low", "medium", "high"] = "low"
    refusal_reason: str | None = None
    normalized_question: str = ""


class ChatQueryPlan(BaseModel):
    original_question: str
    normalized_question: str
    intent: Literal[
        "analysis",
        "price",
        "supply",
        "demand",
        "sentiment",
        "regulation",
        "comparison",
        "daily_brief",
        "recommendation",
    ] = "analysis"
    product: str | None = None
    pack_size: str | None = None
    location: str | None = None
    search_terms: list[str] = Field(default_factory=list)
    crawl_needed: bool = True
    price_snapshot_needed: bool = False
    response_style: Literal["short", "normal", "detailed", "ba_report"] = "normal"


@dataclass(frozen=True)
class UserContext:
    chat_id: str | None = None
    username: str | None = None
    business_type: str | None = None
    business_scale: str | None = None
    location: str | None = None
    product_focus: list[str] = field(default_factory=list)
    response_style: str | None = None
    style_instructions: str | None = None
    business_context: str | None = None
    risk_preference: str | None = None
    # Set when the user is correcting a previous answer.  The composer will
    # treat this as an override instruction and re-generate accordingly.
    feedback_instruction: str | None = None


@dataclass(frozen=True)
class ChatEngineResult:
    answer: str
    guard: BusinessGuardResult
    plan: ChatQueryPlan | None = None
    crawl_stats: list[Any] = field(default_factory=list)
    evidence_count: int = 0
    used_price_data: bool = False
