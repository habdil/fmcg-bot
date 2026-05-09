"""On-demand price crawler service.

Dipanggil oleh ChatEngine ketika user menanyakan harga produk spesifik.
Mencocokkan keyword dari query user ke PriceTarget yang sudah dikonfigurasi,
lalu menjalankan crawler yang sesuai (httpx atau playwright).

Flow:
    User: "harga minyak goreng tropical indogrosir berapa?"
    → QueryPlanner deteksi price_snapshot_needed=True, product="minyak goreng tropical"
    → ChatEngine panggil crawl_prices_for_query("minyak goreng tropical")
    → Service match ke PriceTarget "Minyak Goreng Tropical 2L" di KlikIndogrosir
    → Crawl dengan Playwright → simpan ke price_snapshots
    → ChatEngine ambil data segar dari DB → compose jawaban dengan harga
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from crawling_bot.price_targets import PRICE_SOURCE_CONFIGS, PriceSourceConfig, PriceTarget

logger = logging.getLogger(__name__)

# Cache hasil crawl harga agar Playwright tidak diluncurkan ulang tiap query
_price_cache: dict[str, tuple[float, list["PriceCrawlResult"]]] = {}
_PRICE_CACHE_TTL = 1800  # 30 menit


@dataclass(frozen=True)
class PriceCrawlResult:
    source_name: str
    product_name: str
    price: float
    raw_text: str
    success: bool
    error: str = ""


def crawl_prices_for_query(keyword: str, *, max_targets: int = 3) -> list[PriceCrawlResult]:
    """Crawl harga untuk keyword yang diberikan.

    Mencocokkan keyword ke PriceTarget yang dikonfigurasi, lalu menjalankan
    fetcher yang sesuai. Mengembalikan list hasil crawl (berhasil maupun gagal).

    Hasil di-cache 30 menit agar Playwright tidak diluncurkan ulang untuk
    pertanyaan yang sama dalam satu sesi.

    Args:
        keyword: Kata kunci produk dari query user (misal "minyak goreng tropical").
        max_targets: Batas target yang di-crawl agar tidak terlalu lambat.

    Returns:
        List PriceCrawlResult. Caller bisa filter yang success=True saja.
    """
    now = time.monotonic()
    cached = _price_cache.get(keyword)
    if cached is not None and (now - cached[0]) < _PRICE_CACHE_TTL:
        logger.info("price_crawler_service: pakai cache untuk %r (%.0fs lalu)", keyword, now - cached[0])
        return cached[1]

    targets = _find_matching_targets(keyword, max_results=max_targets)
    if not targets:
        logger.info("price_crawler_service: tidak ada target cocok untuk %r", keyword)
        return []

    results: list[PriceCrawlResult] = []
    for config, target in targets:
        result = _crawl_target(config, target)
        results.append(result)

    _price_cache[keyword] = (now, results)
    return results


def list_active_targets() -> list[tuple[PriceSourceConfig, PriceTarget]]:
    """Kembalikan semua target yang aktif dan punya URL."""
    out = []
    for config in PRICE_SOURCE_CONFIGS:
        for target in config.targets:
            if target.enabled and target.url:
                out.append((config, target))
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_matching_targets(
    keyword: str,
    *,
    max_results: int = 3,
) -> list[tuple[PriceSourceConfig, PriceTarget]]:
    """Cocokkan keyword ke target aktif berdasarkan match_keywords atau product_name."""
    keyword_lower = keyword.lower().strip()
    kw_tokens = set(keyword_lower.split())
    scored: list[tuple[int, PriceSourceConfig, PriceTarget]] = []

    for config in PRICE_SOURCE_CONFIGS:
        for target in config.targets:
            if not target.enabled or not target.url:
                continue
            score = _match_score(keyword_lower, kw_tokens, target)
            if score > 0:
                scored.append((score, config, target))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(cfg, tgt) for _, cfg, tgt in scored[:max_results]]


def _match_score(keyword_lower: str, kw_tokens: set[str], target: PriceTarget) -> int:
    """Hitung skor kecocokan antara keyword dan target. Skor 0 = tidak cocok."""
    score = 0

    # Cek match_keywords yang sudah dikonfigurasi (lebih presisi)
    for mk in target.match_keywords:
        mk_lower = mk.lower()
        if mk_lower in keyword_lower:
            score += 10
        elif any(t in mk_lower for t in kw_tokens if len(t) > 3):
            score += 5

    # Fallback: match ke product_name
    if score == 0:
        name_lower = target.product_name.lower()
        for token in kw_tokens:
            if len(token) > 3 and token in name_lower:
                score += 3

    return score


def _crawl_target(config: PriceSourceConfig, target: PriceTarget) -> PriceCrawlResult:
    """Jalankan satu target crawl dan kembalikan hasilnya."""
    method = target.fetch_method
    logger.info("price_crawler_service: crawl [%s] %s – %s", method, config.source_name, target.product_name)
    try:
        if method == "playwright":
            from crawling_bot.services.playwright_price_fetcher import fetch_price_with_playwright
            result = fetch_price_with_playwright(
                product_name=target.product_name,
                source_name=config.source_name,
                url=target.url,
                location=target.location,
            )
        else:
            from crawling_bot.services.price_snapshot_service import collect_price_from_url
            result = collect_price_from_url(
                product_name=target.product_name,
                source_name=config.source_name,
                url=target.url,
                location=target.location,
            )
        return PriceCrawlResult(
            source_name=config.source_name,
            product_name=target.product_name,
            price=float(result.snapshot.price),
            raw_text=result.matched_price_text,
            success=True,
        )
    except Exception as exc:
        logger.warning(
            "price_crawler_service: gagal crawl %s – %s: %s",
            config.source_name, target.product_name, exc,
        )
        return PriceCrawlResult(
            source_name=config.source_name,
            product_name=target.product_name,
            price=0.0,
            raw_text="",
            success=False,
            error=str(exc),
        )
