"""Перехват всех входящих сообщений и их правок.

Этот роутер подключается ПОСЛЕ роутера команд, поэтому команды
администраторов обрабатываются там, а сюда попадает весь остальной
поток сообщений, который мы складываем в БД.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from services import message_service

logger = logging.getLogger(__name__)

router = Router(name="messages")


@router.edited_message()
async def on_edited_message(message: Message) -> None:
    """Telegram прислал событие редактирования — сохраняем старую/новую версию."""
    await message_service.store_edit(message)


@router.message()
async def on_message(message: Message) -> None:
    """Любое новое сообщение — сохраняем в БД."""
    await message_service.store_message(message)
