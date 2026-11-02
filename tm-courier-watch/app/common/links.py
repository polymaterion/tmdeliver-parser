def message_link(username: str | None, chat_id: int, message_id: int) -> str | None:
    """Ссылка на сообщение в публичном чате; для чатов без username — t.me/c/…"""
    if username:
        return f"https://t.me/{username}/{message_id}"
    s = str(chat_id)
    if s.startswith("-100"):
        return f"https://t.me/c/{s[4:]}/{message_id}"
    return None
