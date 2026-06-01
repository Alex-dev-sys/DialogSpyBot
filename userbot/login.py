"""Однократный интерактивный вход в Telegram для создания файла сессии.

Запускается ОДИН раз в интерактивном терминале:
    python -m userbot.login
Telethon спросит номер телефона, код из Telegram и (при наличии) пароль 2FA,
после чего сохранит файл сессии (settings.userbot_session) для последующих
неинтерактивных запусков userbot.main.
"""
from __future__ import annotations

import asyncio

from userbot.client import build_client


async def main() -> None:
    client = build_client()
    # start() сам запросит телефон/код/пароль, если сессии ещё нет.
    await client.start()
    me = await client.get_me()
    print(f"✅ Авторизовано как @{me.username} (id={me.id}). Сессия сохранена.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
