"""Бизнес-логика: преобразование aiogram-сообщений в записи БД."""
from __future__ import annotations

import logging

from aiogram.types import Message as TgMessage

from database import async_session_factory, crud

logger = logging.getLogger(__name__)


def _extract(message: TgMessage) -> dict:
    """Достаёт из объекта aiogram поля, которые мы сохраняем."""
    user = message.from_user
    return {
        "chat_id": message.chat.id,
        "message_id": message.message_id,
        # У постов в каналах from_user может отсутствовать.
        "user_id": user.id if user else 0,
        "username": user.username if user else None,
        "full_name": user.full_name if user else None,
        "chat_title": message.chat.title or message.chat.full_name,
        # Текст обычного сообщения или подпись к медиа.
        "text": message.text or message.caption,
        "date": message.date,
    }


async def store_message(message: TgMessage) -> None:
    """Сохраняет входящее сообщение (идемпотентно по chat_id+message_id)."""
    data = _extract(message)
    async with async_session_factory() as session:
        async with session.begin():
            existing = await crud.get_message(
                session, data["chat_id"], data["message_id"]
            )
            if existing is not None:
                return  # дубликат — например повторный апдейт
            await crud.add_message(session, data)
    logger.debug(
        "Сохранено сообщение chat=%s msg=%s user=%s",
        data["chat_id"], data["message_id"], data["user_id"],
    )


async def store_edit(message: TgMessage) -> None:
    """Фиксирует правку сообщения и историю изменений текста."""
    data = _extract(message)
    async with async_session_factory() as session:
        async with session.begin():
            await crud.add_edit(session, data)
    logger.debug(
        "Зафиксирована правка chat=%s msg=%s",
        data["chat_id"], data["message_id"],
    )


async def mark_message_deleted(chat_id: int, message_id: int) -> bool:
    """Помечает сообщение удалённым. Возвращает True, если запись найдена."""
    async with async_session_factory() as session:
        async with session.begin():
            message = await crud.mark_deleted(session, chat_id, message_id)
            return message is not None
