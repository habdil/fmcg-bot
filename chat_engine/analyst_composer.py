from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any

from chat_engine.ai.base import AIProvider
from chat_engine.ai.router import AIRouter
from chat_engine.schemas import ChatQueryPlan, UserContext
from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary

logger = logging.getLogger(__name__)

FORBIDDEN_USER_TERMS = ["signal", "signal_type", "evidence_text", "source_coverage", "snapshot_count"]

DEVELOPMENT_LABELS = {
    "price_increase": "tekanan harga naik",
    "price_decrease": "harga mulai melemah",
    "shortage": "risiko stok terbatas",
    "oversupply": "stok berlebih",
    "distribution_disruption": "distribusi berpotensi terganggu",
    "demand_increase": "permintaan mulai menguat",
    "demand_decrease": "permintaan melemah",
    "negative_sentiment": "isu negatif terhadap produk atau brand",
    "positive_sentiment": "minat pasar terlihat positif",
    "regulation_change": "perubahan aturan atau kebijakan",
}


class AnalystComposer:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or AIRouter().composer_provider()

    def compose(
        self,
        *,
        plan: ChatQueryPlan,
        rows: list[dict[str, Any]],
        price_summary: PriceMovementSummary,
        availability_summary: AvailabilitySummary,
        user_context: UserContext | None = None,
    ) -> str:
        fallback = self._compose_fallback(
            plan=plan,
            rows=rows,
            price_summary=price_summary,
            availability_summary=availability_summary,
            user_context=user_context,
        )
        if plan.intent == "daily_brief":
            return fallback
        if not self.provider.is_configured:
            return fallback

        prompt = self._prompt(plan, rows, price_summary, availability_summary, user_context)
        try:
            answer = self.provider.generate_text(prompt).strip()
            if _has_forbidden_terms(answer):
                logger.warning("AI answer contained internal terms, using fallback.")
                return fallback
            return answer or fallback
        except Exception as exc:  # pragma: no cover - provider fallback
            logger.warning("Analyst composer AI failed, using fallback: %s", exc)
            return fallback

    def _compose_fallback(
        self,
        *,
        plan: ChatQueryPlan,
        rows: list[dict[str, Any]],
        price_summary: PriceMovementSummary,
        availability_summary: AvailabilitySummary,
        user_context: UserContext | None,
    ) -> str:
        product_label = _product_label(plan)
        has_price = price_summary.snapshot_count > 0
        if plan.intent == "daily_brief":
            return _latest_news_message(plan, rows, user_context)
        if plan.price_snapshot_needed and not has_price:
            return _price_not_found_message(plan, rows)

        if not rows and not has_price:
            return (
                "Intinya\n"
                f"Saya belum menemukan informasi bisnis yang cukup jelas untuk {product_label} dari sumber yang berhasil dicek.\n\n"
                "Yang sebaiknya dilakukan\n"
                "- Coba gunakan kata kunci produk yang lebih spesifik.\n"
                "- Jika butuh harga, sertakan ukuran produk dan wilayah.\n\n"
                "Catatan\n"
                "Untuk saat ini saya tidak akan menyimpulkan harga, stok, atau arah pasar tanpa dasar informasi yang cukup."
            )

        counts = Counter(str(row.get("signal_type") or "unknown") for row in rows)
        developments = _top_developments(counts)
        sources = _format_sources(rows)
        price_block = _format_price_block(price_summary, plan.price_snapshot_needed)
        availability_text = _availability_text(availability_summary, counts)
        business_note = _business_note(counts, user_context)
        reason = _best_reason(rows)

        lines = [
            "Intinya",
            _summary_sentence(product_label, developments, has_price),
            "",
            "Apa yang terjadi",
            developments or "- Belum ada perkembangan kuat, tetapi ada beberapa berita yang relevan untuk dipantau.",
        ]
        if price_block:
            lines.extend(["", "Harga", price_block])
        lines.extend(
            [
                "",
                "Pasokan dan permintaan",
                availability_text,
                "",
                "Kenapa ini penting",
                reason,
                "",
                "Dampak untuk bisnis Anda",
                business_note,
                "",
                "Yang sebaiknya dilakukan",
                _recommendations(counts, has_price, plan.price_snapshot_needed),
            ]
        )
        if sources:
            lines.extend(["", "Sumber", sources])
        lines.extend(["", "Catatan", _limitation_text(has_price, plan.price_snapshot_needed, rows)])
        return "\n".join(lines).strip()

    def _prompt(
        self,
        plan: ChatQueryPlan,
        rows: list[dict[str, Any]],
        price_summary: PriceMovementSummary,
        availability_summary: AvailabilitySummary,
        user_context: UserContext | None,
    ) -> str:
        return (
            "Anda adalah asisten analis bisnis untuk user FMCG, retail, grosir, dan distribusi.\n"
            "Tulis jawaban Bahasa Indonesia yang natural, tidak teknis, dan bisa dipakai untuk keputusan operasional.\n"
            "Jangan memakai kata 'signal', 'signal_type', 'evidence_text', 'source coverage', atau label database lain.\n"
            "Jangan mengarang harga, sumber, stok, sebab, atau jadwal.\n"
            "Jika user bertanya harga dan price_summary.snapshot_count=0, wajib tulis: "
            "'Maaf, kami belum berhasil menemukan harga untuk produk ini dari sumber yang kami cek.'\n"
            "Jika menyebut harga, sertakan sumber dan waktu cek jika tersedia.\n"
            "Selalu jelaskan kenapa informasi ini penting untuk bisnis user.\n\n"
            f"User response style memory: {_style_notes(user_context) or 'not set'}\n"
            f"User profile: {user_context}\n"
            f"Plan: {plan.model_dump()}\n"
            f"Selected rows: {[_compact_row(row) for row in rows]}\n"
            f"Price summary: {price_summary.model_dump(mode='json')}\n"
            f"Availability summary: {availability_summary.model_dump(mode='json')}\n"
        )


def _product_label(plan: ChatQueryPlan) -> str:
    parts = [plan.product or plan.normalized_question or "topik ini"]
    if plan.pack_size:
        parts.append(plan.pack_size)
    if plan.location:
        parts.append(f"di {plan.location}")
    return " ".join(parts)


def _price_not_found_message(plan: ChatQueryPlan, rows: list[dict[str, Any]]) -> str:
    product_label = _product_label(plan)
    message = (
        "Intinya\n"
        f"Maaf, kami belum berhasil menemukan harga {product_label} dari sumber yang kami cek.\n\n"
        "Catatan\n"
        "Untuk sementara, analisis ini memakai berita dan pembahasan publik yang berhasil kami temukan. "
        "Jadi rekomendasinya lebih cocok dipakai sebagai bahan pantauan, bukan sebagai patokan harga beli."
    )
    sources = _format_sources(rows)
    if sources:
        message += f"\n\nSumber\n{sources}"
    return message


def _top_developments(counts: Counter[str]) -> str:
    if not counts:
        return ""
    lines = []
    for signal_type, count in counts.most_common(4):
        label = DEVELOPMENT_LABELS.get(signal_type, "perkembangan bisnis yang perlu dipantau")
        lines.append(f"- {label} ({count} sumber/temuan)")
    return "\n".join(lines)


def _summary_sentence(product_label: str, developments: str, has_price: bool) -> str:
    if has_price and developments:
        return f"Untuk {product_label}, ada data harga yang berhasil dipantau dan beberapa perkembangan bisnis yang perlu diperhatikan."
    if has_price:
        return f"Untuk {product_label}, ada data harga yang berhasil dipantau dari sumber yang dicek."
    if developments:
        return f"Untuk {product_label}, ada beberapa perkembangan bisnis yang perlu dipantau sebelum mengambil keputusan stok atau harga."
    return f"Untuk {product_label}, informasi yang tersedia masih terbatas."


def _format_price_block(price: PriceMovementSummary, user_asked_price: bool) -> str:
    if price.snapshot_count <= 0:
        if user_asked_price:
            return "Maaf, kami belum berhasil menemukan harga untuk produk ini dari sumber yang kami cek."
        return ""

    parts = ["Harga yang berhasil kami pantau:"]
    if price.lowest_price is not None and price.highest_price is not None:
        if price.lowest_price == price.highest_price:
            parts.append(f"- Harga terlihat di sekitar {_format_money(price.lowest_price, price.currency)}.")
        else:
            parts.append(
                f"- Kisaran harga terlihat antara {_format_money(price.lowest_price, price.currency)} "
                f"sampai {_format_money(price.highest_price, price.currency)}."
            )
    if price.average_price is not None:
        parts.append(f"- Rata-rata sederhana: {_format_money(price.average_price, price.currency)}.")
    if price.latest_observed_at:
        parts.append(f"- Waktu cek terakhir: {_format_datetime(price.latest_observed_at)}.")
    if price.source_references:
        parts.append("- Sumber harga:")
        for reference in price.source_references[:3]:
            label = reference.reference_label or reference.source_name
            url = reference.reference_url or reference.source_url
            observed = f" ({_format_datetime(reference.observed_at)})" if reference.observed_at else ""
            parts.append(f"  - {label}{observed}")
            if url:
                parts.append(f"    {url}")
    parts.append("- Gunakan ini sebagai pembanding awal, bukan patokan final harga supplier.")
    return "\n".join(parts)


def _availability_text(availability: AvailabilitySummary, counts: Counter[str]) -> str:
    if availability.total_snapshots:
        return (
            f"- Ada {availability.total_snapshots} data ketersediaan yang berhasil dicek. "
            f"Kondisi umum: {availability.availability_signal}."
        )
    risk_count = counts["shortage"] + counts["distribution_disruption"]
    if risk_count:
        return f"- Ada {risk_count} pembahasan yang mengarah ke risiko stok atau distribusi. Ini perlu divalidasi ke supplier."
    return "- Belum ada data stok yang cukup jelas. Pantau supplier dan berita terbaru sebelum mengambil stok besar."


def _business_note(counts: Counter[str], user_context: UserContext | None) -> str:
    base = []
    if counts["price_increase"]:
        base.append("margin bisa tertekan jika harga supplier ikut naik")
    if counts["shortage"] or counts["distribution_disruption"]:
        base.append("ketersediaan barang dan lead time perlu dicek lebih sering")
    if counts["demand_increase"]:
        base.append("alokasi stok untuk produk cepat jalan bisa jadi lebih penting")
    if not base:
        base.append("informasi ini sebaiknya dipakai sebagai bahan pantauan sebelum keputusan pembelian")

    prefix = "Untuk bisnis Anda"
    if user_context and user_context.business_type:
        prefix = f"Untuk bisnis {user_context.business_type.replace('_', ' ')} Anda"
    return f"{prefix}, " + ", ".join(base) + "."


def _recommendations(counts: Counter[str], has_price: bool, user_asked_price: bool) -> str:
    items = []
    if has_price:
        items.append("Bandingkan harga yang terpantau dengan harga supplier langsung sebelum mengambil stok.")
    elif user_asked_price:
        items.append("Cek harga supplier langsung karena sumber publik yang dicek belum memberi harga yang bisa dipakai.")
    if counts["price_increase"]:
        items.append("Siapkan skenario penyesuaian margin jika supplier mulai menaikkan harga.")
    if counts["shortage"] or counts["distribution_disruption"]:
        items.append("Validasi ketersediaan barang dan siapkan alternatif supplier untuk SKU cepat jalan.")
    if counts["demand_increase"]:
        items.append("Prioritaskan alokasi stok ke channel atau area dengan perputaran lebih cepat.")
    if not items:
        items.append("Pantau update berikutnya dan jangan membuat keputusan besar dari satu sumber saja.")
    return "\n".join(f"- {item}" for item in items[:5])


def _best_reason(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        reason = str(row.get("reason") or "").strip()
        if reason and "not clearly stated" not in reason.lower():
            return reason
    for row in rows:
        text = str(row.get("evidence_text") or row.get("title") or "").strip()
        if text:
            return text
    return "Sumber yang dicek belum menjelaskan penyebabnya secara kuat. Gunakan informasi ini sebagai bahan pantauan."


def _format_sources(rows: list[dict[str, Any]], limit: int = 5) -> str:
    lines = []
    seen: set[str] = set()
    for row in rows:
        url = str(row.get("article_url") or "").strip()
        title = str(row.get("title") or "-").strip()
        source = str(row.get("source_name") or "-").strip()
        key = url or f"{source}:{title}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{len(lines) + 1}. {source} - {_trim(title, 110)}")
        if url:
            lines.append(f"   {url}")
        if len(lines) // 2 >= limit:
            break
    return "\n".join(lines)


def _latest_news_message(
    plan: ChatQueryPlan,
    rows: list[dict[str, Any]],
    user_context: UserContext | None,
) -> str:
    topic = "bisnis dan FMCG"
    if plan.product:
        topic = plan.product
    elif plan.location:
        topic = f"bisnis di {plan.location}"

    if not rows:
        return (
            f"Berita terbaru {topic}\n\n"
            "Saya belum menemukan berita terbaru yang cukup jelas dari sumber publik yang berhasil dicek.\n\n"
            "Catatan\n"
            "- Coba pakai keyword yang lebih spesifik, misalnya: berita terbaru gula, harga beras, atau stok minyak goreng.\n"
            "- Bot tidak akan mengarang judul berita, sumber, atau isi berita kalau datanya belum ada."
        )

    prefers_short = _prefers_short_answer(user_context)
    include_notes = not _prefers_no_notes(user_context)
    limit = 3 if prefers_short else 5

    lines = [f"Berita terbaru {topic}"]
    for index, row in enumerate(rows[:limit], start=1):
        title = _trim(str(row.get("title") or "Tanpa judul").strip(), 120)
        source = str(row.get("source_name") or "Sumber tidak tercatat").strip()
        url = str(row.get("article_url") or "").strip()
        published_at = row.get("published_at") or row.get("created_at") or row.get("crawled_at")
        date_text = (
            _format_datetime(published_at)
            if isinstance(published_at, datetime)
            else "tanggal tidak tercatat"
        )
        essence = _news_essence(row)
        business_angle = _news_business_angle(row)

        lines.extend(
            [
                "",
                f"{index}. {title}",
                f"Intinya: {essence}",
                f"Dampak bisnis: {business_angle}",
                f"Sumber: {source} ({date_text})",
            ]
        )
        if url:
            lines.append(f"Link: {url}")

    if include_notes:
        lines.extend(
            [
                "",
                "Catatan",
                "- Ringkasan ini hanya memakai sumber yang sudah berhasil dicrawl dan tersimpan.",
                "- Untuk keputusan stok, harga, atau pembelian, tetap validasi ke supplier dan kondisi wilayah Anda.",
            ]
        )
    return "\n".join(lines).strip()


def _news_essence(row: dict[str, Any]) -> str:
    for key in ["ai_polished_summary", "reason", "evidence_text", "explanation"]:
        value = str(row.get(key) or "").strip()
        if value and "not clearly stated" not in value.lower():
            return _trim(value, 220)
    return _trim(str(row.get("title") or "Isi berita belum cukup jelas dari data yang tersimpan."), 220)


def _news_business_angle(row: dict[str, Any]) -> str:
    signal_type = str(row.get("signal_type") or "")
    label = DEVELOPMENT_LABELS.get(signal_type)
    if label:
        return f"Ini mengarah ke {label}, jadi perlu dipantau untuk keputusan harga, stok, atau distribusi."
    urgency = str(row.get("urgency") or "").lower()
    if urgency == "high":
        return "Berita ini punya prioritas tinggi untuk dipantau sebelum mengambil keputusan operasional."
    return "Berita ini relevan sebagai bahan pantauan pasar dan keputusan operasional."


def _limitation_text(has_price: bool, user_asked_price: bool, rows: list[dict[str, Any]]) -> str:
    items = []
    if user_asked_price and not has_price:
        items.append("Harga belum berhasil ditemukan dari sumber yang dicek.")
    if not rows:
        items.append("Belum ada berita atau sumber publik yang cukup kuat untuk topik ini.")
    items.append("Validasi ulang dengan harga supplier, stok internal, dan kondisi wilayah sebelum keputusan operasional.")
    return "\n".join(f"- {item}" for item in items)


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "development_type": DEVELOPMENT_LABELS.get(str(row.get("signal_type") or ""), "perkembangan bisnis"),
        "product": row.get("product"),
        "location": row.get("location"),
        "reason": row.get("reason"),
        "basis": row.get("evidence_text"),
        "title": row.get("title"),
        "source_name": row.get("source_name"),
        "article_url": row.get("article_url"),
        "published_at": str(row.get("published_at") or ""),
    }


def _format_money(value: Decimal, currency: str = "IDR") -> str:
    amount = int(value.quantize(Decimal("1")))
    if currency.upper() == "IDR":
        return f"Rp {amount:,}".replace(",", ".")
    return f"{currency} {amount:,}"


def _format_datetime(value: datetime) -> str:
    return value.strftime("%d %b %Y %H:%M")


def _trim(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3].rstrip()}..."


def _style_notes(user_context: UserContext | None) -> str:
    if not user_context or not user_context.style_instructions:
        return ""
    return user_context.style_instructions.strip()


def _prefers_short_answer(user_context: UserContext | None) -> bool:
    notes = _style_notes(user_context).lower()
    return any(term in notes for term in ["singkat", "pendek", "ringkas", "to the point", "langsung"])


def _prefers_no_notes(user_context: UserContext | None) -> bool:
    notes = _style_notes(user_context).lower()
    return any(term in notes for term in ["tanpa catatan", "jangan ada catatan", "no notes"])


def _has_forbidden_terms(answer: str) -> bool:
    lowered = answer.lower()
    return any(term.lower() in lowered for term in FORBIDDEN_USER_TERMS)
