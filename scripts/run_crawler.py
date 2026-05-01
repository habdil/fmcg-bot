from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.main import run_crawler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FMCG crawling pipeline.")
    parser.add_argument("--max", type=int, default=None, help="Maximum articles per source.")
    args = parser.parse_args()

    results = run_crawler(max_articles_per_source=args.max)
    for index, stats in enumerate(results, start=1):
        print(
            f"{index}. found={stats.total_found} crawled={stats.total_crawled} "
            f"processed={stats.total_processed} saved={stats.total_saved} "
            f"skipped={stats.total_skipped} failed={stats.total_failed}"
        )


if __name__ == "__main__":
    main()
