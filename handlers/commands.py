"""Команды бота: справка и админские запросы к истории сообщений."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from config import settings
from database import async_session_factory, crud
from services import formatter, message_service, notifier

from .filters import IsAdmin

logger = logging.getLogger(__name__)

router = Router(name="commands")

HELP_TEXT = (
    "<b>DialogSpyBot</b> — журналирование сообщений.\n\n"
    "Доступные команды (только для администраторов):\n"
    "• <code>/history [N]</code> — последние N сообщений этого чата\n"
    "• <code>/history_all [N]</code> — последние N сообщений по всем чатам\n"
    "• <code>/deleted [N]</code> — удалённые сообщения\n"
    "• <code>/search &lt;текст&gt;</code> — поиск по тексту\n"
    "• <code>/user &lt;@username|id&gt;</code> — сообщения пользователя\n"
    "• <code>/info &lt;message_id&gt;</code> — карточка сообщения с историей правок\n"
    "• <code>/markdeleted &lt;message_id&gt;</code> — пометить сообщение удалённым\n"
)


def _parse_limit(command: CommandObject, default: int) -> int:
    """Достаёт числовой лимит из аргумента команды, если он есть."""
    if command.args:
        token = command.args.strip().split()[0]
        if token.isdigit():
            return max(1, min(int(token), 100))
    return default


async def _reply_list(message: Message, items, title: str, empty: str) -> None:
    """Форматирует список сообщений и отправляет (с разбивкой на чанки)."""
    for chunk in formatter.render_list(items, title=title, empty=empty):
        await message.answer(chunk, disable_web_page_preview=True)


# --------------------------------------------------------------------------- #
# Публичные команды (доступны всем)                                           #
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Бот запущен и ведёт журнал сообщений.\n"
        "Наберите /help, чтобы увидеть список команд."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, disable_web_page_preview=True)


# --------------------------------------------------------------------------- #
# Админские команды (фильтр IsAdmin)                                          #
# --------------------------------------------------------------------------- #
@router.message(Command("history"), IsAdmin())
async def cmd_history(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command, settings.page_size)
    async with async_session_factory() as session:
        items = await crud.get_history(session, chat_id=message.chat.id, limit=limit)
    await _reply_list(
        message, items,
        title=f"История чата (последние {limit})",
        empty="В этом чате пока нет сохранённых сообщений.",
    )


@router.message(Command("history_all"), IsAdmin())
async def cmd_history_all(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command, settings.page_size)
    async with async_session_factory() as session:
        items = await crud.get_history(session, chat_id=None, limit=limit)
    await _reply_list(
        message, items,
        title=f"История по всем чатам (последние {limit})",
        empty="База сообщений пуста.",
    )


@router.message(Command("deleted"), IsAdmin())
async def cmd_deleted(message: Message, command: CommandObject) -> None:
    limit = _parse_limit(command, settings.page_size)
    async with async_session_factory() as session:
        items = await crud.get_deleted(session, limit=limit)
    await _reply_list(
        message, items,
        title="Удалённые сообщения",
        empty="Удалённых сообщений нет.",
    )


@router.message(Command("search"), IsAdmin())
async def cmd_search(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: <code>/search текст</code>")
        return
    query = command.args.strip()
    async with async_session_factory() as session:
        items = await crud.search_text(session, query, limit=settings.page_size)
    await _reply_list(
        message, items,
        title=f"Поиск по тексту: «{query}»",
        empty="Ничего не найдено.",
    )


@router.message(Command("user"), IsAdmin())
async def cmd_user(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: <code>/user @username</code> или <code>/user 123456</code>")
        return
    term = command.args.strip()
    async with async_session_factory() as session:
        items = await crud.search_user(session, term, limit=settings.page_size)
    await _reply_list(
        message, items,
        title=f"Сообщения пользователя: {term}",
        empty="Ничего не найдено.",
    )


@router.message(Command("info"), IsAdmin())
async def cmd_info(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.strip().split()[0].isdigit():
        await message.answer("Использование: <code>/info &lt;message_id&gt;</code> (id сообщения в этом чате)")
        return
    message_id = int(command.args.strip().split()[0])
    async with async_session_factory() as session:
        msg = await crud.get_with_edits(session, message.chat.id, message_id)
    if msg is None:
        await message.answer("Сообщение с таким message_id в этом чате не найдено.")
        return
    await message.answer(formatter.format_edits(msg, msg.edits), disable_web_page_preview=True)


@router.message(Command("markdeleted"), IsAdmin())
async def cmd_mark_deleted(message: Message, command: CommandObject, bot: Bot) -> None:
    """Ручная пометка удаления.

    Через Bot API Telegram НЕ присылает событий об удалении сообщений
    пользователями, поэтому удаление отмечается вручную администратором
    (или можно ответить этой командой на нужное сообщение). После пометки
    бот мгновенно рассылает админам исходный текст удалённого сообщения.
    """
    target_id: int | None = None
    if message.reply_to_message:
        target_id = message.reply_to_message.message_id
    elif command.args and command.args.strip().split()[0].isdigit():
        target_id = int(command.args.strip().split()[0])

    if target_id is None:
        await message.answer(
            "Использование: ответьте на сообщение командой <code>/markdeleted</code> "
            "или укажите id: <code>/markdeleted &lt;message_id&gt;</code>"
        )
        return

    saved = await message_service.mark_message_deleted(message.chat.id, target_id)
    if saved is not None:
        await message.answer(f"🗑 Сообщение <code>{target_id}</code> помечено как удалённое.")
        # Мгновенная рассылка исходника всем администраторам.
        await notifier.notify_deleted(bot, saved)
    else:
        await message.answer("Сообщение с таким message_id в этом чате не найдено.")
