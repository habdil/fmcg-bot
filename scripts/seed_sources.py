from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.database import session_scope
from crawling_bot.services.source_service import upsert_source
from database_migration.models.source import Source


# Sorota MVP needs fewer, cleaner sources. Keep the default active list focused
# on Indonesian market context that can help UMKM pricing, stock, supplier, and
# demand decisions. Global sources are kept as disabled references to avoid
# noisy crawls in early product testing.
SEED_SOURCES: list[dict[str, Any]] = [
    {
        "name": "Antara Ekonomi RSS",
        "url": "https://www.antaranews.com/rss/ekonomi.xml",
        "source_category": "indonesia_economy",
        "credibility_score": 0.82,
        "priority": 1,
        "use_cases": ["macro", "regulation", "commodity", "market_update"],
        "notes": "Sumber resmi berita ekonomi nasional; baik untuk konteks kebijakan dan harga pasar.",
    },
    {
        "name": "Bisnis.com RSS",
        "url": "https://www.bisnis.com/rss",
        "source_category": "indonesia_business",
        "credibility_score": 0.80,
        "priority": 1,
        "is_active": False,
        "use_cases": ["business_news", "retail", "commodity", "supplier_context"],
        "notes": "Dinonaktifkan karena endpoint RSS mengembalikan 404 pada 2026-05-10.",
    },
    {
        "name": "Kontan RSS",
        "url": "https://www.kontan.co.id/rss",
        "source_category": "indonesia_business",
        "credibility_score": 0.78,
        "priority": 1,
        "use_cases": ["business_news", "commodity", "consumer_spending"],
        "notes": "Berita bisnis dan ekonomi Indonesia; relevan untuk daya beli dan biaya usaha.",
    },
    {
        "name": "Detik Finance RSS",
        "url": "https://finance.detik.com/rss",
        "source_category": "indonesia_business",
        "credibility_score": 0.75,
        "priority": 2,
        "use_cases": ["business_news", "commodity", "market_update"],
        "notes": "Update cepat ekonomi Indonesia; dipakai sebagai pembanding berita pasar.",
    },
    {
        "name": "CNBC Indonesia RSS",
        "url": "https://www.cnbcindonesia.com/rss",
        "source_category": "indonesia_business",
        "credibility_score": 0.75,
        "priority": 2,
        "use_cases": ["macro", "commodity", "business_news"],
        "notes": "Berita ekonomi dan bisnis Indonesia; gunakan selektif agar tidak terlalu pasar modal.",
    },
    {
        "name": "Tempo Bisnis RSS",
        "url": "https://rss.tempo.co/bisnis",
        "source_category": "indonesia_business",
        "credibility_score": 0.76,
        "priority": 2,
        "use_cases": ["business_news", "regulation", "market_update"],
        "notes": "Berita bisnis nasional untuk konteks regulasi dan kondisi pasar.",
    },
    {
        "name": "Republika Ekonomi RSS",
        "url": "https://www.republika.co.id/rss/ekonomi",
        "source_category": "indonesia_economy",
        "credibility_score": 0.72,
        "priority": 3,
        "use_cases": ["business_news", "consumer_spending", "market_update"],
        "notes": "Sumber tambahan ekonomi nasional untuk coverage berita umum.",
    },
    {
        "name": "Liputan6 Bisnis RSS",
        "url": "https://www.liputan6.com/rss/bisnis",
        "source_category": "indonesia_business",
        "credibility_score": 0.71,
        "priority": 3,
        "use_cases": ["business_news", "market_update"],
        "notes": "Sumber tambahan untuk update cepat bisnis dan ekonomi Indonesia.",
    },
    {
        "name": "IDX Channel RSS",
        "url": "https://www.idxchannel.com/feed",
        "source_category": "capital_market",
        "credibility_score": 0.72,
        "priority": 4,
        "is_active": False,
        "use_cases": ["public_company_context"],
        "notes": "Dinonaktifkan untuk MVP karena terlalu banyak konteks pasar modal.",
    },
    {
        "name": "Investor Daily RSS",
        "url": "https://investor.id/feed",
        "source_category": "capital_market",
        "credibility_score": 0.74,
        "priority": 4,
        "is_active": False,
        "use_cases": ["macro", "public_company_context"],
        "notes": "Dinonaktifkan untuk MVP; aktifkan hanya jika butuh konteks pasar modal.",
    },
    {
        "name": "BBC Business RSS",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "source_category": "global_business",
        "credibility_score": 0.88,
        "priority": 5,
        "is_active": False,
        "use_cases": ["global_macro"],
        "notes": "Referensi global, dinonaktifkan agar jawaban UMKM tidak terlalu melebar.",
    },
    {
        "name": "Al Jazeera Business RSS",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "source_category": "global_business",
        "credibility_score": 0.78,
        "priority": 5,
        "is_active": False,
        "use_cases": ["global_macro", "commodity"],
        "notes": "Referensi global, dinonaktifkan untuk menjaga fokus MVP.",
    },
]


def seed_sources(*, dry_run: bool = False, deactivate_unlisted: bool = False) -> None:
    active = sum(1 for item in SEED_SOURCES if item.get("is_active", True))
    inactive = len(SEED_SOURCES) - active

    if dry_run:
        print(f"Sorota sources: {len(SEED_SOURCES)} total")
        print(f"Active: {active}")
        print(f"Inactive: {inactive}")
        for item in SEED_SOURCES:
            status = "active" if item.get("is_active", True) else "inactive"
            category = item.get("source_category", "market_intelligence")
            priority = item.get("priority", "-")
            print(f"- [{status}] p{priority} {category}: {item['name']} -> {item['url']}")
        if deactivate_unlisted:
            print("Would deactivate unlisted Sorota seed sources.")
        return

    seeded_names = {item["name"] for item in SEED_SOURCES}
    with session_scope() as session:
        for item in SEED_SOURCES:
            upsert_source(
                session,
                name=item["name"],
                url=item["url"],
                source_type="rss",
                source_category=item.get("source_category", "market_intelligence"),
                credibility_score=item["credibility_score"],
                is_active=item.get("is_active", True),
                notes=item.get("notes"),
                config_json={
                    "seed_script": "scripts/seed_sources.py",
                    "seed_group": "sorota_market_news",
                    "priority": item.get("priority"),
                    "use_cases": item.get("use_cases", []),
                },
            )

        deactivated = 0
        if deactivate_unlisted:
            statement = select(Source).where(
                Source.source_type == "rss",
                Source.name.notin_(seeded_names),
            )
            for source in session.scalars(statement):
                config = source.config_json or {}
                if config.get("seed_script") == "scripts/seed_sources.py":
                    source.is_active = False
                    source.notes = _append_note(source.notes, "Dinonaktifkan karena tidak ada di seed Sorota terbaru.")
                    deactivated += 1

    print(f"Seeded {len(SEED_SOURCES)} Sorota market news sources.")
    print(f"Active      : {active}")
    print(f"Inactive    : {inactive}")
    if deactivate_unlisted:
        print(f"Deactivated : {deactivated} unlisted old seed sources")


def _append_note(existing: str | None, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing}\n{note}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Sorota market news RSS sources.")
    parser.add_argument("--dry-run", action="store_true", help="Print sources without writing to DB.")
    parser.add_argument(
        "--deactivate-unlisted",
        action="store_true",
        help="Deactivate old RSS sources previously created by this seed script but not listed anymore.",
    )
    args = parser.parse_args()
    seed_sources(dry_run=args.dry_run, deactivate_unlisted=args.deactivate_unlisted)


if __name__ == "__main__":
    main()
