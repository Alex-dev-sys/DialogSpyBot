"""ORM-модели: сохранённые сообщения и история их правок."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Message(Base):
    """Одно входящее сообщение Telegram.

    Пара (chat_id, message_id) уникальна — это естественный ключ
    сообщения в Telegram, по нему мы находим запись при правке/удалении.
    """

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("chat_id", "message_id", name="uq_chat_message"),
    )

    # Внутренний суррогатный первичный ключ.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Идентификаторы Telegram (BigInteger — id чатов/пользователей бывают большими).
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    # Профиль отправителя на момент получения сообщения.
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chat_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Текст (или подпись к медиа). Для медиа без подписи может быть NULL.
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Дата отправки сообщения (из Telegram).
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Флаги состояния.
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Служебные временные метки (заполняет БД).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # История правок: при каждом редактировании добавляется строка.
    edits: Mapped[list["MessageEdit"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageEdit.edited_at",
    )


class MessageEdit(Base):
    """Одна правка сообщения: храним старую и новую версию текста."""

    __tablename__ = "message_edits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_db_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )

    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped["Message"] = relationship(back_populates="edits")
