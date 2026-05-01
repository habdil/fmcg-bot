from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedSignal(BaseModel):
    signal_type: str
    product: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    value: Optional[str] = None
    severity: int = Field(default=1, ge=1, le=5)
    confidence_score: float = Field(default=0.5, ge=0, le=1)
    reason: Optional[str] = None
    evidence_text: Optional[str] = None
    explanation: Optional[str] = None
    source_count: int = Field(default=1, ge=1)
    related_article_count: int = Field(default=1, ge=1)
