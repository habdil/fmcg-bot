from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url_direct: str = ""
    database_url_pooler: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_allowed_chat_ids: str = ""

    crawler_user_agent: str = "FMCGIntelligenceBot/1.0"
    crawler_timeout: int = Field(default=20, ge=1, le=120)
    max_articles_per_source: int = Field(default=50, ge=1, le=500)

    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_chat_ids(self) -> List[str]:
        if not self.telegram_allowed_chat_ids.strip():
            return []
        return [
            chat_id.strip()
            for chat_id in self.telegram_allowed_chat_ids.split(",")
            if chat_id.strip()
        ]

    def require_runtime_database_url(self) -> str:
        if not self.database_url_pooler:
            raise RuntimeError("DATABASE_URL_POOLER is required for runtime services.")
        return self.database_url_pooler

    def require_migration_database_url(self) -> str:
        if not self.database_url_direct:
            raise RuntimeError("DATABASE_URL_DIRECT is required for Alembic migrations.")
        return self.database_url_direct


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
