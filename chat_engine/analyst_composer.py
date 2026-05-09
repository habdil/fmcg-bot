from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any

from chat_engine.ai.base import AIProvider
from chat_engine.ai.router import AIRouter
from chat_engine.schemas import ChatQueryPlan, UserContext
from crawling_bot.schemas.price_schema import AvailabilitySummary, PriceMovementSummary

logger = logging.getLogger(__name__)

FORBIDDEN_USER_TERMS = [
    "signal",
    "signal_type",
    "evidence_text",
    "source_coverage",
    "snapshot_count",
    "database",
    "crawler",
    "crawl",
]

# Referensi seller/marketplace yang bisa direkomendasikan kalau data tidak ada di DB
_SELLER_SUGGESTIONS = (
    "Untuk cek harga atau ketersediaan langsung:\n"
    "- KlikIndogrosir (klikindogrosir.com) — grosir resmi Indogrosir\n"
    "- Panel Harga Pangan (pihp.kemendag.go.id) — referensi harga pangan Kemendag\n"
    "- Tokopedia / Shopee — bandingkan harga dari berbagai reseller\n"
    "- Marketplace B2B: Ralali, Grosir.co.id\n"
    "- Atau hubungi agen/supplier langsung untuk harga grosir terkini."
)
_SELLER_SUGGESTIONS = (
    "Cek pembanding cepat di KlikIndogrosir, PIHPS/Kemendag, marketplace, "
    "atau supplier langganan. Untuk harga beli final, tetap minta quotation langsung."
)

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
        few_shot_examples: list[Any] | None = None,
    ) -> str:
        calculation_answer = _business_calculation_answer(plan)
        if calculation_answer:
            return calculation_answer

        # Fallback hanya dipakai kalau AI tidak terkonfigurasi atau AI gagal total
        if not self.provider.is_configured:
            return self._compose_fallback(
                plan=plan,
                rows=rows,
                price_summary=price_summary,
                availability_summary=availability_summary,
                user_context=user_context,
            )

        prompt = self._prompt(
            plan,
            rows,
            price_summary,
            availability_summary,
            user_context,
            few_shot_examples=few_shot_examples,
        )
        try:
            answer = self.provider.generate_text(prompt).strip()
            if not answer or _has_forbidden_terms(answer) or _is_too_verbose(answer):
                logger.warning("AI answer empty, too verbose, or contained internal terms; using fallback.")
                return self._compose_fallback(
                    plan=plan,
                    rows=rows,
                    price_summary=price_summary,
                    availability_summary=availability_summary,
                    user_context=user_context,
                )
            return answer
        except Exception as exc:
            logger.warning("Analyst composer AI failed, using fallback: %s", exc)
            return self._compose_fallback(
                plan=plan,
                rows=rows,
                price_summary=price_summary,
                availability_summary=availability_summary,
                user_context=user_context,
            )

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
                f"Aku belum punya data yang cukup untuk {product_label} dari sumber yang sudah dicek.\n\n"
                f"{_SELLER_SUGGESTIONS}\n\n"
                "Tanya lagi dengan ukuran kemasan dan lokasi supaya hasilnya lebih presisi."
            )

        counts = Counter(str(row.get("signal_type") or "unknown") for row in rows)
        lines = [_summary_sentence(product_label, _top_developments(counts), has_price)]

        price_line = _short_price_line(price_summary, plan.price_snapshot_needed)
        if price_line:
            lines.append(price_line)

        reason = _best_reason(rows) if rows else ""
        if reason:
            lines.append(_trim(reason, 180))

        lines.append(_primary_recommendation(counts, has_price, plan.price_snapshot_needed))

        sources = _format_sources_short(rows)
        if sources:
            lines.append(sources)
        return "\n".join(lines).strip()

    def _prompt(
        self,
        plan: ChatQueryPlan,
        rows: list[dict[str, Any]],
        price_summary: PriceMovementSummary,
        availability_summary: AvailabilitySummary,
        user_context: UserContext | None,
        *,
        few_shot_examples: list[Any] | None = None,
    ) -> str:
        # ── PERSONA ─────────────────────────────────────────────────────────
        parts = [
            "Kamu adalah Sorota, advisor keputusan bisnis untuk UMKM Indonesia.",
            "Jawab seperti chat dari teman yang paham bisnis — langsung ke poin, tidak kaku, tidak berlebihan.",
            "Bahasa: Indonesia santai. Tidak perlu salam pembuka.",
            "DILARANG memakai label laporan seperti 'Intinya:', 'Dampak bisnis:', 'Rekomendasi:', 'Catatan:'.",
            "DILARANG mengarang fakta, harga, atau berita yang tidak ada di data di bawah.",
            "Maksimal 5 kalimat pendek, kecuali user minta detail.",
            "Fokus hanya pada jawaban inti, angka penting, dan saran tindakan untuk owner UMKM.",
            "Buang teori umum, daftar panjang, dan info sampingan yang tidak membantu keputusan user.",
            "Jangan menampilkan semua sumber. Sebutkan maksimal 2 sumber singkat jika memang membantu.",
            "DILARANG memakai label panjang seperti 'Pasokan dan permintaan', 'Kenapa ini penting', atau 'Dampak untuk bisnis Anda'.",
            "Kalau data tidak ada → jujur, lalu arahkan ke tempat yang bisa dicek (KlikIndogrosir, pihp.kemendag.go.id, Tokopedia, supplier langsung).",
        ]

        # ── GAYA JAWABAN (dari memory user) ─────────────────────────────────
        style = _style_notes(user_context)
        if style:
            parts.append(f"\nPreferensi gaya jawaban user ini: {style}")

        # ── KOREKSI AKTIF (feedback saat ini) ───────────────────────────────
        feedback = user_context.feedback_instruction if user_context else None
        if feedback:
            parts.append(
                f"\n[USER MINTA PERBAIKAN] {feedback}\n"
                "Langsung tulis jawaban yang memenuhi permintaan itu. Jangan sebut bahwa ini perbaikan."
            )

        # ── CONTOH KOREKSI SEBELUMNYA (few-shot) ────────────────────────────
        if few_shot_examples:
            parts.append("\nContoh cara user ini ingin dijawab (dari koreksi sebelumnya):")
            for ex in few_shot_examples[:3]:
                parts.append(f"- Ketika ditanya '{ex.question[:80]}': {ex.improved_style_note}")

        # ── PERTANYAAN USER ──────────────────────────────────────────────────
        parts.append(f"\nPertanyaan user: {plan.original_question}")
        if plan.product:
            parts.append(f"Produk yang ditanyakan: {plan.product}{' ' + plan.pack_size if plan.pack_size else ''}")
        if plan.location:
            parts.append(f"Lokasi: {plan.location}")

        # ── DATA HARGA ───────────────────────────────────────────────────────
        if price_summary.snapshot_count > 0:
            price_block = _readable_price_summary(price_summary)
            parts.append(f"\nData harga yang tersedia:\n{price_block}")
        elif plan.price_snapshot_needed:
            parts.append(
                "\nHarga pembanding belum tersedia di data yang ada. "
                "Arahkan user ke: KlikIndogrosir, pihp.kemendag.go.id, Tokopedia, atau supplier langsung."
            )

        # ── DATA BERITA/SIGNAL ───────────────────────────────────────────────
        if rows:
            parts.append(f"\nBerita/informasi relevan yang ditemukan ({len(rows)} item):")
            for i, row in enumerate(rows[:4], 1):
                title = _trim(str(row.get("title") or ""), 100)
                summary = _trim(str(row.get("ai_polished_summary") or row.get("reason") or row.get("evidence_text") or ""), 140)
                source = str(row.get("source_name") or "")
                pub = row.get("published_at")
                date_str = _format_datetime(pub) if isinstance(pub, datetime) else ""
                line = f"{i}. {title}"
                if summary:
                    line += f"\n   {summary}"
                if source:
                    line += f"\n   Sumber: {source}"
                    if date_str:
                        line += f" ({date_str})"
                parts.append(line)
        else:
            parts.append("\nTidak ada berita/data yang ditemukan untuk topik ini.")

        # ── INSTRUKSI AKHIR ──────────────────────────────────────────────────
        if plan.intent == "daily_brief":
            parts.append(
                "\nTulis ringkasan berita di atas dengan gaya natural — seperti update singkat dari teman. "
                "Pilih maksimal 3 berita paling penting. Satu berita cukup 1 kalimat inti + sumber."
            )
        else:
            parts.append(
                "\nJawab pertanyaan user berdasarkan data di atas. "
                "Langsung ke keputusan praktis. Jangan melebar."
            )

        return "\n".join(parts)


def _product_label(plan: ChatQueryPlan) -> str:
    parts = [plan.product or plan.normalized_question or "topik ini"]
    if plan.pack_size:
        parts.append(plan.pack_size)
    if plan.location:
        parts.append(f"di {plan.location}")
    return " ".join(parts)


def _business_calculation_answer(plan: ChatQueryPlan) -> str:
    text = plan.original_question.lower()
    if not any(term in text for term in ["hpp", "modal", "margin", "markup", "laba", "untung", "profit", "harga jual"]):
        return ""

    cost = _extract_labeled_money(text, ["hpp", "modal", "biaya pokok", "harga pokok"])
    selling_price = _extract_labeled_money(text, ["harga jual", "jual", "dijual"])
    if cost is None or selling_price is None or selling_price <= 0:
        return ""

    gross_profit = selling_price - cost
    margin_percent = (gross_profit / selling_price) * Decimal("100")
    markup_percent = (gross_profit / cost) * Decimal("100") if cost > 0 else Decimal("0")
    target_margin = _extract_target_margin(text) or Decimal("30")

    if margin_percent >= target_margin:
        opening = (
            f"Masih cukup aman. Margin kotornya sekitar {_format_percent(margin_percent)}, "
            f"di atas patokan {_format_percent(target_margin)}."
        )
    else:
        opening = (
            f"Belum aman kalau target margin Anda {_format_percent(target_margin)}. "
            f"Margin kotornya baru sekitar {_format_percent(margin_percent)}."
        )

    lines = [
        opening,
        f"HPP {_format_money(cost)} dan harga jual {_format_money(selling_price)} memberi laba kotor {_format_money(gross_profit)} per item.",
        f"Markup-nya sekitar {_format_percent(markup_percent)} dari HPP.",
    ]

    if margin_percent >= target_margin:
        lines.append("Tetap cek biaya kemasan, komisi platform, promo, dan waste. Kalau biaya tambahan belum masuk, jangan diskon dulu.")
    else:
        recommended_price = _recommended_selling_price(cost, target_margin)
        lines.append(f"Agar lebih sehat, harga jual perlu mendekati {_format_money(recommended_price)} atau HPP harus ditekan.")
    return "\n".join(lines)


def _extract_labeled_money(text: str, labels: list[str]) -> Decimal | None:
    for label in labels:
        pattern = rf"{re.escape(label)}(?:(?!\d).){{0,50}}(?:rp\.?\s*)?(\d[\d.,]*)"
        match = re.search(pattern, text)
        if match:
            return _parse_money(match.group(1))
    return None


def _parse_money(value: str) -> Decimal | None:
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    return Decimal(digits)


def _extract_target_margin(text: str) -> Decimal | None:
    if "target" not in text and "minimal" not in text and "margin" not in text:
        return None
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*%", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", "."))


def _recommended_selling_price(cost: Decimal, target_margin: Decimal) -> Decimal:
    rate = target_margin / Decimal("100")
    if rate >= Decimal("0.95"):
        rate = Decimal("0.95")
    return (cost / (Decimal("1") - rate)).quantize(Decimal("1"))


def _format_percent(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.1"))
    return f"{quantized}%".replace(".", ",")


def _price_not_found_message(plan: ChatQueryPlan, rows: list[dict[str, Any]]) -> str:
    product_label = _product_label(plan)
    message = (
            f"Aku belum menemukan harga {product_label} dari sumber pembanding yang tersedia.\n\n"
        f"{_SELLER_SUGGESTIONS}"
    )
    sources = _format_sources_short(rows)
    if sources:
        message += f"\n\n{sources}"
    return message


def _top_developments(counts: Counter[str]) -> str:
    if not counts:
        return ""
    lines = []
    for signal_type, count in counts.most_common(2):
        label = DEVELOPMENT_LABELS.get(signal_type, "perkembangan bisnis yang perlu dipantau")
        suffix = f" dari {count} temuan" if count > 1 else ""
        lines.append(f"{label}{suffix}")
    return ", ".join(lines)


def _summary_sentence(product_label: str, developments: str, has_price: bool) -> str:
    if has_price and developments:
        return f"Untuk {product_label}, ada data harga dan indikasi {developments}."
    if has_price:
        return f"Untuk {product_label}, sudah ada data harga pembanding dari sumber yang dicek."
    if developments:
        return f"Untuk {product_label}, indikasi utamanya: {developments}."
    return f"Untuk {product_label}, informasi yang tersedia masih terbatas."


def _short_price_line(price: PriceMovementSummary, user_asked_price: bool) -> str:
    if price.snapshot_count <= 0:
        return "Harga belum tersedia dari sumber yang dicek." if user_asked_price else ""
    if price.lowest_price is not None and price.highest_price is not None:
        if price.lowest_price == price.highest_price:
            return f"Harga terpantau sekitar {_format_money(price.lowest_price, price.currency)}."
        return (
            f"Kisaran harga terpantau {_format_money(price.lowest_price, price.currency)}-"
            f"{_format_money(price.highest_price, price.currency)}."
        )
    if price.average_price is not None:
        return f"Rata-rata harga terpantau {_format_money(price.average_price, price.currency)}."
    return f"Ada {price.snapshot_count} data harga, tapi kisarannya belum cukup rapi."


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


def _primary_recommendation(counts: Counter[str], has_price: bool, user_asked_price: bool) -> str:
    if has_price:
        return "Pakai angka ini sebagai pembanding, lalu minta harga final ke supplier sebelum restock."
    if user_asked_price:
        return "Cek supplier langsung dulu; data publik belum cukup kuat untuk jadi patokan beli."
    if counts["price_increase"]:
        return "Jangan restock besar dulu sebelum harga supplier dikonfirmasi."
    if counts["shortage"] or counts["distribution_disruption"]:
        return "Siapkan supplier cadangan dan cek lead time sebelum ambil stok."
    if counts["demand_increase"]:
        return "Prioritaskan stok untuk produk yang perputarannya paling cepat."
    return "Pantau dulu dan jangan ambil keputusan besar dari satu sumber saja."


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


def _format_sources_short(rows: list[dict[str, Any]], limit: int = 2) -> str:
    items = []
    seen: set[str] = set()
    for row in rows:
        source = str(row.get("source_name") or "").strip()
        title = _trim(str(row.get("title") or "").strip(), 70)
        if not source and not title:
            continue
        key = f"{source}:{title}"
        if key in seen:
            continue
        seen.add(key)
        if source and title:
            items.append(f"{source} - {title}")
        else:
            items.append(source or title)
        if len(items) >= limit:
            break
    if not items:
        return ""
    return "Sumber: " + "; ".join(items)


def _latest_news_message(
    plan: ChatQueryPlan,
    rows: list[dict[str, Any]],
    user_context: UserContext | None,
) -> str:
    topic = "bisnis UMKM"
    if plan.product:
        topic = plan.product
    elif plan.location:
        topic = f"bisnis di {plan.location}"

    if not rows:
        return (
            f"Berita terbaru {topic}\n\n"
            "Belum ada berita terbaru yang berhasil ditemukan untuk topik ini.\n\n"
            "Coba tanyakan dengan kata kunci yang lebih spesifik, misalnya:\n"
            "\"berita terbaru gula\", \"update harga beras\", atau \"stok minyak goreng\"."
        )

    prefers_short = _prefers_short_answer(user_context)
    include_notes = not _prefers_no_notes(user_context)
    lines = [f"Update terbaru {topic}:"]
    for index, row in enumerate(rows[:3], start=1):
        title = _trim(str(row.get("title") or "Tanpa judul").strip(), 120)
        source = str(row.get("source_name") or "Sumber tidak tercatat").strip()
        essence = _trim(_news_essence(row), 150)
        lines.append(f"{index}. {title} - {essence} ({source})")
    if include_notes:
        lines.append("Validasi ke supplier sebelum keputusan stok atau harga.")
    return "\n".join(lines).strip()
    limit = 3 if prefers_short else 5

    lines = [f"Update terbaru — {topic}"]
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

        lines.append(f"\n{index}. {title}")
        lines.append(essence)
        if business_angle:
            lines.append(business_angle)
        lines.append(f"— {source}, {date_text}")
        if url:
            lines.append(url)

    if include_notes:
        lines.append(
            "\nData dari sumber publik yang sudah dicrawl. "
            "Validasi ke supplier sebelum keputusan pembelian."
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
    urgency = str(row.get("urgency") or "").lower()
    label = DEVELOPMENT_LABELS.get(signal_type)
    if urgency == "high" and label:
        return f"Perlu dipantau segera — ada indikasi {label}."
    if label:
        return f"Ada indikasi {label}."
    if urgency == "high":
        return "Relevansi tinggi untuk keputusan operasional."
    return ""  # skip kalau tidak ada angle konkret


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


def _readable_price_summary(price: PriceMovementSummary) -> str:
    """Format price summary jadi teks yang mudah dibaca AI (bukan raw JSON)."""
    lines = []
    if price.lowest_price is not None and price.highest_price is not None:
        if price.lowest_price == price.highest_price:
            lines.append(f"- Harga: {_format_money(price.lowest_price, price.currency)}")
        else:
            lines.append(
                f"- Kisaran: {_format_money(price.lowest_price, price.currency)} – "
                f"{_format_money(price.highest_price, price.currency)}"
            )
    if price.average_price is not None:
        lines.append(f"- Rata-rata: {_format_money(price.average_price, price.currency)}")
    if price.latest_observed_at:
        lines.append(f"- Terakhir dicek: {_format_datetime(price.latest_observed_at)}")
    for ref in price.source_references[:2]:
        label = ref.reference_label or ref.source_name
        lines.append(f"- Sumber: {label}")
    lines.append(f"- Total snapshot: {price.snapshot_count}")
    return "\n".join(lines)


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


def _is_too_verbose(answer: str) -> bool:
    lines = [line for line in answer.splitlines() if line.strip()]
    return len(answer) > 1800 or len(lines) > 14
