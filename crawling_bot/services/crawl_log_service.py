from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from database_migration.models.crawl_log import CrawlLog
from database_migration.models.source import Source


def start_log(session: Session, source: Source | None) -> CrawlLog:
    log = CrawlLog(source_id=source.id if source else None, status="partial_success")
    session.add(log)
    session.flush()
    return log


def finish_log(
    log: CrawlLog,
    *,
    status: str,
    message: Optional[str] = None,
    total_found: int = 0,
    total_crawled: int = 0,
    total_processed: int = 0,
    total_saved: int = 0,
    total_skipped: int = 0,
    total_failed: int = 0,
) -> None:
    log.status = status
    log.message = message
    log.total_found = total_found
    log.total_crawled = total_crawled
    log.total_processed = total_processed
    log.total_saved = total_saved
    log.total_skipped = total_skipped
    log.total_failed = total_failed
    log.finished_at = datetime.now(timezone.utc)
