"""Раскладка кнопок под уведомлением и ссылки на профиль."""
import pytest

from app.bot.render import VERDICTS, match_keyboard
from app.common.i18n import I18n
from app.common.links import profile_link


def _m(**kw):
    base = dict(id=7, link="https://t.me/chat/5", profile_url="https://t.me/user1")
    base.update(kw)
    return base


def _layout(kb):
    return [[b.text for b in row] for row in kb.inline_keyboard]


def test_layout_ru():
    kb = match_keyboard(I18n("locales"), "ru", _m())
    rows = _layout(kb)
    assert rows[0] == ["👍 Полезно", "👎 Не релевантно"]
    assert rows[1] == ["👤 Профиль", "💬 Сообщение"]
    urls = [b.url for b in kb.inline_keyboard[1]]
    assert urls == ["https://t.me/user1", "https://t.me/chat/5"]
    assert len(rows) == 2
    assert not any(w in t for row in rows for t in row for w in ("Дубликат", "Контакт"))


def test_no_duplicate_verdict():
    assert set(VERDICTS.values()) == {"useful", "irrelevant"}


@pytest.mark.parametrize("profile,link,expected", [
    (None, "https://t.me/chat/5", ["💬 Сообщение"]),
    ("https://t.me/u", None, ["👤 Профиль"]),
])
def test_missing_links_hide_buttons(profile, link, expected):
    rows = _layout(match_keyboard(I18n("locales"), "ru", _m(profile_url=profile, link=link)))
    assert rows[1] == expected


def test_no_links_at_all_only_feedback():
    rows = _layout(match_keyboard(I18n("locales"), "ru", _m(profile_url=None, link=None)))
    assert len(rows) == 1 and rows[0][0].endswith("Полезно")


def test_selected_verdict_marked():
    rows = _layout(match_keyboard(I18n("locales"), "tk", _m(), verdict="irrelevant"))
    assert rows[0][1].startswith("✅") and not rows[0][0].startswith("✅")


def test_profile_link():
    assert profile_link("ivan_k", 5) == "https://t.me/ivan_k"
    assert profile_link(None, 12345) == "tg://user?id=12345"
    assert profile_link(None, None) is None
    assert profile_link(None, -100123) is None      # каналы/анонимные админы
