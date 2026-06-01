"""Точка входа userbot-процесса (Telethon)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database import dispose_engine, init_db
from userbot import handlers
from userbot.client import build_client

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("dialogspybot.userbot")


async def main() -> None:
    # Таблицы общие с ботом — создаём, если запущен только userbot.
    await init_db()

    # aiogram-бот нужен лишь как «отправитель» уведомлений админам.
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    client = build_client()
    await client.connect()
    if not await client.is_user_authorized():
        # В контейнере интерактивный ввод невозможен — просим залогиниться заранее.
        await client.disconnect()
        await bot.session.close()
        raise SystemExit(
            "Userbot не авторизован. Выполните однократный вход:\n"
            "  python -m userbot.login"
        )

    handlers.register(client, bot)
    me = await client.get_me()
    logger.info("Userbot запущен как @%s (id=%s). Слежу за удалениями/правками…",
                me.username, me.id)

    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        await bot.session.close()
        await dispose_engine()
        logger.info("Userbot остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки.")
