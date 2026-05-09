from __future__ import annotations

from collections import Counter
import json
import logging
from typing import Any

from chat_engine.ai.base import AIProvider, NoopAIProvider
from chat_engine.ai.router import AIRouter
from crawling_bot.schemas.analyst_schema import (
    AnalystQuery,
    GroundedAnalystReport,
    format_grounded_report,
)

logger = logging.getLogger(__name__)


class GroundedAnswerComposer:
    """Source-grounded answer composer for Sorota business analysis."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        provider: AIProvider | None = None,
    ) -> None:
        # Passing api_key="" is used by tests to force the rule-based fallback.
        self.provider = provider or (NoopAIProvider() if api_key == "" else AIRouter().composer_provider())

    def compose(self, query: AnalystQuery, evidence_rows: list[dict[str, Any]]) -> str:
        fallback = format_grounded_report(self._fallback_report(query, evidence_rows))
        if not evidence_rows:
            return fallback

        payload = {
            "question": query.model_dump(),
            "evidence": [_compact_evidence(row) for row in evidence_rows[:20]],
            "rules": [
                "Use only the supplied evidence.",
                "Do not invent prices, pack size availability, causes, or market forecasts.",
                "If evidence does not mention the requested pack size, say so explicitly.",
                "Always include source names and URLs in source_notes.",
                "Write in Indonesian, concise, and useful for Indonesian UMKM owners.",
            ],
        }
        prompt = (
            "Create a source-backed Sorota business decision answer for an Indonesian UMKM owner. "
            "The user wants a dynamic analyst-style answer, but every factual claim "
            "must be supported by the evidence payload.\n\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        if self.provider.is_configured:
            try:
                return format_grounded_report(self.provider.generate_json(prompt, GroundedAnalystReport))
            except Exception as exc:
                logger.warning("AI answer composition failed, using fallback report: %s", exc)

        return fallback

    def _fallback_report(self, query: AnalystQuery, evidence_rows: list[dict[str, Any]]) -> GroundedAnalystReport:
        if not evidence_rows:
            return GroundedAnalystReport(
                title=f"Sorota Business Insight: {query.normalized_keyword}",
                executive_summary=(
                    "Aku belum punya data pembanding yang cukup untuk topik ini. "
                    "Jadi aku belum bisa menyimpulkan tren, harga, atau outlook tanpa sumber yang jelas."
                ),
                trend_analysis="Belum ada arah trend yang bisa dipertanggungjawabkan.",
                price_signal="Belum ada indikasi harga yang relevan.",
                supply_signal="Belum ada indikasi pasokan atau distribusi yang relevan.",
                demand_signal="Belum ada indikasi permintaan yang relevan.",
                sentiment_signal="Belum ada indikasi sentimen yang relevan.",
                business_impact="Belum ada dasar sumber yang cukup untuk menyarankan tindakan bisnis.",
                recommended_actions=[
                    "Tambahkan sumber pasar atau berita yang lebih relevan.",
                    "Tambahkan data harga supplier, retail, atau marketplace jika butuh harga produk spesifik.",
                ],
                confidence_level="low",
                limitations=["Belum ada sumber relevan untuk pertanyaan ini."],
                source_notes=["Tidak ada sumber relevan."],
            )

        counts = Counter(str(row.get("signal_type") or "unknown") for row in evidence_rows)
        high_count = sum(1 for row in evidence_rows if row.get("urgency") == "high")
        pack_size_present = _pack_size_present(query, evidence_rows)

        price = _direction(counts["price_increase"], counts["price_decrease"], "belum jelas")
        demand = _direction(counts["demand_increase"], counts["demand_decrease"], "belum jelas")
        sentiment = _direction(counts["positive_sentiment"], counts["negative_sentiment"], "netral/belum kuat")
        supply_risk = counts["shortage"] + counts["distribution_disruption"]

        limitations = [
            "Analisis hanya memakai artikel publik yang sudah tersedia di sistem.",
        ]
        if query.pack_size and not pack_size_present:
            limitations.append(
                f"Evidence yang ditemukan belum menyebut kemasan {query.pack_size} secara spesifik."
            )

        actions = ["Pantau update supplier dan validasi stok internal sebelum keputusan pembelian."]
        if counts["price_increase"] > counts["price_decrease"]:
            actions.append("Siapkan skenario adjustment margin dan komunikasi perubahan harga.")
        if supply_risk:
            actions.append("Cek alternatif supply dan buffer stock untuk SKU fast-moving.")
        if counts["demand_increase"] > counts["demand_decrease"]:
            actions.append("Prioritaskan alokasi stok ke channel atau area dengan demand kuat.")

        source_notes = []
        for index, row in enumerate(evidence_rows[:8], start=1):
            source_notes.append(
                f"{index}. {row.get('source_name')} - {row.get('title')} | "
                f"Indikasi: {row.get('signal_type')} | URL: {row.get('article_url')}"
            )

        confidence = "high" if len(evidence_rows) >= 8 and high_count >= 2 else "medium" if len(evidence_rows) >= 3 else "low"
        return GroundedAnalystReport(
            title=f"Sorota Business Insight: {query.normalized_keyword}",
            executive_summary=(
                f"Ada {len(evidence_rows)} temuan relevan untuk topik ini. "
                f"Arah harga {price}, pasokan/distribusi punya {supply_risk} indikasi risiko, "
                f"dan permintaan {demand}."
            ),
            trend_analysis=(
                "Indikasi terbanyak: "
                + ", ".join(f"{name} ({count})" for name, count in counts.most_common(5))
            ),
            price_signal=f"Harga {price} berdasarkan indikasi kenaikan dan penurunan harga yang tersedia.",
            supply_signal=f"Ada {supply_risk} indikasi risiko pasokan/distribusi yang perlu dipantau.",
            demand_signal=f"Permintaan {demand} berdasarkan indikasi yang tersedia.",
            sentiment_signal=f"Sentimen {sentiment} berdasarkan indikasi yang tersedia.",
            business_impact=(
                "Untuk UMKM, temuan ini berguna sebagai early warning untuk pricing, "
                "buffer stock, dan prioritas alokasi barang. Keputusan final tetap perlu validasi "
                "dengan data stok, PO, dan harga supplier internal."
            ),
            recommended_actions=actions,
            confidence_level=confidence,  # type: ignore[arg-type]
            limitations=limitations,
            source_notes=source_notes,
        )


def _compact_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "signal_type": row.get("signal_type"),
        "product": row.get("product"),
        "company": row.get("company"),
        "location": row.get("location"),
        "urgency": row.get("urgency"),
        "impact_score": row.get("impact_score"),
        "confidence_score": row.get("confidence_score"),
        "reason": row.get("reason"),
        "evidence_text": row.get("evidence_text"),
        "explanation": row.get("explanation"),
        "title": row.get("title"),
        "source_name": row.get("source_name"),
        "article_url": row.get("article_url"),
        "published_at": str(row.get("published_at") or ""),
    }


def _direction(up_count: int, down_count: int, neutral: str) -> str:
    if up_count > down_count:
        return "cenderung naik"
    if down_count > up_count:
        return "cenderung turun"
    if up_count or down_count:
        return "campuran"
    return neutral


def _pack_size_present(query: AnalystQuery, rows: list[dict[str, Any]]) -> bool:
    if not query.pack_size:
        return True
    needle = query.pack_size.lower().replace(" ", "")
    for row in rows:
        haystack = " ".join(
            str(row.get(key) or "")
            for key in ["title", "reason", "evidence_text", "ai_polished_summary"]
        ).lower().replace(" ", "")
        if needle in haystack:
            return True
    return False
