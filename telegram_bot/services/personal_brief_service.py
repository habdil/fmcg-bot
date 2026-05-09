from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram_bot.services.memory_service import ChatMemoryPreferences, get_chat_memory

DEFAULT_TIMEZONE = "Asia/Jakarta"


def build_personalized_brief(chat_id: int | str) -> str:
    memory = get_chat_memory(chat_id)
    return compose_personalized_brief(memory)


def compose_personalized_brief(memory: ChatMemoryPreferences | None, *, now: datetime | None = None) -> str:
    greeting = _greeting(now)
    if memory is None or not _has_business_profile(memory):
        return (
            f"{greeting}. Aku bisa bikin brief harian yang lebih nyambung kalau aku tahu konteks bisnismu.\n"
            "Coba kirim: aku jual ayam geprek di Bandung, target margin 30%, supplier utama Pasar Ciroyom."
        )

    subject = _business_subject(memory)
    product_text = _product_text(memory)
    margin_text = _margin_text(memory.target_margin_percent)
    location_text = f" di {memory.location}" if memory.location else ""

    lines = [
        f"{greeting}. Brief singkat untuk {subject}{location_text}:",
        f"1. Cek HPP {product_text} sebelum ubah harga jual.",
        f"2. Pantau bahan yang paling cepat menggerus margin{margin_text}.",
        "3. Kalau ada promo, batasi dulu ke menu yang marginnya paling tebal.",
    ]
    if memory.known_supplier:
        lines.append(f"4. Follow up {memory.known_supplier} untuk harga dan ketersediaan stok.")
    elif memory.risk_preference == "hati-hati":
        lines.append("4. Ambil keputusan stok konservatif sampai harga bahan lebih stabil.")
    else:
        lines.append("4. Catat harga supplier hari ini supaya rekomendasi berikutnya makin presisi.")
    return "\n".join(lines)


def _has_business_profile(memory: ChatMemoryPreferences) -> bool:
    return bool(
        memory.business_context
        or memory.business_type
        or memory.location
        or memory.product_focus
        or memory.target_margin_percent
        or memory.known_supplier
    )


def _business_subject(memory: ChatMemoryPreferences) -> str:
    if memory.business_type:
        return f"bisnis {memory.business_type}"
    if memory.product_focus:
        return f"jualan {memory.product_focus[0]}"
    return "bisnismu"


def _product_text(memory: ChatMemoryPreferences) -> str:
    products = memory.product_focus or []
    if not products:
        return "produk utama"
    if len(products) == 1:
        return products[0]
    return ", ".join(products[:2])


def _margin_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    margin = format(value, "f")
    if "." in margin:
        margin = margin.rstrip("0").rstrip(".")
    return f"; patokanmu minimal {margin}%"


def _greeting(now: datetime | None = None) -> str:
    local = _as_local(now or datetime.now(_local_timezone(DEFAULT_TIMEZONE)), _local_timezone(DEFAULT_TIMEZONE))
    hour = local.hour
    if 4 <= hour < 11:
        return "Pagi"
    if 11 <= hour < 15:
        return "Siang"
    if 15 <= hour < 18:
        return "Sore"
    return "Malam"


def _local_timezone(timezone_name: str) -> tzinfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=7), name=timezone_name)


def _as_local(value: datetime, tz: tzinfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)
