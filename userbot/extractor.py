"""Преобразование Telethon-сообщения в словарь полей для БД."""
from __future__ import annotations

from typing import Any


def _full_name(entity: Any) -> str | None:
    """Имя автора: для пользователя — имя+фамилия, для канала — title."""
    if entity is None:
        return None
    first = getattr(entity, "first_name", None)
    last = getattr(entity, "last_name", None)
    if first or last:
        return " ".join(part for part in (first, last) if part)
    return getattr(entity, "title", None)


def _chat_title(chat: Any) -> str | None:
    """Заголовок чата (для групп/каналов) или имя собеседника (для лички)."""
    if chat is None:
        return None
    title = getattr(chat, "title", None)
    if title:
        return title
    return _full_name(chat)


async def extract(message: Any) -> dict:
    """Достаёт поля из Telethon-сообщения (аналог _extract в message_service).

    get_sender()/get_chat() могут сходить в сеть, но Telethon кэширует
    сущности, поэтому в большинстве случаев это дёшево.
    """
    try:
        sender = await message.get_sender()
    except Exception:
        sender = None
    try:
        chat = await message.get_chat()
    except Exception:
        chat = None

    return {
        # chat_id у Telethon уже в «маркированном» виде (-100… для каналов),
        # что совпадает с форматом Bot API — таблица общая.
        "chat_id": message.chat_id,
        "message_id": message.id,
        "user_id": getattr(sender, "id", 0) or 0,
        "username": getattr(sender, "username", None),
        "full_name": _full_name(sender),
        "chat_title": _chat_title(chat),
        # message.message — это «сырой» текст; для медиа без подписи он пуст.
        "text": message.message or None,
        "date": message.date,
    }
