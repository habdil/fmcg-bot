from __future__ import annotations

from sqlalchemy import select

from crawling_bot.database import session_scope
from database_migration.models.user_subscription import UserSubscription


def subscribe_chat(chat_id: int | str, username: str | None = None) -> None:
    with session_scope() as session:
        subscription = session.scalar(
            select(UserSubscription).where(UserSubscription.telegram_chat_id == str(chat_id))
        )
        if subscription is None:
            subscription = UserSubscription(
                channel="telegram",
                channel_chat_id=str(chat_id),
                telegram_chat_id=str(chat_id),
            )
            session.add(subscription)
        subscription.channel = "telegram"
        subscription.channel_chat_id = str(chat_id)
        subscription.username = username
        subscription.is_active = True


def unsubscribe_chat(chat_id: int | str) -> None:
    with session_scope() as session:
        subscription = session.scalar(
            select(UserSubscription).where(UserSubscription.telegram_chat_id == str(chat_id))
        )
        if subscription is not None:
            subscription.is_active = False
