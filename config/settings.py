"""Загрузка конфигурации из переменных окружения / .env."""
from __future__ import annotations

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки приложения.

    Значения читаются из переменных окружения (или файла .env).
    Имена полей в нижнем регистре автоматически сопоставляются с
    UPPER_CASE-переменными окружения (BOT_TOKEN -> bot_token и т.д.).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Токен бота от @BotFather (обязателен).
    bot_token: str

    # Список Telegram user_id администраторов, которым разрешены команды.
    # NoDecode отключает попытку pydantic распарсить значение как JSON —
    # значение разбирает наш валидатор ниже (строка "111,222,333").
    admin_ids: Annotated[list[int], NoDecode] = []

    # DSN для async SQLAlchemy. По умолчанию — локальный SQLite-файл.
    database_url: str = "sqlite+aiosqlite:///data/messages.db"

    # Уровень логирования (DEBUG / INFO / WARNING / ERROR).
    log_level: str = "INFO"

    # Сколько записей по умолчанию показывать в /history, /deleted, поиске.
    page_size: int = 20

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        """Позволяет задавать ADMIN_IDS как строку "111,222,333" в .env."""
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        return value
