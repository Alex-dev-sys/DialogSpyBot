"""Операции доступа к данным (CRUD) поверх ORM-моделей.

Все функции принимают активную AsyncSession и не управляют транзакцией —
коммит/rollback делает вызывающий код (см. services.message_service).
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Message, MessageEdit


async def get_message(
    session: AsyncSession, chat_id: int, message_id: int
) -> Message | None:
    """Находит сообщение по естественному ключу (chat_id, message_id)."""
    stmt = select(Message).where(
        Message.chat_id == chat_id,
        Message.message_id == message_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_message(session: AsyncSession, data: dict) -> Message:
    """Сохраняет новое входящее сообщение."""
    message = Message(**data)
    session.add(message)
    await session.flush()  # получаем message.id, не закрывая транзакцию
    return message


async def add_edit(session: AsyncSession, data: dict) -> tuple[Message, str | None, bool]:
    """Регистрирует правку сообщения.

    Если оригинал у нас уже есть — пишем старую/новую версию в историю
    и обновляем актуальный текст. Если оригинала нет (бот добавлен позже
    или сообщение пришло до запуска) — создаём запись сразу как изменённую.

    Возвращает кортеж (сообщение, старый_текст, был_ли_изменён_текст),
    чтобы вызывающий код мог мгновенно уведомить администраторов.
    """
    chat_id = data["chat_id"]
    message_id = data["message_id"]
    new_text = data.get("text")

    message = await get_message(session, chat_id, message_id)
    if message is None:
        # Оригинал не сохранён — создаём запись и помечаем как изменённую.
        message = Message(**data)
        message.is_edited = True
        session.add(message)
        await session.flush()
        session.add(
            MessageEdit(message_db_id=message.id, old_text=None, new_text=new_text)
        )
        return message, None, True

    old_text = message.text
    changed = old_text != new_text
    # Если текст фактически не поменялся (правка медиа и т.п.) — историю не плодим.
    if changed:
        session.add(
            MessageEdit(
                message_db_id=message.id,
                old_text=old_text,
                new_text=new_text,
            )
        )
        message.text = new_text
    message.is_edited = True
    return message, old_text, changed


async def mark_deleted(
    session: AsyncSession, chat_id: int, message_id: int
) -> Message | None:
    """Помечает сообщение как удалённое (и проставляет время удаления)."""
    message = await get_message(session, chat_id, message_id)
    if message is not None:
        message.is_deleted = True
        message.deleted_at = datetime.now(timezone.utc)
    return message


async def get_history(
    session: AsyncSession,
    chat_id: int | None = None,
    limit: int = 20,
    include_deleted: bool = True,
) -> Sequence[Message]:
    """Последние сообщения (опционально по конкретному чату)."""
    stmt = select(Message).order_by(desc(Message.date)).limit(limit)
    if chat_id is not None:
        stmt = stmt.where(Message.chat_id == chat_id)
    if not include_deleted:
        stmt = stmt.where(Message.is_deleted.is_(False))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_deleted(
    session: AsyncSession, chat_id: int | None = None, limit: int = 20
) -> Sequence[Message]:
    """Удалённые сообщения."""
    stmt = (
        select(Message)
        .where(Message.is_deleted.is_(True))
        .order_by(desc(Message.deleted_at))
        .limit(limit)
    )
    if chat_id is not None:
        stmt = stmt.where(Message.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def search_text(
    session: AsyncSession, query: str, limit: int = 20
) -> Sequence[Message]:
    """Поиск по подстроке в тексте (регистронезависимо)."""
    pattern = f"%{query}%"
    stmt = (
        select(Message)
        .where(Message.text.ilike(pattern))
        .order_by(desc(Message.date))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def search_user(
    session: AsyncSession, term: str, limit: int = 20
) -> Sequence[Message]:
    """Поиск сообщений пользователя по username или числовому user_id."""
    conditions = [Message.username.ilike(f"%{term.lstrip('@')}%")]
    # Если передали число — ищем ещё и по user_id.
    if term.isdigit():
        conditions.append(Message.user_id == int(term))

    stmt = (
        select(Message)
        .where(or_(*conditions))
        .order_by(desc(Message.date))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_with_edits(
    session: AsyncSession, chat_id: int, message_id: int
) -> Message | None:
    """Сообщение вместе с полной историей правок (eager-загрузка)."""
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id, Message.message_id == message_id)
        .options(selectinload(Message.edits))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
