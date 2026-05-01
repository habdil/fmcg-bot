from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from crawling_bot.schemas.signal_schema import ExtractedSignal


class SourceReference(BaseModel):
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None


class SourceInfo(BaseModel):
    name: str
    url: str
    credibility_score: float = Field(ge=0, le=1)


class CrawlStats(BaseModel):
    crawled_source_count: int = 1
    related_article_count: int = 1


class AIReadyInsight(BaseModel):
    title: str
    source: SourceInfo
    article_url: str
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    entities: Dict[str, List[str]]
    signals: List[ExtractedSignal]
    reason: Optional[str] = None
    evidence_text: Optional[str] = None
    source_references: List[SourceReference]
    crawl_stats: CrawlStats
    relevance_score: float = Field(ge=0, le=1)
    impact_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    urgency: str
    ai_polished_summary: Optional[str] = None


class GeminiPolishedInsight(BaseModel):
    polished_title: str
    polished_summary: str
    business_reason: str
    recommended_action: str
    risk_level: str
    source_note: str
