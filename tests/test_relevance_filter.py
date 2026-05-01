from crawling_bot.processors.relevance_filter import is_relevant, score_relevance


def test_relevance_filter_detects_fmcg_price_topic() -> None:
    result = score_relevance(
        "Harga minyak goreng naik di retail modern",
        "Distributor melaporkan pasokan minyak goreng terbatas dan stok menipis.",
    )

    assert result.is_relevant is True
    assert result.score > 0.3
    assert "minyak goreng" in result.keyword_hits


def test_relevance_filter_rejects_unrelated_topic() -> None:
    assert is_relevant("Klub sepak bola menang besar", "Pertandingan berlangsung sengit.") is False
