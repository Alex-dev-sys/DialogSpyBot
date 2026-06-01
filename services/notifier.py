"""Мгновенная рассылка уведомлений администраторам.

Сами отправки делает Telegram-бот (объект Bot), а не оператор: при правке
или удалении сообщения админы из ADMIN_IDS моментально получают алерт.
"""
from __future__ import annotations

import logging

from aiogram import Bot

from config import settings
from models import Message
from services import formatter

logger = logging.getLogger(__name__)


async def _broadcast(bot: Bot, text: str) -> None:
    """Шлёт текст всем администраторам, не падая из-за одного недоступного."""
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, disable_web_page_preview=True)
        except Exception as exc:  # заблокировал бота, неверный id и т.п.
            logger.warning("Не доставлено админу %s: %s", admin_id, exc)


async def notify_edit(
    bot: Bot, message: Message, old_text: str | None, new_text: str | None
) -> None:
    """Мгновенно уведомляет о правке (было → стало)."""
    await _broadcast(bot, formatter.format_edit_alert(message, old_text, new_text))


async def notify_deleted(bot: Bot, message: Message) -> None:
    """Мгновенно уведомляет об удалении (с исходным текстом)."""
    await _broadcast(bot, formatter.format_deleted_alert(message))
