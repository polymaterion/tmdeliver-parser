"""Отправка уведомления: запасные варианты, если Telegram отклоняет кнопку профиля/разметку."""
import asyncio
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage

import app.bot.main as bm
from app.common.i18n import I18n


class FakePool:
    def __init__(self): self.sql = []
    async def fetchrow(self, *a): return {"lang": "ru"}
    async def execute(self, *a): self.sql.append(a)


class FakeBot:
    def __init__(self, fail_first: int):
        self.fail_first, self.calls = fail_first, []

    async def send_message(self, uid, **kw):
        self.calls.append(kw)
        if len(self.calls) <= self.fail_first:
            raise TelegramBadRequest(method=SendMessage(chat_id=uid, text="x"), message="BUTTON_USER_PRIVACY_RESTRICTED")
        return SimpleNamespace(message_id=99)


def _match():
    return dict(id=1, score=80, category="carrier_offer", direction="to_tm", route=["moscow", "ashgabat"],
                route_names={"moscow": {"ru": "Москва"}, "ashgabat": {"ru": "Ашхабад"}}, travel_date=None, date_text="5.11",
                chat_title="Чат", reasons=[], text="Лечу <b>", link="https://t.me/c/1/2", profile_url="tg://user?id=5")


@pytest.fixture(autouse=True)
def state():
    bm.S.clear()
    bm.S.update(pool=FakePool(), i18n=I18n("locales"), admins={1})


@pytest.mark.parametrize("fail_first,expected_calls", [(0, 1), (1, 2), (2, 3)])
def test_fallbacks(fail_first, expected_calls):
    bot = FakeBot(fail_first)
    assert asyncio.run(bm.send_match(bot, _match())) is True
    assert len(bot.calls) == expected_calls
    if fail_first >= 1:   # во втором варианте кнопки профиля уже нет
        rows = bot.calls[1]["reply_markup"].inline_keyboard
        assert all("tg://" not in (b.url or "") for r in rows for b in r)
    if fail_first == 2:
        assert "<" not in bot.calls[2]["text"] or "&lt;" not in bot.calls[2]["text"]
        assert bot.calls[2]["parse_mode"] is None
