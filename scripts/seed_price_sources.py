"""Seed Sorota price source metadata and market products.

The actual crawl targets live in ``crawling_bot/price_targets.py``. This script
persists their source and product metadata to the v2 database so price survey
and market-price flows have a clean baseline after DB reset.

Usage:
  python scripts/seed_price_sources.py --dry-run
  python scripts/seed_price_sources.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.database import session_scope
from crawling_bot.price_targets import PRICE_SOURCE_CONFIGS, PriceSourceConfig, PriceTarget
from crawling_bot.services.price_analysis_service import normalize_product_name
from crawling_bot.services.source_service import upsert_source
from database_migration.models.product import Product


def seed_price_sources(*, dry_run: bool = False) -> None:
    total_targets = 0
    ready_targets = 0
    disabled_targets = 0
    missing_url_targets = 0

    if dry_run:
        for config in PRICE_SOURCE_CONFIGS:
            print(f"\n{config.source_name} ({config.source_url})")
            if config.notes:
                print(f"  {config.notes}")
            for target in config.targets:
                total_targets += 1
                status = _target_status(target)
                if status == "ready":
                    ready_targets += 1
                elif status == "missing_url":
                    missing_url_targets += 1
                else:
                    disabled_targets += 1
                print(f"  - [{status}] [{target.fetch_method}] {target.product_name}")
                if target.url:
                    print(f"    {target.url}")
        _print_summary(total_targets, ready_targets, disabled_targets, missing_url_targets, dry_run=True)
        return

    with session_scope() as session:
        for config in PRICE_SOURCE_CONFIGS:
            active_targets = [target for target in config.targets if target.enabled and target.url]
            source = upsert_source(
                session,
                name=config.source_name,
                url=config.source_url,
                source_type="price_page",
                source_category="price_reference",
                credibility_score=0.72,
                is_active=bool(active_targets),
                notes=config.notes or None,
                config_json={
                    "seed_script": "scripts/seed_price_sources.py",
                    "seed_group": "sorota_price_reference",
                    "target_count": len(config.targets),
                    "active_target_count": len(active_targets),
                    "use_cases": ["market_price_survey", "supplier_comparison", "margin_check"],
                },
            )

            for target in config.targets:
                total_targets += 1
                status = _target_status(target)
                if status == "ready":
                    ready_targets += 1
                elif status == "missing_url":
                    missing_url_targets += 1
                else:
                    disabled_targets += 1
                _upsert_market_product(session, config, target, source_id=str(source.id), status=status)

    _print_summary(total_targets, ready_targets, disabled_targets, missing_url_targets, dry_run=False)


def _upsert_market_product(
    session: Session,
    config: PriceSourceConfig,
    target: PriceTarget,
    *,
    source_id: str,
    status: str,
) -> Product:
    normalized = normalize_product_name(target.product_name)
    product = session.scalar(select(Product).where(Product.normalized_name == normalized))
    if product is None:
        product = Product(name=target.product_name, normalized_name=normalized)
        session.add(product)

    product.name = target.product_name
    product.market_scope = "public_price_reference"
    product.metadata_json = {
        "seed_script": "scripts/seed_price_sources.py",
        "source_id": source_id,
        "source_name": config.source_name,
        "source_url": config.source_url,
        "target_status": status,
        "target_url": target.url or None,
        "reference_label": target.reference_label,
        "fetch_method": target.fetch_method,
        "match_keywords": target.match_keywords,
        "location": target.location,
    }
    return product


def _target_status(target: PriceTarget) -> str:
    if target.enabled and target.url:
        return "ready"
    if target.enabled and not target.url:
        return "missing_url"
    return "disabled"


def _print_summary(
    total_targets: int,
    ready_targets: int,
    disabled_targets: int,
    missing_url_targets: int,
    *,
    dry_run: bool,
) -> None:
    title = "DRY RUN" if dry_run else "SEEDED"
    print(f"\n=== {title} SOROTA PRICE SOURCES ===")
    print(f"Sources     : {len(PRICE_SOURCE_CONFIGS)}")
    print(f"Products    : {total_targets}")
    print(f"Ready       : {ready_targets}")
    print(f"Disabled    : {disabled_targets}")
    print(f"Missing URL : {missing_url_targets}")
    print("Run price crawl with: python scripts/run_price_crawler.py --dry-run")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed price source metadata and market products.")
    parser.add_argument("--dry-run", action="store_true", help="Print config without writing to DB.")
    args = parser.parse_args()
    seed_price_sources(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
