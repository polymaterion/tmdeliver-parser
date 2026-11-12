"""Экран настроек и смена языка (раньше падали: переменная Fluent $lang конфликтовала с параметром T)."""
import asyncio

import pytest

import app.bot.main as bm
from app.common.config import load_chats_config
from app.common.i18n import I18n


class FakePool:
    """Минимальная заглушка БД: настройки пустые (берутся значения по умолчанию), язык — ru."""
    async def fetchrow(self, sql, *a):
        return {"lang": "ru"} if "bot_users" in sql else None

    async def execute(self, *a): return None


@pytest.fixture(autouse=True)
def state():
    bm.S.clear()
    bm.S.update(pool=FakePool(), i18n=I18n("locales"), admins={1}, cfg=load_chats_config("config/chats.yml"))


def test_settings_view_renders():
    text, kb = asyncio.run(bm.settings_view(1))
    assert "50" in text and "Русский" in text
    assert len(kb.inline_keyboard) >= 7


def test_translator_accepts_variable_named_lang():
    assert "Русский" in bm.T("ru", "settings-title", threshold=1, notifications="x", lang="Русский")
