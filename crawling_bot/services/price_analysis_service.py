from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

from sqlalchemy import or_, select

from crawling_bot.database import session_scope
from crawling_bot.schemas.price_schema import (
    AvailabilitySummary,
    PriceMovementSummary,
    PricePoint,
    PriceSourceReference,
)
from database_migration.models.product import (
    Product,
    ProductAvailabilitySnapshot,
    ProductPriceSnapshot,
)

MONEY_QUANT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.01")


def normalize_product_name(value: str) -> str:
    return " ".join(value.lower().strip().split())


def calculate_price_movement(
    product: str,
    snapshots: Iterable[Any],
    *,
    period_days: int = 7,
    currency: str = "IDR",
) -> PriceMovementSummary:
    rows = list(snapshots)
    if not rows:
        return PriceMovementSummary(product=product, period_days=period_days, currency=currency)

    daily_prices: dict[date, list[Decimal]] = defaultdict(list)
    daily_sources: dict[date, set[str]] = defaultdict(set)
    daily_locations: dict[date, set[str]] = defaultdict(set)
    all_prices: list[Decimal] = []
    all_sources: set[str] = set()
    source_references: list[PriceSourceReference] = []
    seen_references: set[str] = set()
    latest_observed_at: datetime | None = None

    for row in rows:
        price = _decimal_value(_field(row, "price"))
        observed_at = _datetime_value(_field(row, "observed_at"))
        if price is None or observed_at is None:
            continue

        observed_date = observed_at.date()
        daily_prices[observed_date].append(price)
        all_prices.append(price)

        source_name = str(_field(row, "source_name") or "").strip()
        if source_name:
            daily_sources[observed_date].add(source_name)
            all_sources.add(source_name)
            source_url = _string_or_none(_field(row, "source_url"))
            reference_url = _string_or_none(_field(row, "reference_url"))
            reference_label = _string_or_none(_field(row, "reference_label"))
            reference_key = f"{source_name}|{reference_url or source_url or reference_label or ''}"
            if reference_key not in seen_references:
                source_references.append(
                    PriceSourceReference(
                        source_name=source_name,
                        source_url=source_url,
                        reference_label=reference_label,
                        reference_url=reference_url,
                        observed_at=observed_at,
                    )
                )
                seen_references.add(reference_key)

        location = str(_field(row, "location") or "").strip()
        if location:
            daily_locations[observed_date].add(location)

        if latest_observed_at is None or observed_at > latest_observed_at:
            latest_observed_at = observed_at

    if not daily_prices:
        return PriceMovementSummary(product=product, period_days=period_days, currency=currency)

    points: list[PricePoint] = []
    previous_average: Decimal | None = None
    for observed_date in sorted(daily_prices):
        average_price = _average_decimal(daily_prices[observed_date])
        change_amount: Decimal | None = None
        change_percent: Decimal | None = None
        if previous_average is not None:
            change_amount = _money(average_price - previous_average)
            if previous_average != 0:
                change_percent = _percent((change_amount / previous_average) * Decimal("100"))
        points.append(
            PricePoint(
                date=observed_date,
                average_price=average_price,
                change_amount=change_amount,
                change_percent=change_percent,
                source_count=len(daily_sources[observed_date]) or len(daily_prices[observed_date]),
                locations=sorted(daily_locations[observed_date]),
            )
        )
        previous_average = average_price

    total_change_amount: Decimal | None = None
    total_change_percent: Decimal | None = None
    if len(points) >= 2:
        first = points[0].average_price
        last = points[-1].average_price
        total_change_amount = _money(last - first)
        if first != 0:
            total_change_percent = _percent((total_change_amount / first) * Decimal("100"))

    return PriceMovementSummary(
        product=product,
        period_days=period_days,
        currency=currency,
        price_points=points,
        total_change_amount=total_change_amount,
        total_change_percent=total_change_percent,
        trend_direction=_trend_direction(points, total_change_percent),
        highest_price=_money(max(all_prices)),
        lowest_price=_money(min(all_prices)),
        average_price=_average_decimal(all_prices),
        source_count=len(all_sources) or len(rows),
        snapshot_count=len(all_prices),
        latest_observed_at=latest_observed_at,
        data_quality=_price_data_quality(len(points), len(all_prices), len(all_sources)),
        source_references=source_references[:10],
    )


def calculate_availability_summary(
    product: str,
    snapshots: Iterable[Any],
    *,
    period_days: int = 7,
) -> AvailabilitySummary:
    rows = list(snapshots)
    if not rows:
        return AvailabilitySummary(product=product, period_days=period_days)

    counts = {"in_stock": 0, "low_stock": 0, "out_of_stock": 0, "unknown": 0}
    locations: set[str] = set()
    latest_observed_at: datetime | None = None
    latest_seller_count: int | None = None

    for row in rows:
        status = _stock_status(_field(row, "stock_status"))
        counts[status] += 1

        location = str(_field(row, "location") or "").strip()
        if location:
            locations.add(location)

        observed_at = _datetime_value(_field(row, "observed_at"))
        if observed_at is not None and (latest_observed_at is None or observed_at > latest_observed_at):
            latest_observed_at = observed_at
            latest_seller_count = _int_value(_field(row, "seller_count"))

    total = sum(counts.values())
    return AvailabilitySummary(
        product=product,
        period_days=period_days,
        total_snapshots=total,
        in_stock_count=counts["in_stock"],
        low_stock_count=counts["low_stock"],
        out_of_stock_count=counts["out_of_stock"],
        unknown_count=counts["unknown"],
        seller_count_latest=latest_seller_count,
        locations=sorted(locations),
        latest_observed_at=latest_observed_at,
        availability_signal=_availability_signal(counts, total),
        data_quality="high" if total >= 5 else "medium" if total >= 2 else "low",
    )


def get_price_movement(product_keyword: str, period_days: int = 7) -> PriceMovementSummary:
    normalized = normalize_product_name(product_keyword)
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    pattern = f"%{normalized}%"
    raw_pattern = f"%{product_keyword.strip()}%"

    with session_scope() as session:
        statement = (
            select(ProductPriceSnapshot)
            .join(Product, ProductPriceSnapshot.product_id == Product.id)
            .where(
                ProductPriceSnapshot.observed_at >= since,
                or_(
                    ProductPriceSnapshot.normalized_product_name.ilike(pattern),
                    ProductPriceSnapshot.product_name.ilike(raw_pattern),
                    Product.normalized_name.ilike(pattern),
                    Product.name.ilike(raw_pattern),
                ),
            )
            .order_by(ProductPriceSnapshot.observed_at.asc())
        )
        snapshots = list(session.execute(statement).scalars())

    currency = str(_field(snapshots[0], "currency") or "IDR") if snapshots else "IDR"
    return calculate_price_movement(
        product_keyword,
        snapshots,
        period_days=period_days,
        currency=currency,
    )


def get_availability_summary(product_keyword: str, period_days: int = 7) -> AvailabilitySummary:
    normalized = normalize_product_name(product_keyword)
    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    pattern = f"%{normalized}%"
    raw_pattern = f"%{product_keyword.strip()}%"

    with session_scope() as session:
        availability_statement = (
            select(ProductAvailabilitySnapshot)
            .join(Product, ProductAvailabilitySnapshot.product_id == Product.id)
            .where(
                ProductAvailabilitySnapshot.observed_at >= since,
                or_(
                    Product.normalized_name.ilike(pattern),
                    Product.name.ilike(raw_pattern),
                    ProductAvailabilitySnapshot.product_name.ilike(raw_pattern),
                ),
            )
            .order_by(ProductAvailabilitySnapshot.observed_at.asc())
        )
        availability_rows = list(session.execute(availability_statement).scalars())

        if availability_rows:
            return calculate_availability_summary(product_keyword, availability_rows, period_days=period_days)

        price_statement = (
            select(ProductPriceSnapshot)
            .join(Product, ProductPriceSnapshot.product_id == Product.id)
            .where(
                ProductPriceSnapshot.observed_at >= since,
                or_(
                    ProductPriceSnapshot.normalized_product_name.ilike(pattern),
                    ProductPriceSnapshot.product_name.ilike(raw_pattern),
                    Product.normalized_name.ilike(pattern),
                    Product.name.ilike(raw_pattern),
                ),
            )
            .order_by(ProductPriceSnapshot.observed_at.asc())
        )
        price_rows = list(session.execute(price_statement).scalars())

    return calculate_availability_summary(product_keyword, price_rows, period_days=period_days)


def _field(row: Any, name: str) -> Any:
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


def _datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _decimal_value(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_or_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _average_decimal(values: list[Decimal]) -> Decimal:
    return _money(sum(values) / Decimal(len(values)))


def _trend_direction(points: list[PricePoint], total_change_percent: Decimal | None) -> str:
    if len(points) < 2 or total_change_percent is None:
        return "insufficient_data"

    changes = [point.change_percent for point in points[1:] if point.change_percent is not None]
    positive = sum(1 for change in changes if change is not None and change > Decimal("1"))
    negative = sum(1 for change in changes if change is not None and change < Decimal("-1"))

    if positive and negative:
        return "volatile"
    if abs(total_change_percent) <= Decimal("1"):
        return "stable"
    if total_change_percent > Decimal("1") and positive >= negative:
        return "increasing"
    if total_change_percent < Decimal("-1") and negative >= positive:
        return "decreasing"
    return "volatile"


def _price_data_quality(point_count: int, snapshot_count: int, source_count: int) -> str:
    if point_count >= 3 and snapshot_count >= 5 and source_count >= 3:
        return "high"
    if point_count >= 2 or source_count >= 2 or snapshot_count >= 3:
        return "medium"
    return "low"


def _stock_status(value: Any) -> str:
    status = str(value or "unknown").strip().lower()
    if status in {"in_stock", "available", "ready", "tersedia"}:
        return "in_stock"
    if status in {"low_stock", "limited", "terbatas", "menipis"}:
        return "low_stock"
    if status in {"out_of_stock", "empty", "sold_out", "habis"}:
        return "out_of_stock"
    return "unknown"


def _availability_signal(counts: dict[str, int], total: int) -> str:
    if total == 0:
        return "insufficient_data"
    if counts["out_of_stock"] >= max(1, total // 2):
        return "out_of_stock"
    if counts["low_stock"] + counts["out_of_stock"] >= max(1, int(total * 0.4)):
        return "limited"
    if counts["in_stock"] and (counts["low_stock"] or counts["out_of_stock"]):
        return "mixed"
    if counts["in_stock"]:
        return "healthy"
    return "unknown"
