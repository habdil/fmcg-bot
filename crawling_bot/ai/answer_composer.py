from __future__ import annotations

from collections import Counter
import json
import logging
from typing import Any

from crawling_bot.config import settings
from crawling_bot.schemas.analyst_schema import (
    AnalystQuery,
    GroundedAnalystReport,
    format_grounded_report,
)

logger = logging.getLogger(__name__)


class GroundedAnswerComposer:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model

    def compose(self, query: AnalystQuery, evidence_rows: list[dict[str, Any]]) -> str:
        fallback = format_grounded_report(self._fallback_report(query, evidence_rows))
        if not self.api_key or not evidence_rows:
            return fallback

        try:
            from google import genai
            from google.genai import types

            payload = {
                "question": query.model_dump(),
                "evidence": [_compact_evidence(row) for row in evidence_rows[:20]],
                "rules": [
                    "Use only the supplied evidence.",
                    "Do not invent prices, pack size availability, causes, or market forecasts.",
                    "If evidence does not mention the requested pack size, say so explicitly.",
                    "Always include source names and URLs in source_notes.",
                    "Write in Indonesian, concise, and useful for FMCG sub-distributors.",
                ],
            }
            prompt = (
                "Create a source-grounded FMCG business intelligence answer. "
                "The user wants a dynamic analyst-style answer, but every factual claim "
                "must be supported by the evidence payload.\n\n"
                f"{json.dumps(payload, ensure_ascii=False)}"
            )
            with genai.Client(api_key=self.api_key) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GroundedAnalystReport,
                    ),
                )
            parsed = response.parsed if getattr(response, "parsed", None) else json.loads(response.text)
            return format_grounded_report(GroundedAnalystReport.model_validate(parsed))
        except Exception as exc:  # pragma: no cover - API fallback path
            logger.warning("Gemini answer composition failed, using fallback report: %s", exc)
            return fallback

    def _fallback_report(self, query: AnalystQuery, evidence_rows: list[dict[str, Any]]) -> GroundedAnalystReport:
        if not evidence_rows:
            return GroundedAnalystReport(
                title=f"FMCG Intelligence Report: {query.normalized_keyword}",
                executive_summary=(
                    "Belum ada evidence yang cukup di database setelah proses crawling terbatas. "
                    "Sistem tidak menyimpulkan trend, harga, atau forecast tanpa sumber."
                ),
                trend_analysis="Belum ada arah trend yang bisa dipertanggungjawabkan.",
                price_signal="Belum ada signal harga yang relevan.",
                supply_signal="Belum ada signal supply atau distribusi yang relevan.",
                demand_signal="Belum ada signal demand yang relevan.",
                sentiment_signal="Belum ada signal sentiment yang relevan.",
                business_impact="Belum ada dasar source-grounded untuk tindakan bisnis.",
                recommended_actions=[
                    "Jalankan crawling lagi dengan batas source/artikel lebih besar.",
                    "Tambahkan source harga retail atau marketplace jika butuh harga SKU spesifik.",
                ],
                confidence_level="low",
                limitations=["Tidak ada source relevan yang tersimpan untuk pertanyaan ini."],
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
            "Analisis hanya memakai artikel publik yang sudah dicrawl dan tersimpan di database.",
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
                f"Signal: {row.get('signal_type')} | URL: {row.get('article_url')}"
            )

        confidence = "high" if len(evidence_rows) >= 8 and high_count >= 2 else "medium" if len(evidence_rows) >= 3 else "low"
        return GroundedAnalystReport(
            title=f"FMCG Intelligence Report: {query.normalized_keyword}",
            executive_summary=(
                f"Ditemukan {len(evidence_rows)} signal relevan untuk topik ini. "
                f"Arah harga {price}, supply/distribusi memiliki {supply_risk} signal risiko, "
                f"dan demand {demand}."
            ),
            trend_analysis=(
                "Signal terbanyak: "
                + ", ".join(f"{name} ({count})" for name, count in counts.most_common(5))
            ),
            price_signal=f"Harga {price} berdasarkan perbandingan signal price_increase dan price_decrease.",
            supply_signal=f"Ada {supply_risk} signal shortage/distribution_disruption yang perlu dipantau.",
            demand_signal=f"Demand {demand} berdasarkan signal demand yang tersimpan.",
            sentiment_signal=f"Sentiment {sentiment} berdasarkan signal sentiment yang tersimpan.",
            business_impact=(
                "Untuk sub-distributor, signal ini berguna sebagai early warning untuk pricing, "
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
