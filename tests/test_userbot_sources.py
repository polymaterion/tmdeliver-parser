"""Поиск приватного чата по числовому id среди диалогов аккаунта (без сети, на заглушках)."""
import asyncio
from types import SimpleNamespace

import pytest
from telethon.tl.types import Channel

from app.userbot.main import Userbot


def _chan(cid: int):
    return Channel(id=cid, title="Private", photo=None, date=None, megagroup=True, access_hash=1)


class FakeClient:
    def __init__(self, entities):
        self.entities, self.calls = entities, 0

    async def iter_dialogs(self):
        self.calls += 1
        for e in self.entities:
            yield SimpleNamespace(entity=e)


def _bot(entities):
    b = Userbot(SimpleNamespace(rules_dir="rules"), {"sources": [], "defaults": {"max_sources": 25, "backfill_hours": 0}})
    b.client = FakeClient(entities)
    return b


def test_private_chat_found_by_full_and_short_id():
    for ref in ("-1001234567890", "1234567890"):
        b = _bot([_chan(1234567890), _chan(999)])
        b._numeric_refs = [ref]
        ent = asyncio.run(b._entity_by_id(int(ref)))
        assert ent.id == 1234567890
        assert list(b._dialogs) == [-1001234567890]   # чужие диалоги не запоминаются


def test_unknown_private_chat_gives_clear_error():
    b = _bot([_chan(5)])
    b._numeric_refs = ["-1009999999999"]
    with pytest.raises(ValueError, match="не найден"):
        asyncio.run(b._entity_by_id(-1009999999999))
