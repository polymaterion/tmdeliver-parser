def message_link(username: str | None, chat_id: int, message_id: int) -> str | None:
    """Ссылка на сообщение в публичном чате; для чатов без username — t.me/c/…"""
    if username:
        return f"https://t.me/{username}/{message_id}"
    s = str(chat_id)
    if s.startswith("-100"):
        return f"https://t.me/c/{s[4:]}/{message_id}"
    return None


def profile_link(username: str | None, user_id: int | None) -> str | None:
    """Ссылка на профиль автора: t.me/<username>, а без username — tg://user?id=<id>
    (откроется в Telegram, если это позволяют настройки приватности пользователя)."""
    if username:
        return f"https://t.me/{username}"
    if user_id and user_id > 0:
        return f"tg://user?id={user_id}"
    return None
