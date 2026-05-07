from __future__ import annotations

import asyncio
from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes

from crawling_bot.services.price_analysis_service import get_price_movement
from crawling_bot.services.price_snapshot_service import (
    PriceSnapshotInput,
    collect_price_from_url,
    parse_price,
    save_price_snapshot,
)
from telegram_bot.services.telegram_service import reject_if_not_allowed


async def price_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    product = " ".join(context.args).strip()
    if not product:
        await update.effective_message.reply_text("Gunakan format: /price_check <produk>")
        return
    summary = await asyncio.to_thread(get_price_movement, product, 7)
    await update.effective_message.reply_text(_format_price_summary(summary))


async def price_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    raw = " ".join(context.args).strip()
    parsed = _parse_price_add(raw)
    if parsed is None:
        await update.effective_message.reply_text(
            "Gunakan format:\n"
            "/price_add produk | harga | sumber | url | lokasi\n\n"
            "Contoh:\n"
            "/price_add gula pasir 1 kg | 16900 | Katalog Supplier A | https://example.com/gula | Jakarta"
        )
        return
    try:
        snapshot = await asyncio.to_thread(save_price_snapshot, parsed)
    except Exception as exc:
        await update.effective_message.reply_text(f"Gagal menyimpan harga: {exc}")
        return
    await update.effective_message.reply_text(
        "Harga berhasil disimpan.\n"
        f"Produk: {snapshot.product_name}\n"
        f"Harga: {_format_money(snapshot.price)}\n"
        f"Sumber: {snapshot.source_name}\n"
        f"Waktu cek: {snapshot.observed_at:%d %b %Y %H:%M}"
    )


async def price_collect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await reject_if_not_allowed(update):
        return
    raw = " ".join(context.args).strip()
    parts = [item.strip() for item in raw.split("|")]
    if len(parts) < 3:
        await update.effective_message.reply_text(
            "Gunakan format:\n"
            "/price_collect produk | sumber | url | lokasi\n\n"
            "Catatan: URL harus halaman harga/katalog yang memang boleh dicek."
        )
        return
    product, source, url = parts[:3]
    location = parts[3] if len(parts) >= 4 and parts[3] else None
    try:
        result = await asyncio.to_thread(
            collect_price_from_url,
            product_name=product,
            source_name=source,
            url=url,
            location=location,
        )
    except Exception as exc:
        await update.effective_message.reply_text(f"Gagal mengambil harga dari URL: {exc}")
        return
    await update.effective_message.reply_text(
        "Harga dari URL berhasil disimpan.\n"
        f"Produk: {result.snapshot.product_name}\n"
        f"Harga terbaca: {_format_money(result.snapshot.price)}\n"
        f"Cuplikan: {result.matched_price_text}\n"
        f"Kandidat harga di halaman: {result.candidate_count}\n"
        f"Sumber: {result.snapshot.source_name}\n"
        f"URL: {result.snapshot.reference_url or result.snapshot.source_url}"
    )


def _parse_price_add(raw: str) -> PriceSnapshotInput | None:
    parts = [item.strip() for item in raw.split("|")]
    if len(parts) < 4:
        return None
    product, price_text, source, url = parts[:4]
    location = parts[4] if len(parts) >= 5 and parts[4] else None
    price = parse_price(price_text)
    if not product or price is None or not source:
        return None
    return PriceSnapshotInput(
        product_name=product,
        price=price,
        source_name=source,
        source_url=url or None,
        reference_label=f"{source} - {product}",
        reference_url=url or None,
        capture_method="manual_telegram",
        raw_price_text=price_text,
        location=location,
    )


def _format_price_summary(summary) -> str:
    if not summary.has_price_data:
        return (
            f"Maaf, kami belum berhasil menemukan harga {summary.product} dari sumber yang kami cek.\n\n"
            "Isi dulu dengan /price_add atau /price_collect kalau Anda punya sumber harga yang boleh dicek."
        )
    lines = [
        f"Harga yang berhasil kami pantau untuk {summary.product}",
    ]
    if summary.lowest_price is not None and summary.highest_price is not None:
        lines.append(f"Kisaran: {_format_money(summary.lowest_price)} - {_format_money(summary.highest_price)}")
    if summary.average_price is not None:
        lines.append(f"Rata-rata: {_format_money(summary.average_price)}")
    lines.append(f"Jumlah data: {summary.snapshot_count}")
    if summary.latest_observed_at:
        lines.append(f"Cek terakhir: {summary.latest_observed_at:%d %b %Y %H:%M}")
    if summary.source_references:
        lines.append("")
        lines.append("Sumber:")
        for reference in summary.source_references[:5]:
            lines.append(f"- {reference.reference_label or reference.source_name}")
            url = reference.reference_url or reference.source_url
            if url:
                lines.append(f"  {url}")
    lines.append("")
    lines.append("Data ini pembanding awal, bukan patokan final harga supplier.")
    return "\n".join(lines)


def _format_money(value: Decimal) -> str:
    amount = int(value)
    return f"Rp {amount:,}".replace(",", ".")
