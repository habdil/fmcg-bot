from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from telegram.error import TelegramError
from telegram.ext import Application

from crawling_bot.database import session_scope
from database_migration.models.chat_memory import UserMemory

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Asia/Jakarta"
REMINDER_MEMORY_TYPE = "reminder"
PENDING = "pending"
SENT = "sent"
FAILED = "failed"

TRIGGER_RE = re.compile(
    r"\b(?:tolong\s+)?(?:ingatkan|ingetin|remind)\s+(?:aku|saya|gue|gw)?\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"\b(?:jam|pukul)\s*(\d{1,2})(?:[.:](\d{2}))?\b", re.IGNORECASE)
BARE_TIME_RE = re.compile(r"\b(\d{1,2})[.:](\d{2})\b")
DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
TEMPORAL_WORD_RE = re.compile(
    r"\b(?:hari ini|besok|lusa|nanti|pagi|siang|sore|malam|"
    r"senin|selasa|rabu|kamis|jumat|jum'at|sabtu|minggu|ahad)\b",
    re.IGNORECASE,
)
WEEKDAYS = {
    "senin": 0,
    "selasa": 1,
    "rabu": 2,
    "kamis": 3,
    "jumat": 4,
    "jum'at": 4,
    "sabtu": 5,
    "minggu": 6,
    "ahad": 6,
}


@dataclass(frozen=True)
class ReminderRequest:
    reminder_text: str
    scheduled_at: datetime
    timezone_name: str = DEFAULT_TIMEZONE


@dataclass(frozen=True)
class DueReminder:
    memory_id: object
    chat_id: int
    reminder_text: str
    scheduled_at: datetime
    username: str | None = None


def parse_reminder_request(
    message: str,
    *,
    now: datetime | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> ReminderRequest | None:
    normalized = " ".join((message or "").strip().split())
    if not normalized:
        return None

    trigger = TRIGGER_RE.search(normalized)
    if trigger is None:
        return None

    tz = _local_timezone(timezone_name)
    current = _as_local(now or datetime.now(tz), tz)
    remainder = normalized[trigger.end() :].strip(" ,.-")
    if not remainder:
        return None

    scheduled_at = _parse_schedule(remainder, current)
    reminder_text = _extract_reminder_text(remainder)
    return ReminderRequest(
        reminder_text=reminder_text or "hal yang kamu minta",
        scheduled_at=scheduled_at,
        timezone_name=timezone_name,
    )


def save_reminder(chat_id: int | str, username: str | None, request: ReminderRequest) -> str:
    memory_key = f"reminder:{uuid.uuid4()}"
    try:
        with session_scope() as session:
            session.add(
                UserMemory(
                    channel="telegram",
                    channel_user_id=str(chat_id),
                    username=username,
                    memory_type=REMINDER_MEMORY_TYPE,
                    memory_key=memory_key,
                    memory_text=request.reminder_text,
                    memory_json={
                        "scheduled_at": request.scheduled_at.isoformat(),
                        "timezone": request.timezone_name,
                        "status": PENDING,
                    },
                    source="explicit_user_instruction",
                )
            )
        return format_reminder_ack(request)
    except SQLAlchemyError as exc:
        raise RuntimeError("Reminder belum aktif. Jalankan migrasi database dulu.") from exc


def due_reminders(*, now: datetime | None = None, timezone_name: str = DEFAULT_TIMEZONE) -> list[DueReminder]:
    tz = _local_timezone(timezone_name)
    current = _as_local(now or datetime.now(tz), tz)
    reminders: list[DueReminder] = []
    with session_scope() as session:
        memories = session.scalars(
            select(UserMemory).where(
                UserMemory.channel == "telegram",
                UserMemory.memory_type == REMINDER_MEMORY_TYPE,
            )
        ).all()
        for memory in memories:
            data = memory.memory_json if isinstance(memory.memory_json, dict) else {}
            if data.get("status", PENDING) != PENDING:
                continue
            scheduled_at = _parse_iso_datetime(data.get("scheduled_at"), tz)
            if scheduled_at is None or scheduled_at > current:
                continue
            try:
                chat_id = int(memory.channel_user_id)
            except (TypeError, ValueError):
                continue
            reminders.append(
                DueReminder(
                    memory_id=memory.id,
                    chat_id=chat_id,
                    reminder_text=memory.memory_text or "hal yang kamu minta",
                    scheduled_at=scheduled_at,
                    username=memory.username,
                )
            )
    return reminders


def mark_reminder_sent(memory_id: object, *, sent_at: datetime | None = None) -> None:
    _update_reminder_status(memory_id, SENT, sent_at=sent_at)


def mark_reminder_failed(memory_id: object, error_message: str) -> None:
    _update_reminder_status(memory_id, FAILED, error_message=error_message)


async def reminder_loop(application: Application, *, interval_seconds: int = 60) -> None:
    while True:
        try:
            reminders = await asyncio.to_thread(due_reminders)
            for reminder in reminders:
                try:
                    await application.bot.send_message(
                        chat_id=reminder.chat_id,
                        text=f"Pengingat: {reminder.reminder_text}",
                    )
                    await asyncio.to_thread(mark_reminder_sent, reminder.memory_id)
                except TelegramError as exc:
                    logger.warning("Failed sending reminder to chat %s: %s", reminder.chat_id, exc)
                    await asyncio.to_thread(mark_reminder_failed, reminder.memory_id, str(exc))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Reminder loop skipped one cycle: %s", exc)
        await asyncio.sleep(interval_seconds)


def format_reminder_ack(request: ReminderRequest) -> str:
    return (
        "Siap, aku ingatkan "
        f"{_format_local_datetime(request.scheduled_at)}: {request.reminder_text}"
    )


def _parse_schedule(text: str, now: datetime) -> datetime:
    day_offset = _day_offset(text, now)
    date_value = _date_from_text(text, now)
    hour, minute = _time_from_text(text)

    if hour is None:
        hour, minute = _default_time(text)

    if date_value is not None:
        target = date_value.replace(hour=hour, minute=minute, second=0, microsecond=0)
    else:
        target = (now + timedelta(days=day_offset)).replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

    if target <= now:
        target += timedelta(days=1)
    return target


def _day_offset(text: str, now: datetime) -> int:
    lowered = text.lower()
    if "lusa" in lowered:
        return 2
    if "besok" in lowered:
        return 1
    weekday = _weekday_from_text(lowered, now=now)
    if weekday is not None:
        return weekday
    return 0


def _weekday_from_text(lowered: str, *, now: datetime | None = None) -> int | None:
    current = now or datetime.now(_local_timezone(DEFAULT_TIMEZONE))
    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            delta = (weekday - current.weekday()) % 7
            return delta or 7
    return None


def _date_from_text(text: str, now: datetime) -> datetime | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year_text = match.group(3)
    year = int(year_text) if year_text else now.year
    if year < 100:
        year += 2000
    try:
        return now.replace(year=year, month=month, day=day)
    except ValueError:
        return None


def _time_from_text(text: str) -> tuple[int | None, int]:
    lowered = text.lower()
    match = TIME_RE.search(text) or BARE_TIME_RE.search(text)
    if not match:
        return None, 0
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if minute > 59:
        minute = 0
    if hour > 23:
        hour = 9
    if any(word in lowered for word in ["sore", "malam"]) and 1 <= hour <= 11:
        hour += 12
    if "siang" in lowered and 1 <= hour <= 10:
        hour += 12
    return hour, minute


def _default_time(text: str) -> tuple[int, int]:
    lowered = text.lower()
    if "pagi" in lowered:
        return 9, 0
    if "siang" in lowered:
        return 12, 0
    if "sore" in lowered:
        return 16, 0
    if "malam" in lowered:
        return 19, 0
    return 9, 0


def _extract_reminder_text(text: str) -> str:
    cleaned = TIME_RE.sub(" ", text)
    cleaned = BARE_TIME_RE.sub(" ", cleaned)
    cleaned = DATE_RE.sub(" ", cleaned)
    cleaned = TEMPORAL_WORD_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\b(?:untuk|buat|agar|supaya|ya|dong|nanti)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.strip(" ,.-").split())
    return cleaned[:500]


def _update_reminder_status(
    memory_id: object,
    status: str,
    *,
    sent_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    with session_scope() as session:
        memory = session.get(UserMemory, memory_id)
        if memory is None:
            return
        data = dict(memory.memory_json or {})
        data["status"] = status
        if sent_at is not None or status == SENT:
            data["sent_at"] = (sent_at or datetime.now(timezone.utc)).isoformat()
        if error_message:
            data["error_message"] = error_message[:500]
        memory.memory_json = data


def _parse_iso_datetime(value: object, tz: tzinfo) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _as_local(parsed, tz)


def _as_local(value: datetime, tz: tzinfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _local_timezone(timezone_name: str) -> tzinfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=7), name=timezone_name)


def _format_local_datetime(value: datetime) -> str:
    local = _as_local(value, _local_timezone(DEFAULT_TIMEZONE))
    return local.strftime("%d/%m/%Y %H:%M WIB")
