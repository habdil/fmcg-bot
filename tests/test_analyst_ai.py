from crawling_bot.ai.answer_composer import GroundedAnswerComposer
from crawling_bot.ai.query_parser import AnalystQueryParser


def test_query_parser_fallback_normalizes_minyak_pack_size() -> None:
    query = AnalystQueryParser(api_key="").parse("Tolong analisis produk minyak kita 2 liter")

    assert query.normalized_keyword == "minyak goreng"
    assert query.product == "minyak goreng"
    assert query.pack_size == "2 liter"
    assert "minyak goreng" in query.search_terms
    assert "2 liter" in query.search_terms


def test_answer_composer_fallback_mentions_pack_size_limitation() -> None:
    query = AnalystQueryParser(api_key="").parse("Analisis minyak 2 liter")
    rows = [
        {
            "signal_type": "price_increase",
            "urgency": "high",
            "impact_score": 0.81,
            "confidence_score": 0.72,
            "reason": "Harga naik karena pasokan terbatas.",
            "evidence_text": "Harga minyak goreng naik akibat pasokan terbatas.",
            "title": "Harga minyak goreng naik",
            "source_name": "Test Source",
            "article_url": "https://example.com/minyak",
        }
    ]

    answer = GroundedAnswerComposer(api_key="").compose(query, rows)

    assert "Sorota Business Insight" in answer
    assert "2 liter" in answer
    assert "Test Source" in answer
