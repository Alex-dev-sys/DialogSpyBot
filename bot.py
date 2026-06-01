"""Точка входа: инициализация БД, регистрация роутеров, запуск polling."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database import dispose_engine, init_db
from handlers import commands, messages

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("dialogspybot")


async def main() -> None:
    # 1. Автоматически создаём таблицы при старте.
    await init_db()

    # 2. Бот с HTML-разметкой по умолчанию (для форматированного вывода).
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Порядок важен: сначала команды, потом «всеядный» перехватчик сообщений.
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    if not settings.admin_ids:
        logger.warning("ADMIN_IDS пуст — админские команды будут недоступны всем!")

    logger.info("Бот запускается (admins=%s)…", settings.admin_ids)
    try:
        # Сбрасываем накопившиеся за время простоя апдейты и стартуем polling.
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await dispose_engine()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки.")
