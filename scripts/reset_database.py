"""Reset the development database and apply the Sorota v2 schema.

This script is destructive by design. It drops the PostgreSQL ``public``
schema, recreates it, then applies the current Alembic head.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.config import settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Drop all DB data and apply Sorota v2 schema.")
    parser.add_argument(
        "--yes-i-understand",
        action="store_true",
        help="Required. Confirms that all data in the target database may be deleted.",
    )
    args = parser.parse_args()
    if not args.yes_i_understand:
        raise SystemExit("Refusing to reset database without --yes-i-understand.")

    database_url = settings.require_migration_database_url()
    engine = create_engine(database_url, isolation_level="AUTOCOMMIT", future=True)
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    alembic_cfg = Config(str(ROOT_DIR / "database_migration" / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    print("Database reset complete. Sorota v2 schema is applied.")


if __name__ == "__main__":
    main()
