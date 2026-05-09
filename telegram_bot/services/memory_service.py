from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from crawling_bot.database import session_scope
from database_migration.models.chat_memory import UserMemory


MAX_STYLE_CHARS = 800


@dataclass(frozen=True)
class ChatMemoryPreferences:
    response_style_notes: str | None = None
    business_context: str | None = None
    preferred_topics: str | None = None
    feedback_notes: str | None = None
    business_type: str | None = None
    location: str | None = None
    product_focus: list[str] | None = None
    target_margin_percent: Decimal | None = None
    known_supplier: str | None = None
    pricing_preference: str | None = None
    risk_preference: str | None = None


STYLE_PATTERNS = [
    re.compile(
        r"^(?:ingat|simpan|catat)\s+(?:gaya|style|preferensi)(?:\s+jawaban)?\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:atur|set)\s+(?:gaya|style|preferensi)(?:\s+jawaban)?\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:mulai sekarang|kedepannya|ke depannya)\s+(?:jawab|respon|balas)\s+(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:saya|aku)\s+mau\s+(?:jawaban|respon|balasan)(?:nya)?\s+(.+)$",
        re.IGNORECASE,
    ),
]

BUSINESS_TYPE_KEYWORDS = {
    "kuliner": ["kuliner", "makanan", "minuman", "ayam geprek", "warung makan", "resto", "cafe", "coffee shop", "kopi"],
    "retail": ["retail", "toko", "warung", "kelontong", "sembako"],
    "fashion": ["fashion", "baju", "pakaian", "hijab"],
    "laundry": ["laundry", "cuci kiloan"],
    "reseller": ["reseller", "dropship", "jualan online", "online shop"],
}

LOCATION_RE = re.compile(
    r"\b(?:di|lokasi(?:\s+saya|\s+kami|nya)?(?:\s+di)?|domisili(?:\s+saya|\s+kami|nya)?|area)\s+"
    r"([A-Za-z .'-]{3,40})",
    re.IGNORECASE,
)
TARGET_MARGIN_RE = re.compile(r"\b(?:target\s+)?margin(?:\s+minimal)?\s*(\d+(?:[,.]\d+)?)\s*%", re.IGNORECASE)
SUPPLIER_RE = re.compile(
    r"\b(?:supplier(?:\s+saya|\s+kami)?|pemasok|ambil(?:\s+barang)?\s+dari)\s+"
    r"([A-Za-z0-9 .,'&-]{3,60})",
    re.IGNORECASE,
)
PRODUCT_RE = re.compile(
    r"\b(?:saya|aku|kami)?\s*(?:jual|jualan|menjual|produk(?:\s+utama)?(?:\s+saya|\s+kami)?|menu(?:\s+utama)?(?:\s+saya|\s+kami)?)\s+"
    r"([A-Za-z0-9 .,'&/-]{3,80})",
    re.IGNORECASE,
)


def extract_style_instruction(message: str) -> str | None:
    normalized = " ".join((message or "").strip().split())
    if not normalized:
        return None
    for pattern in STYLE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return _clean_style_notes(match.group(1))
    return None


def get_chat_memory(chat_id: int | str) -> ChatMemoryPreferences | None:
    try:
        with session_scope() as session:
            preference_memories = session.scalars(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "preference",
                )
            ).all()
            profile_memory = session.scalar(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "business_profile",
                    UserMemory.memory_key == "structured_profile",
                )
            )
            if not preference_memories and profile_memory is None:
                return None
            values = {memory.memory_key: memory.memory_text for memory in preference_memories}
            profile = profile_memory.memory_json if profile_memory and isinstance(profile_memory.memory_json, dict) else {}
            return ChatMemoryPreferences(
                response_style_notes=values.get("response_style_notes"),
                business_context=values.get("business_context") or _business_context_text(profile),
                preferred_topics=values.get("preferred_topics"),
                feedback_notes=values.get("feedback_notes"),
                business_type=_str_or_none(profile.get("business_type")),
                location=_str_or_none(profile.get("location")),
                product_focus=list(profile.get("main_products") or []),
                target_margin_percent=_decimal_or_none(profile.get("target_margin_percent")),
                known_supplier=_str_or_none(profile.get("known_supplier")),
                pricing_preference=_str_or_none(profile.get("pricing_preference")),
                risk_preference=_str_or_none(profile.get("risk_preference")),
            )
    except SQLAlchemyError:
        return None


def save_response_style(chat_id: int | str, username: str | None, notes: str) -> str:
    cleaned = _clean_style_notes(notes)
    if not cleaned:
        raise ValueError("Instruksi gaya jawaban kosong.")
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "preference",
                    UserMemory.memory_key == "response_style_notes",
                )
            )
            if memory is None:
                memory = UserMemory(
                    channel="telegram",
                    channel_user_id=str(chat_id),
                    memory_type="preference",
                    memory_key="response_style_notes",
                    source="explicit_user_instruction",
                )
                session.add(memory)
            memory.username = username
            memory.memory_text = cleaned
        return cleaned
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory belum aktif. Jalankan migrasi database dulu.") from exc


def extract_business_facts(message: str) -> dict[str, Any]:
    normalized = " ".join((message or "").strip().split())
    lowered = normalized.lower()
    if not normalized:
        return {}

    facts: dict[str, Any] = {}
    for business_type, keywords in BUSINESS_TYPE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            facts["business_type"] = business_type
            break

    location_match = LOCATION_RE.search(normalized)
    if location_match:
        facts["location"] = _clean_fact(location_match.group(1))

    margin_match = TARGET_MARGIN_RE.search(normalized)
    if margin_match:
        facts["target_margin_percent"] = margin_match.group(1).replace(",", ".")

    supplier_match = SUPPLIER_RE.search(normalized)
    if supplier_match:
        facts["known_supplier"] = _clean_fact(supplier_match.group(1))

    product_match = PRODUCT_RE.search(normalized)
    if product_match:
        products = _split_products(product_match.group(1))
        if products:
            facts["main_products"] = products

    if any(term in lowered for term in ["jangan terlalu berisiko", "hati-hati", "konservatif", "stok besar"]):
        facts["risk_preference"] = "hati-hati"
    if any(term in lowered for term in ["harga kompetitif", "jangan kemahalan", "murah tapi margin"]):
        facts["pricing_preference"] = "kompetitif tapi margin tetap aman"

    return facts


def save_business_facts(chat_id: int | str, username: str | None, facts: dict[str, Any]) -> ChatMemoryPreferences | None:
    if not facts:
        return get_chat_memory(chat_id)
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "business_profile",
                    UserMemory.memory_key == "structured_profile",
                )
            )
            if memory is None:
                memory = UserMemory(
                    channel="telegram",
                    channel_user_id=str(chat_id),
                    memory_type="business_profile",
                    memory_key="structured_profile",
                    source="chat_extraction",
                )
                session.add(memory)
            profile = memory.memory_json if isinstance(memory.memory_json, dict) else {}
            merged = _merge_profile(profile, facts)
            memory.username = username
            memory.memory_json = merged
            memory.memory_text = _business_context_text(merged)
        return get_chat_memory(chat_id)
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory bisnis belum aktif. Jalankan migrasi database dulu.") from exc


def save_business_context_text(chat_id: int | str, username: str | None, text: str) -> str:
    cleaned = " ".join(text.strip().split())[:1200]
    if not cleaned:
        raise ValueError("Konteks bisnis kosong.")
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "preference",
                    UserMemory.memory_key == "business_context",
                )
            )
            if memory is None:
                memory = UserMemory(
                    channel="telegram",
                    channel_user_id=str(chat_id),
                    memory_type="preference",
                    memory_key="business_context",
                    source="explicit_user_instruction",
                )
                session.add(memory)
            memory.username = username
            memory.memory_text = cleaned
        return cleaned
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory belum aktif. Jalankan migrasi database dulu.") from exc


def clear_response_style(chat_id: int | str) -> None:
    try:
        with session_scope() as session:
            memory = session.scalar(
                select(UserMemory).where(
                    UserMemory.channel == "telegram",
                    UserMemory.channel_user_id == str(chat_id),
                    UserMemory.memory_type == "preference",
                    UserMemory.memory_key == "response_style_notes",
                )
            )
            if memory is not None:
                memory.memory_text = None
    except SQLAlchemyError as exc:
        raise RuntimeError("Memory belum aktif. Jalankan migrasi database dulu.") from exc


def _clean_style_notes(value: str) -> str:
    return " ".join(value.strip().split())[:MAX_STYLE_CHARS]


def _clean_fact(value: str) -> str:
    cleaned = re.split(r"\b(?:dan|dengan|target|margin|supplier|produk|menu)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
    return " ".join(cleaned.strip(" .,-").split())[:80]


def _split_products(value: str) -> list[str]:
    cleaned = re.split(r"\b(?:di|dengan|target|margin|supplier|ambil|lokasi)\b", value, maxsplit=1, flags=re.IGNORECASE)[0]
    parts = re.split(r",|/|\bdan\b|\&", cleaned)
    products = []
    for part in parts:
        item = " ".join(part.strip(" .,-").split()).lower()
        if 2 < len(item) <= 50 and item not in {"saya", "aku", "kami"}:
            products.append(item)
    return list(dict.fromkeys(products))[:8]


def _merge_profile(profile: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    merged = dict(profile)
    for key, value in facts.items():
        if key == "main_products":
            existing = list(merged.get("main_products") or [])
            for product in value or []:
                if product not in existing:
                    existing.append(product)
            merged[key] = existing[:12]
        elif value not in (None, "", []):
            merged[key] = value
    return merged


def _business_context_text(profile: dict[str, Any]) -> str | None:
    if not profile:
        return None
    parts = []
    if profile.get("business_type"):
        parts.append(f"jenis usaha {profile['business_type']}")
    if profile.get("location"):
        parts.append(f"lokasi {profile['location']}")
    products = profile.get("main_products") or []
    if products:
        parts.append("produk utama " + ", ".join(products[:5]))
    if profile.get("target_margin_percent"):
        parts.append(f"target margin {profile['target_margin_percent']}%")
    if profile.get("known_supplier"):
        parts.append(f"supplier {profile['known_supplier']}")
    if profile.get("pricing_preference"):
        parts.append(f"preferensi harga {profile['pricing_preference']}")
    if profile.get("risk_preference"):
        parts.append(f"preferensi risiko {profile['risk_preference']}")
    return "Bisnis user: " + "; ".join(parts) + "."


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
