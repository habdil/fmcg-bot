from crawling_bot.processors.entity_extractor import extract_entities
from crawling_bot.processors.signal_extractor import extract_signals, infer_category


def test_signal_extractor_detects_price_and_shortage_signals() -> None:
    title = "Harga minyak goreng naik karena pasokan terbatas"
    content = (
        "Harga minyak goreng naik di Jawa Tengah karena pasokan terbatas. "
        "Beberapa distributor menyebut stok kosong di gudang ritel."
    )
    entities = extract_entities(title, content)
    signals = extract_signals(title, content, entities)
    signal_types = {signal.signal_type for signal in signals}

    assert "price_increase" in signal_types
    assert "shortage" in signal_types
    assert all(signal.evidence_text for signal in signals)
    assert infer_category(signals) in {"price", "supply"}
