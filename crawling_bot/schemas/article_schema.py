from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ArticleCandidate(BaseModel):
    source_id: str
    title: str
    url: HttpUrl
    raw_content: Optional[str] = None
    clean_content: Optional[str] = None
    published_at: Optional[datetime] = None
    language: str = "id"


class ProcessedArticle(BaseModel):
    title: str
    url: str
    raw_content: Optional[str] = None
    clean_content: str
    summary: Optional[str] = None
    reason: Optional[str] = None
    evidence_text: Optional[str] = None
    ai_polished_summary: Optional[str] = None
    published_at: Optional[datetime] = None
    language: str = "id"
    category: Optional[str] = None
    relevance_score: float = Field(default=0, ge=0, le=1)
    impact_score: float = Field(default=0, ge=0, le=1)
    confidence_score: float = Field(default=0, ge=0, le=1)
    urgency: str = "low"
    content_hash: str
