"""Playwright-based price fetcher untuk situs dengan anti-bot protection.

Digunakan ketika httpx biasa kena 403 (Cloudflare, login-wall, JS-heavy pages).
Playwright menjalankan Chromium sungguhan (headless) sehingga tampil seperti
browser nyata di mata server.

Dependency:
    pip install playwright
    playwright install chromium

Cara pakai:
    from crawling_bot.services.playwright_price_fetcher import fetch_price_with_playwright
    result = fetch_price_with_playwright(
        product_name="Minyak Goreng Tropical 2L",
        source_name="KlikIndogrosir",
        url="https://klikindogrosir.com/product_details/1511121",
    )
"""

from __future__ import annotations

import logging
from decimal import Decimal

from bs4 import BeautifulSoup

from crawling_bot.services.price_snapshot_service import (
    PriceCollectResult,
    PriceSnapshotInput,
    extract_price_candidates,
    save_price_snapshot,
)

logger = logging.getLogger(__name__)

# Waktu tunggu maksimal agar JS selesai render (ms)
_PAGE_TIMEOUT_MS = 30_000
# Setelah halaman load, tunggu sebentar agar elemen harga muncul (ms)
_SETTLE_DELAY_MS = 2_000


def fetch_price_with_playwright(
    *,
    product_name: str,
    source_name: str,
    url: str,
    location: str | None = None,
) -> PriceCollectResult:
    """Ambil harga dari URL menggunakan Playwright (Chromium headless).

    Raises:
        ImportError: jika playwright belum diinstall.
        ValueError: jika tidak ada harga Rupiah ditemukan di halaman.
        Exception: jika halaman gagal dibuka atau timeout.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "Playwright belum diinstall. Jalankan:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from exc

    logger.info("Playwright fetching: %s", url)
    html = _fetch_html(url)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())

    candidates = extract_price_candidates(text)
    if not candidates:
        # Coba cari pola harga langsung di raw HTML sebelum menyerah
        candidates = extract_price_candidates(html)
    if not candidates:
        raise ValueError(
            f"Tidak menemukan pola harga Rupiah di halaman: {url}\n"
            "Kemungkinan halaman memerlukan login atau konten dimuat via API terpisah."
        )

    raw_price_text, price = candidates[0]
    logger.info("  Harga ditemukan: %s → Rp %s", raw_price_text, price)

    snapshot = save_price_snapshot(
        PriceSnapshotInput(
            product_name=product_name,
            price=price,
            source_name=source_name,
            source_url=url,
            reference_label=f"{source_name} – {product_name}",
            reference_url=url,
            capture_method="playwright",
            raw_price_text=raw_price_text,
            location=location,
        )
    )
    return PriceCollectResult(
        snapshot=snapshot,
        matched_price_text=raw_price_text,
        candidate_count=len(candidates),
    )


def _fetch_html(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
        )
        # Sembunyikan tanda-tanda automation dari navigator JS
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()
        try:
            page.goto(url, timeout=_PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            # Tunggu sebentar agar konten JS selesai render
            page.wait_for_timeout(_SETTLE_DELAY_MS)
            html = page.content()
        finally:
            browser.close()
    return html
