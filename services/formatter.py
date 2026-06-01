"""Форматирование сообщений для отправки в Telegram (HTML)."""
from __future__ import annotations

from collections.abc import Iterable
from html import escape

from models import Message, MessageEdit

# Лимит Telegram на длину одного сообщения.
TELEGRAM_MAX_LEN = 4096


def _fmt_dt(dt) -> str:
    """Дата в читаемом виде (UTC)."""
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_message(message: Message) -> str:
    """Форматирует одно сообщение в HTML-блок."""
    flags = []
    if message.is_edited:
        flags.append("✏️ изменено")
    if message.is_deleted:
        flags.append(f"🗑 удалено ({_fmt_dt(message.deleted_at)})")
    flags_line = ("  " + " | ".join(flags)) if flags else ""

    username = f"@{message.username}" if message.username else "—"
    name = escape(message.full_name or "Неизвестный")
    text = escape(message.text) if message.text else "<i>(без текста / медиа)</i>"

    return (
        f"<b>#{message.id}</b> · chat <code>{message.chat_id}</code> · "
        f"msg <code>{message.message_id}</code>{flags_line}\n"
        f"👤 {name} ({escape(username)}) · id <code>{message.user_id}</code>\n"
        f"🕒 {_fmt_dt(message.date)}\n"
        f"{text}"
    )


def _who(message: Message) -> str:
    """Строка-«шапка» с автором и координатами сообщения."""
    username = f"@{message.username}" if message.username else "—"
    name = escape(message.full_name or "Неизвестный")
    return (
        f"👤 {name} ({escape(username)}) · id <code>{message.user_id}</code>\n"
        f"💬 chat <code>{message.chat_id}</code> · msg <code>{message.message_id}</code>"
    )


def format_edit_alert(message: Message, old_text: str | None, new_text: str | None) -> str:
    """Мгновенное уведомление о правке: было → стало."""
    old = escape(old_text) if old_text else "<i>(не сохранено / пусто)</i>"
    new = escape(new_text) if new_text else "<i>(пусто)</i>"
    return (
        "✏️ <b>Сообщение изменено</b>\n"
        f"{_who(message)}\n"
        f"🕒 отправлено: {_fmt_dt(message.date)}\n\n"
        f"<b>Было:</b>\n{old}\n\n"
        f"<b>Стало:</b>\n{new}"
    )


def format_deleted_alert(message: Message) -> str:
    """Мгновенное уведомление об удалении: исходный текст."""
    text = escape(message.text) if message.text else "<i>(без текста / медиа)</i>"
    return (
        "🗑 <b>Сообщение удалено</b>\n"
        f"{_who(message)}\n"
        f"🕒 отправлено: {_fmt_dt(message.date)}\n"
        f"🕒 удалено: {_fmt_dt(message.deleted_at)}\n\n"
        f"<b>Исходный текст:</b>\n{text}"
    )


def format_edits(message: Message, edits: Iterable[MessageEdit]) -> str:
    """Подробная история правок одного сообщения."""
    header = format_message(message)
    lines = [header, "\n<b>История правок:</b>"]
    edits = list(edits)
    if not edits:
        lines.append("<i>правок не зафиксировано</i>")
    for i, edit in enumerate(edits, start=1):
        old = escape(edit.old_text) if edit.old_text else "<i>(пусто)</i>"
        new = escape(edit.new_text) if edit.new_text else "<i>(пусто)</i>"
        lines.append(
            f"\n<b>{i}.</b> {_fmt_dt(edit.edited_at)}\n"
            f"➖ {old}\n"
            f"➕ {new}"
        )
    return "\n".join(lines)


def render_list(messages: Iterable[Message], title: str, empty: str) -> list[str]:
    """Собирает список сообщений в текст и режет на чанки <= 4096 символов.

    Возвращает список строк — каждую нужно отправить отдельным сообщением.
    """
    messages = list(messages)
    if not messages:
        return [f"<b>{escape(title)}</b>\n\n{escape(empty)}"]

    blocks = [f"<b>{escape(title)}</b> (найдено: {len(messages)})"]
    blocks += [format_message(m) for m in messages]

    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) > TELEGRAM_MAX_LEN:
            if current:
                chunks.append(current)
            # Отдельный слишком длинный блок укорачиваем принудительно.
            current = block[:TELEGRAM_MAX_LEN]
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
