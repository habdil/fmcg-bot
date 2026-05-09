from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from telegram_bot.services.memory_service import ChatMemoryPreferences, extract_business_facts
from telegram_bot.services.personal_brief_service import compose_personalized_brief
from telegram_bot.services.reminder_service import parse_reminder_request


JAKARTA_TZ = timezone(timedelta(hours=7), name="Asia/Jakarta")


def test_extract_business_facts_from_natural_profile_message() -> None:
    facts = extract_business_facts(
        "Aku jual ayam geprek dan es teh di Bandung, target margin 30%, supplier saya Pasar Ciroyom."
    )

    assert facts["business_type"] == "kuliner"
    assert facts["location"] == "Bandung"
    assert facts["target_margin_percent"] == "30"
    assert facts["known_supplier"] == "Pasar Ciroyom"
    assert facts["main_products"] == ["ayam geprek", "es teh"]


def test_parse_reminder_request_for_tomorrow_with_time() -> None:
    now = datetime(2026, 5, 10, 8, 30, tzinfo=JAKARTA_TZ)

    reminder = parse_reminder_request(
        "ingatkan saya besok jam 9 bayar supplier ayam",
        now=now,
    )

    assert reminder is not None
    assert reminder.reminder_text == "bayar supplier ayam"
    assert reminder.scheduled_at == datetime(2026, 5, 11, 9, 0, tzinfo=JAKARTA_TZ)


def test_parse_reminder_request_uses_period_default_time() -> None:
    now = datetime(2026, 5, 10, 8, 30, tzinfo=JAKARTA_TZ)

    reminder = parse_reminder_request("ingatkan aku nanti malam cek stok telur", now=now)

    assert reminder is not None
    assert reminder.reminder_text == "cek stok telur"
    assert reminder.scheduled_at == datetime(2026, 5, 10, 19, 0, tzinfo=JAKARTA_TZ)


def test_compose_personalized_brief_uses_memory_profile() -> None:
    memory = ChatMemoryPreferences(
        business_type="kuliner",
        location="Bandung",
        product_focus=["ayam geprek", "es teh"],
        target_margin_percent=Decimal("30"),
        known_supplier="Pasar Ciroyom",
    )

    brief = compose_personalized_brief(
        memory,
        now=datetime(2026, 5, 10, 8, 30, tzinfo=JAKARTA_TZ),
    )

    assert "Brief singkat untuk bisnis kuliner di Bandung" in brief
    assert "Cek HPP ayam geprek, es teh" in brief
    assert "patokanmu minimal 30%" in brief
    assert "Follow up Pasar Ciroyom" in brief
