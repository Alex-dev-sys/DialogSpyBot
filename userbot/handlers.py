"""Регистрация Telethon-обработчиков: новые сообщения, правки, удаления."""
from __future__ import annotations

import logging

from aiogram import Bot
from telethon import TelegramClient, events

from database import async_session_factory, crud
from services import message_service, notifier
from userbot.extractor import extract

logger = logging.getLogger(__name__)


def register(client: TelegramClient, bot: Bot) -> None:
    """Навешивает обработчики на Telethon-клиент.

    `bot` — aiogram Bot: через него (то есть «от лица бота») рассылаем
    мгновенные уведомления администраторам.
    """

    @client.on(events.NewMessage())
    async def on_new_message(event: events.NewMessage.Event) -> None:
        # Сохраняем всё, что видит аккаунт, — в т.ч. личные чаты,
        # куда бота добавить нельзя. Это же позволяет потом сопоставить
        # удалённое сообщение по message_id.
        await message_service.store_message_data(await extract(event.message))

    @client.on(events.MessageEdited())
    async def on_message_edited(event: events.MessageEdited.Event) -> None:
        result = await message_service.store_edit_data(await extract(event.message))
        if result.changed:
            await notifier.notify_edit(
                bot, result.message, result.old_text, result.new_text
            )

    @client.on(events.MessageDeleted())
    async def on_message_deleted(event: events.MessageDeleted.Event) -> None:
        # Долгожданное: MTProto присылает событие об удалении в реальном времени.
        async with async_session_factory() as session:
            async with session.begin():
                deleted = await crud.mark_deleted_by_ids(
                    session, event.deleted_ids, event.chat_id
                )
            # Внутри контекста сессии (expire_on_commit=False) атрибуты доступны.
            for message in deleted:
                await notifier.notify_deleted(bot, message)

        if deleted:
            logger.info(
                "Userbot зафиксировал удаление %d сообщений (chat=%s)",
                len(deleted), event.chat_id,
            )
