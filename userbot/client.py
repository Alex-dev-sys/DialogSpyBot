"""Создание Telethon-клиента из конфигурации."""
from __future__ import annotations

from telethon import TelegramClient

from config import settings


def build_client() -> TelegramClient:
    """Собирает TelegramClient. api_id/api_hash берутся из .env.

    Имя сессии (settings.userbot_session) указывает на файл .session,
    который Telethon создаёт при первом интерактивном входе.
    """
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError(
            "Не заданы API_ID / API_HASH. Получите их на https://my.telegram.org "
            "и пропишите в .env."
        )
    return TelegramClient(settings.userbot_session, settings.api_id, settings.api_hash)
