"""Перехват всех входящих сообщений и их правок.

Этот роутер подключается ПОСЛЕ роутера команд, поэтому команды
администраторов обрабатываются там, а сюда попадает весь остальной
поток сообщений, который мы складываем в БД.
"""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import Message

from services import message_service, notifier

logger = logging.getLogger(__name__)

router = Router(name="messages")


@router.edited_message()
async def on_edited_message(message: Message, bot: Bot) -> None:
    """Telegram прислал событие редактирования — сохраняем версии и мгновенно
    уведомляем администраторов (было → стало)."""
    result = await message_service.store_edit(message)
    if result.changed:
        await notifier.notify_edit(bot, result.message, result.old_text, result.new_text)


@router.message()
async def on_message(message: Message) -> None:
    """Любое новое сообщение — сохраняем в БД."""
    await message_service.store_message(message)
