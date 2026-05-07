from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


TrendDirection = Literal["increasing", "decreasing", "stable", "volatile", "insufficient_data"]
DataQuality = Literal["high", "medium", "low"]
AvailabilitySignal = Literal[
    "healthy",
    "limited",
    "out_of_stock",
    "mixed",
    "unknown",
    "insufficient_data",
]


class PricePoint(BaseModel):
    date: date
    average_price: Decimal
    change_amount: Decimal | None = None
    change_percent: Decimal | None = None
    source_count: int = 0
    locations: list[str] = Field(default_factory=list)


class PriceSourceReference(BaseModel):
    source_name: str
    source_url: str | None = None
    reference_label: str | None = None
    reference_url: str | None = None
    observed_at: datetime | None = None


class PriceMovementSummary(BaseModel):
    product: str
    period_days: int
    currency: str = "IDR"
    price_points: list[PricePoint] = Field(default_factory=list)
    total_change_amount: Decimal | None = None
    total_change_percent: Decimal | None = None
    trend_direction: TrendDirection = "insufficient_data"
    highest_price: Decimal | None = None
    lowest_price: Decimal | None = None
    average_price: Decimal | None = None
    source_count: int = 0
    snapshot_count: int = 0
    latest_observed_at: datetime | None = None
    data_quality: DataQuality = "low"
    source_references: list[PriceSourceReference] = Field(default_factory=list)

    @property
    def has_price_data(self) -> bool:
        return bool(self.price_points)


class AvailabilitySummary(BaseModel):
    product: str
    period_days: int
    total_snapshots: int = 0
    in_stock_count: int = 0
    low_stock_count: int = 0
    out_of_stock_count: int = 0
    unknown_count: int = 0
    seller_count_latest: int | None = None
    locations: list[str] = Field(default_factory=list)
    latest_observed_at: datetime | None = None
    availability_signal: AvailabilitySignal = "insufficient_data"
    data_quality: DataQuality = "low"

    @property
    def has_availability_data(self) -> bool:
        return self.total_snapshots > 0


class SourceCoverage(BaseModel):
    total_crawled_sources: int = 0
    total_articles_crawled: int = 0
    total_relevant_articles: int = 0
    total_strong_signals: int = 0
    total_price_snapshots: int = 0
    latest_observed_at: datetime | None = None
    source_names: list[str] = Field(default_factory=list)
