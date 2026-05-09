"""Disable sources yang diketahui broken, paywall, atau tidak relevan
untuk Sorota. Jalankan sekali: python scripts/disable_broken_sources.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select

from crawling_bot.database import session_scope
from database_migration.models.source import Source

# Sumber yang dinonaktifkan beserta alasannya
DISABLE = {
    # ---- DNS mati / URL berubah ----
    "Reuters Business RSS": "feeds.reuters.com DNS mati",
    "Reuters Commodities RSS": "feeds.reuters.com DNS mati",

    # ---- Bot-blocked / 403 ----
    "AP Business News RSS": "RSSHub block bot (403)",

    # ---- Paywall artikel (RSS OK, konten 403) ----
    "Financial Times RSS": "FT article paywall (403)",
    "The Economist Business RSS": "Economist paywall",
    "Harvard Business Review RSS": "HBR paywall",

    # ---- Tidak relevan untuk keputusan harian UMKM Indonesia ----
    "TechCrunch Startups RSS": "startup/tech, tidak relevan untuk UMKM MVP",
    "Nasdaq Market News RSS": "pasar saham AS, tidak relevan untuk UMKM MVP",
    "Fortune Business RSS": "US business, tidak relevan untuk UMKM MVP",
    "Forbes Business RSS": "US business, tidak relevan untuk UMKM MVP",
    "MarketWatch RSS": "US finance/market, tidak relevan untuk UMKM MVP",
}


def main() -> None:
    with session_scope() as session:
        disabled = []
        not_found = []
        for name, reason in DISABLE.items():
            source = session.scalar(select(Source).where(Source.name == name))
            if source is None:
                not_found.append(name)
                continue
            source.is_active = False
            disabled.append((name, reason))

        print(f"\nDisabled {len(disabled)} sources:")
        for name, reason in disabled:
            print(f"  ✗  {name}  ({reason})")

        if not_found:
            print(f"\nNot found in DB (skip):")
            for name in not_found:
                print(f"  -  {name}")

    print("\nDone. Jalankan bot lagi – crawler sekarang skip sumber-sumber ini.")


if __name__ == "__main__":
    main()
