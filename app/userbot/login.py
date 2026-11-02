"""Одноразовая интерактивная авторизация юзербота:
docker compose run --rm -it userbot python -m app.userbot.login"""
import asyncio

from telethon import TelegramClient

from app.common.config import load_settings


async def main() -> None:
    s = load_settings(need_userbot=True)
    client = TelegramClient(s.tg_session_path, s.tg_api_id, s.tg_api_hash)
    await client.start()  # спросит телефон, код, пароль 2FA
    me = await client.get_me()
    print(f"Авторизован как id={me.id}. Сессия сохранена: {s.tg_session_path}.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
