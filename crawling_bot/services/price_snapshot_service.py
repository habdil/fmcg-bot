from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from crawling_bot.database import session_scope
from crawling_bot.services.price_analysis_service import normalize_product_name
from database_migration.models.product import Product, ProductPriceSnapshot


PRICE_RE = re.compile(
    r"(?:Rp\.?\s*)?(\d{1,3}(?:[.\s]\d{3})+|\d+)(?:,\d{1,2})?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriceSnapshotInput:
    product_name: str
    price: Decimal
    source_name: str
    source_url: str | None = None
    reference_label: str | None = None
    reference_url: str | None = None
    capture_method: str = "manual"
    raw_price_text: str | None = None
    marketplace: str | None = None
    seller_name: str | None = None
    location: str | None = None
    stock_status: str | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class PriceCollectResult:
    snapshot: ProductPriceSnapshot
    matched_price_text: str
    candidate_count: int


def save_price_snapshot(data: PriceSnapshotInput) -> ProductPriceSnapshot:
    product_name = _required(data.product_name, "product_name")
    source_name = _required(data.source_name, "source_name")
    normalized = normalize_product_name(product_name)
    observed_at = data.observed_at or datetime.now(timezone.utc)

    with session_scope() as session:
        product = session.scalar(select(Product).where(Product.normalized_name == normalized))
        if product is None:
            product = Product(
                name=product_name,
                normalized_name=normalized,
            )
            session.add(product)
            session.flush()

        snapshot = ProductPriceSnapshot(
            product_id=product.id,
            product_name=product_name,
            normalized_product_name=normalized,
            source_name=source_name,
            source_url=data.source_url,
            reference_label=data.reference_label,
            reference_url=data.reference_url,
            capture_method=data.capture_method,
            raw_price_text=data.raw_price_text,
            marketplace=data.marketplace,
            seller_name=data.seller_name,
            location=data.location,
            price=data.price,
            currency="IDR",
            stock_status=data.stock_status,
            observed_at=observed_at,
        )
        session.add(snapshot)
        session.flush()
        session.refresh(snapshot)
        return snapshot


def collect_price_from_url(
    *,
    product_name: str,
    source_name: str,
    url: str,
    location: str | None = None,
) -> PriceCollectResult:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    candidates = extract_price_candidates(text)
    if not candidates:
        raise ValueError("Tidak menemukan pola harga Rupiah di URL tersebut.")

    raw_price_text, price = candidates[0]
    snapshot = save_price_snapshot(
        PriceSnapshotInput(
            product_name=product_name,
            price=price,
            source_name=source_name,
            source_url=url,
            reference_label=f"{source_name} - {product_name}",
            reference_url=str(response.url),
            capture_method="url_fetch",
            raw_price_text=raw_price_text,
            location=location,
        )
    )
    return PriceCollectResult(
        snapshot=snapshot,
        matched_price_text=raw_price_text,
        candidate_count=len(candidates),
    )


def extract_price_candidates(text: str) -> list[tuple[str, Decimal]]:
    candidates: list[tuple[str, Decimal]] = []
    for match in PRICE_RE.finditer(text):
        raw = match.group(0).strip()
        if "rp" not in raw.lower():
            prefix = text[max(match.start() - 4, 0):match.start()].lower()
            if "rp" not in prefix:
                continue
        value = parse_price(raw)
        if value is None:
            continue
        if value < Decimal("100") or value > Decimal("10000000"):
            continue
        candidates.append((raw, value))
    return candidates


def parse_price(value: str) -> Decimal | None:
    cleaned = value.lower().replace("rp", "").replace(" ", "").replace(".", "")
    if "," in cleaned:
        cleaned = cleaned.split(",", 1)[0]
    cleaned = re.sub(r"[^\d]", "", cleaned)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _required(value: str | None, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} wajib diisi.")
    return cleaned
