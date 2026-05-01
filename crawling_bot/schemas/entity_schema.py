from __future__ import annotations

from pydantic import BaseModel, Field


class EntityItem(BaseModel):
    name: str
    entity_type: str
    normalized_name: str
    relevance_score: float = Field(default=0.5, ge=0, le=1)
