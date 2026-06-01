"""Бизнес-логика: преобразование aiogram-сообщений в записи БД."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram.types import Message as TgMessage

from database import async_session_factory, crud
from models import Message

logger = logging.getLogger(__name__)


@dataclass
class EditResult:
    """Результат обработки правки — для мгновенного уведомления админов."""

    message: Message
    old_text: str | None
    new_text: str | None
    changed: bool


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


async def store_message_data(data: dict) -> None:
    """Сохраняет сообщение по готовому словарю (идемпотентно).

    Универсальная точка входа: подходит и для aiogram, и для Telethon-userbot.
    """
    async with async_session_factory() as session:
        async with session.begin():
            existing = await crud.get_message(
                session, data["chat_id"], data["message_id"]
            )
            if existing is not None:
                return  # дубликат — например повторный апдейт или второй источник
            await crud.add_message(session, data)
    logger.debug(
        "Сохранено сообщение chat=%s msg=%s user=%s",
        data["chat_id"], data["message_id"], data["user_id"],
    )


async def store_edit_data(data: dict) -> EditResult:
    """Фиксирует правку по готовому словарю и возвращает EditResult."""
    async with async_session_factory() as session:
        async with session.begin():
            saved, old_text, changed = await crud.add_edit(session, data)
    logger.debug(
        "Зафиксирована правка chat=%s msg=%s changed=%s",
        data["chat_id"], data["message_id"], changed,
    )
    # expire_on_commit=False -> атрибуты saved доступны после закрытия сессии.
    return EditResult(message=saved, old_text=old_text, new_text=data.get("text"), changed=changed)


async def store_message(message: TgMessage) -> None:
    """Сохраняет входящее aiogram-сообщение."""
    await store_message_data(_extract(message))


async def store_edit(message: TgMessage) -> EditResult:
    """Фиксирует правку aiogram-сообщения и возвращает EditResult."""
    return await store_edit_data(_extract(message))


async def mark_message_deleted(chat_id: int, message_id: int) -> Message | None:
    """Помечает сообщение удалённым. Возвращает запись (или None, если не найдена)."""
    async with async_session_factory() as session:
        async with session.begin():
            message = await crud.mark_deleted(session, chat_id, message_id)
        return message
