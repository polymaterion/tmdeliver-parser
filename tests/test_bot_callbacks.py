"""Кнопки под уведомлением не должны «зависать»: всегда отвечаем на нажатие, даже при отказе Telegram."""
import asyncio
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageReplyMarkup
from aiogram.types import ErrorEvent
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Kb

import app.bot.main as bm
from app.common.config import load_chats_config
from app.common.i18n import I18n


class FakePool:
    def __init__(self): self.sql = []
    async def fetchrow(self, sql, *a): return {"lang": "ru"} if "bot_users" in sql else None
    async def fetchval(self, sql, *a): return 1
    async def execute(self, sql, *a): self.sql.append(sql)


def _three_button_markup():
    """Уведомление БЕЗ кнопки профиля (Telegram её отклонил при отправке) — 3 кнопки."""
    return Kb(inline_keyboard=[
        [Btn(text="👍 Полезно", callback_data="fb:1:u"), Btn(text="👎 Не релевантно", callback_data="fb:1:i")],
        [Btn(text="💬 Сообщение", url="https://t.me/c/1/2")]])


class FakeCallback:
    def __init__(self, data, markup, edit_error=None):
        self.data, self.answered, self.edits = data, [], []
        self.from_user = SimpleNamespace(id=1, language_code="ru")
        self.message = SimpleNamespace(reply_markup=markup, edit_reply_markup=self._edit, edit_text=self._edit_text)
        self._edit_error = edit_error

    async def answer(self, text=None): self.answered.append(text)

    async def _edit(self, reply_markup=None):
        if self._edit_error:
            raise self._edit_error
        self.edits.append(reply_markup)

    async def _edit_text(self, text, reply_markup=None):
        if self._edit_error:
            raise self._edit_error
        self.edits.append(reply_markup)


def _bad(msg):
    return TelegramBadRequest(method=EditMessageReplyMarkup(chat_id=1), message=msg)


@pytest.fixture(autouse=True)
def state():
    bm.S.clear()
    bm.S.update(pool=FakePool(), i18n=I18n("locales"), admins={1}, cfg=load_chats_config("config/chats.yml"))


def test_feedback_on_three_button_notification():
    c = FakeCallback("fb:1:u", _three_button_markup())
    asyncio.run(bm.cb_feedback(c))
    assert len(c.answered) == 1 and len(c.edits) == 1
    rows = c.edits[0].inline_keyboard
    assert rows[0][0].text.startswith("✅") and not rows[0][1].text.startswith("✅")
    assert [b.url for b in rows[1]] == ["https://t.me/c/1/2"]      # ссылки не тронуты, новых кнопок нет
    assert sum(len(r) for r in rows) == 3


def test_feedback_four_buttons_keeps_profile_link():
    kb = Kb(inline_keyboard=[[Btn(text="👍 Полезно", callback_data="fb:1:u"), Btn(text="👎 Не релевантно", callback_data="fb:1:i")],
                             [Btn(text="👤 Профиль", url="https://t.me/ivan"), Btn(text="💬 Сообщение", url="https://t.me/c/1/2")]])
    c = FakeCallback("fb:1:i", kb)
    asyncio.run(bm.cb_feedback(c))
    rows = c.edits[0].inline_keyboard
    assert rows[0][1].text.startswith("✅") and [b.url for b in rows[1]] == ["https://t.me/ivan", "https://t.me/c/1/2"]


@pytest.mark.parametrize("error", ["Bad Request: message is not modified", "BUTTON_USER_PRIVACY_RESTRICTED", "message to edit not found"])
def test_telegram_rejecting_edit_does_not_hang(error):
    c = FakeCallback("fb:1:u", _three_button_markup(), edit_error=_bad(error))
    asyncio.run(bm.cb_feedback(c))                 # исключение наружу не выходит
    assert len(c.answered) == 1                    # на нажатие ответили — «часики» сняты


def test_old_removed_buttons_are_answered():
    for data in ("cs:5", "cs:5:done", "fb:1:d", "что-то:старое"):
        c = FakeCallback(data, _three_button_markup())
        handler = bm.cb_feedback if data.startswith("fb:") else bm.cb_unknown
        asyncio.run(handler(c))
        assert len(c.answered) == 1, data


def test_global_error_handler_answers_callback():
    c = FakeCallback("x", None)
    upd = SimpleNamespace(callback_query=c)
    assert asyncio.run(bm.on_error(SimpleNamespace(exception=RuntimeError("boom"), update=upd))) is True
    assert len(c.answered) == 1


def test_settings_language_buttons_survive_not_modified():
    c = FakeCallback("lang:ru", None, edit_error=_bad("message is not modified"))
    asyncio.run(bm.cb_lang(c))
    assert len(c.answered) == 1
