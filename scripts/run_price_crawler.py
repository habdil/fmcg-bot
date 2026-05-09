"""Jalankan price crawler untuk semua target yang sudah dikonfigurasi.

Mengambil harga dari halaman produk retail/grosir yang terdaftar di
seed_price_sources.py, lalu menyimpannya ke product_price_snapshots.

Cara pakai:
  python scripts/run_price_crawler.py           # crawl semua target aktif
  python scripts/run_price_crawler.py --dry-run  # tampilkan target saja, tidak crawl
  python scripts/run_price_crawler.py --source "Indogrosir"  # crawl 1 source saja

Jadwalkan via cron atau APScheduler setiap 4-8 jam agar data harga selalu fresh.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.price_targets import PRICE_SOURCE_CONFIGS
from crawling_bot.services.playwright_price_fetcher import fetch_price_with_playwright
from crawling_bot.services.price_snapshot_service import collect_price_from_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("run_price_crawler")

# Jeda antar request agar tidak kena rate limit
_REQUEST_DELAY_SECONDS = 3


def run(*, dry_run: bool = False, source_filter: str | None = None) -> None:
    total = 0
    ok = 0
    failed = 0
    skipped = 0

    for config in PRICE_SOURCE_CONFIGS:
        if source_filter and config.source_name.lower() != source_filter.lower():
            continue

        for target in config.targets:
            total += 1

            if not target.enabled:
                logger.info("SKIP (disabled)  %s – %s", config.source_name, target.product_name)
                skipped += 1
                continue

            if not target.url:
                logger.warning(
                    "SKIP (no URL)    %s – %s  ← isi URL di seed_price_sources.py",
                    config.source_name,
                    target.product_name,
                )
                skipped += 1
                continue

            if dry_run:
                logger.info("DRY RUN  %s – %s  →  %s", config.source_name, target.product_name, target.url)
                continue

            method = getattr(target, "fetch_method", "httpx")
            logger.info("Fetching [%s]  %s – %s", method, config.source_name, target.product_name)
            try:
                if method == "playwright":
                    result = fetch_price_with_playwright(
                        product_name=target.product_name,
                        source_name=config.source_name,
                        url=target.url,
                        location=target.location,
                    )
                else:
                    result = collect_price_from_url(
                        product_name=target.product_name,
                        source_name=config.source_name,
                        url=target.url,
                        location=target.location,
                    )
                logger.info(
                    "  OK  Rp %s  (dari teks: %r, %d kandidat)",
                    result.snapshot.price,
                    result.matched_price_text,
                    result.candidate_count,
                )
                ok += 1
            except Exception as exc:
                logger.error("  FAIL  %s", exc)
                failed += 1

            time.sleep(_REQUEST_DELAY_SECONDS)

    print(f"\n{'=== DRY RUN ===' if dry_run else '=== DONE ==='}")
    print(f"Total   : {total}")
    print(f"Berhasil: {ok}")
    print(f"Gagal   : {failed}")
    print(f"Skip    : {skipped}")

    if skipped == total and not dry_run:
        print(
            "\nSemua target di-skip. Isi URL produk di scripts/seed_price_sources.py "
            "dan set enabled=True untuk mulai crawl harga."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sorota market price crawler")
    parser.add_argument("--dry-run", action="store_true", help="Tampilkan target saja, jangan crawl")
    parser.add_argument("--source", help="Filter nama source (misal: Indogrosir)")
    args = parser.parse_args()
    run(dry_run=args.dry_run, source_filter=args.source)


if __name__ == "__main__":
    main()
