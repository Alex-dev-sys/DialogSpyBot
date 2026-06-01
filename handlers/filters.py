"""Кастомные фильтры aiogram."""
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import settings


class IsAdmin(BaseFilter):
    """Пропускает апдейт, только если отправитель есть в списке ADMIN_IDS."""

    async def __call__(self, message: Message) -> bool:
        user = message.from_user
        return user is not None and user.id in settings.admin_ids
