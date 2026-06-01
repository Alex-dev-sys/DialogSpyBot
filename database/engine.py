"""Асинхронный движок SQLAlchemy и фабрика сессий."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

# Импортируем Base уже со всеми зарегистрированными моделями,
# чтобы metadata.create_all знал обо всех таблицах.
from models import Base

logger = logging.getLogger(__name__)

# Единый движок и фабрика сессий на всё приложение.
engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _ensure_sqlite_dir() -> None:
    """Создаёт каталог под файл SQLite, если используется файловая БД."""
    url = settings.database_url
    marker = ":///"
    if "sqlite" in url and marker in url:
        # Часть после "///" — путь к файлу (для относительного DSN с тремя слэшами).
        db_path = url.split(marker, 1)[1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    """Создаёт таблицы при старте (автоматическое создание схемы)."""
    _ensure_sqlite_dir()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Схема БД готова (database_url=%s)", settings.database_url)


async def dispose_engine() -> None:
    """Корректно закрывает пул соединений при остановке бота."""
    await engine.dispose()
