"""Admin-only crawl commands.

Perintah yang tersedia (khusus admin):
  /crawl [N]          - Crawl semua sumber berita, maks N artikel per sumber (default 3)
  /crawl_harga        - Crawl semua price target yang aktif ke DB
  /status             - Tampilkan ringkasan kondisi DB (jumlah artikel, harga, dll)
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from crawling_bot.main import run_crawler
from crawling_bot.services.price_crawler_service import list_active_targets
from telegram_bot.services.telegram_service import reject_if_not_admin

logger = logging.getLogger(__name__)

CRAWL_LOCK = asyncio.Lock()
PRICE_CRAWL_LOCK = asyncio.Lock()


# ---------------------------------------------------------------------------
# /crawl — crawl sumber berita
# ---------------------------------------------------------------------------

def _parse_max_articles(args: list[str]) -> int:
    if not args:
        return 3
    try:
        value = int(args[0])
    except ValueError:
        return 3
    return max(1, min(value, 10))


async def _run_news_crawl(context: ContextTypes.DEFAULT_TYPE, chat_id: int, max_articles: int) -> None:
    try:
        async with CRAWL_LOCK:
            results = await asyncio.to_thread(run_crawler, max_articles)
        total_found = sum(r.total_found for r in results)
        total_saved = sum(r.total_saved for r in results)
        total_skipped = sum(r.total_skipped for r in results)
        total_failed = sum(r.total_failed for r in results)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Crawl berita selesai.\n\n"
                f"Sumber diproses : {len(results)}\n"
                f"Artikel ditemukan: {total_found}\n"
                f"Disimpan ke DB   : {total_saved}\n"
                f"Di-skip (duplikat): {total_skipped}\n"
                f"Gagal            : {total_failed}\n\n"
                "DB sudah diperbarui. Coba tanya sesuatu di chat."
            ),
        )
    except Exception as exc:
        logger.exception("News crawl failed for chat %s", chat_id)
        await context.bot.send_message(chat_id=chat_id, text=f"Crawl berita gagal: {exc}")


async def crawl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    chat = update.effective_chat
    if chat is None:
        return

    if CRAWL_LOCK.locked():
        await update.effective_message.reply_text("Crawl berita sedang berjalan. Tunggu dulu.")
        return

    max_articles = _parse_max_articles(context.args or [])
    await update.effective_message.reply_text(
        f"Crawl berita dimulai (maks {max_articles} artikel/sumber). Proses di background, tunggu notifikasi..."
    )
    context.application.create_task(_run_news_crawl(context, chat.id, max_articles))


# ---------------------------------------------------------------------------
# /crawl_harga — crawl semua price target
# ---------------------------------------------------------------------------

async def _run_price_crawl_all(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        from crawling_bot.services.playwright_price_fetcher import fetch_price_with_playwright
        from crawling_bot.services.price_snapshot_service import collect_price_from_url

        targets = list_active_targets()
        if not targets:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Tidak ada price target yang aktif. Cek crawling_bot/price_targets.py.",
            )
            return

        ok = 0
        failed = 0
        lines = ["Crawl harga selesai:\n"]

        async with PRICE_CRAWL_LOCK:
            for config, target in targets:
                try:
                    if target.fetch_method == "playwright":
                        result = await asyncio.to_thread(
                            fetch_price_with_playwright,
                            product_name=target.product_name,
                            source_name=config.source_name,
                            url=target.url,
                            location=target.location,
                        )
                    else:
                        result = await asyncio.to_thread(
                            collect_price_from_url,
                            product_name=target.product_name,
                            source_name=config.source_name,
                            url=target.url,
                            location=target.location,
                        )
                    lines.append(f"OK  {target.product_name} — Rp {result.snapshot.price:,.0f}".replace(",", "."))
                    ok += 1
                except Exception as exc:
                    lines.append(f"FAIL  {target.product_name} — {exc}")
                    failed += 1

        lines.append(f"\nTotal: {ok} berhasil, {failed} gagal.")
        await context.bot.send_message(chat_id=chat_id, text="\n".join(lines))

    except Exception as exc:
        logger.exception("Price crawl-all failed for chat %s", chat_id)
        await context.bot.send_message(chat_id=chat_id, text=f"Crawl harga gagal: {exc}")


async def crawl_harga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return
    chat = update.effective_chat
    if chat is None:
        return

    if PRICE_CRAWL_LOCK.locked():
        await update.effective_message.reply_text("Crawl harga sedang berjalan. Tunggu dulu.")
        return

    targets = list_active_targets()
    await update.effective_message.reply_text(
        f"Crawl harga dimulai untuk {len(targets)} produk. Proses di background (bisa 1-2 menit)..."
    )
    context.application.create_task(_run_price_crawl_all(context, chat.id))


# ---------------------------------------------------------------------------
# /status — ringkasan kondisi DB (admin only)
# ---------------------------------------------------------------------------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_admin(update):
        return

    try:
        stats = await asyncio.to_thread(_fetch_db_stats)
        await update.effective_message.reply_text(stats)
    except Exception as exc:
        await update.effective_message.reply_text(f"Gagal ambil status: {exc}")


def _fetch_db_stats() -> str:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from crawling_bot.database import session_scope
    from database_migration.models.article import Article
    from database_migration.models.product import ProductPriceSnapshot
    from database_migration.models.signal import Signal

    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    with session_scope() as session:
        total_articles = session.scalar(select(func.count(Article.id))) or 0
        articles_24h = session.scalar(
            select(func.count(Article.id)).where(Article.crawled_at >= cutoff_24h)
        ) or 0
        total_signals = session.scalar(select(func.count(Signal.id))) or 0
        signals_24h = session.scalar(
            select(func.count(Signal.id)).where(Signal.created_at >= cutoff_24h)
        ) or 0
        total_prices = session.scalar(select(func.count(ProductPriceSnapshot.id))) or 0
        prices_7d = session.scalar(
            select(func.count(ProductPriceSnapshot.id)).where(
                ProductPriceSnapshot.observed_at >= cutoff_7d
            )
        ) or 0
        last_crawl = session.scalar(
            select(func.max(Article.crawled_at))
        )

    last_crawl_text = (
        last_crawl.strftime("%d %b %Y %H:%M UTC") if last_crawl else "belum ada data"
    )

    return (
        "Status DB Sorota Business Assistant\n\n"
        f"Artikel total   : {total_articles:,}\n"
        f"Artikel 24 jam  : {articles_24h:,}\n"
        f"Signal total    : {total_signals:,}\n"
        f"Signal 24 jam   : {signals_24h:,}\n"
        f"Snapshot harga  : {total_prices:,} (7 hari: {prices_7d:,})\n"
        f"Crawl terakhir  : {last_crawl_text}\n\n"
        "Gunakan /crawl untuk update berita, /crawl_harga untuk update harga."
    )
