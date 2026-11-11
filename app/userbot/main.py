"""Юзербот: слушает только перечисленные публичные чаты и передаёт сообщения в фильтр."""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events, utils
from telethon.tl.types import User
from telethon.errors import (AuthKeyError, ChannelPrivateError, FloodWaitError,
                             UsernameInvalidError, UsernameNotOccupiedError)

from app.common.config import load_chats_config, load_settings
from app.common.db import create_pool, get_setting, migrate
from app.common.links import message_link
from app.common.logging_setup import setup_logging
from app.filter.engine import FilterEngine
from app.userbot.pipeline import process

log = logging.getLogger("userbot")
_USERNAME = re.compile(r"^(?:https?://)?(?:t\.me/)?@?([A-Za-z][A-Za-z0-9_]{3,31})/?$")


class Userbot:
    def __init__(self, settings, chats_cfg):
        self.s = settings
        self.cfg = chats_cfg
        self.engine = FilterEngine.from_dir(settings.rules_dir)
        self.pool = None
        self.client: TelegramClient | None = None
        self.sources: dict[int, dict] = {}          # chat_id -> {id, title, username, entity}
        self.watermark: dict[int, int] = {}          # chat_id -> последний обработанный message_id
        self._dirty: set[int] = set()
        self.seen: OrderedDict[tuple[int, int], None] = OrderedDict()
        self._dialogs: dict[int, object] = {}        # кэш peer_id -> entity (только для поиска по числовому id)
        self._dialogs_at = -1e9
        self._numeric_refs: list[str] = []

    # ---------------- источники ----------------
    async def seed_sources(self) -> None:
        for item in self.cfg["sources"]:
            ref = str(item.get("username") or item.get("id") or "").lstrip("@")
            if not ref:
                continue
            await self.pool.execute(
                "INSERT INTO sources(ref, title, enabled, origin) VALUES($1,$2,$3,'config') "
                "ON CONFLICT (ref) DO UPDATE SET title=COALESCE(EXCLUDED.title, sources.title)",
                ref, item.get("title"), bool(item.get("enabled", True)))

    async def _entity_by_id(self, num: int):
        """Чат по числовому id (в т.ч. приватный), если аккаунт в нём состоит.
        Список диалогов читается только чтобы найти ЗАПРОШЕННЫЙ id; остальные диалоги отбрасываются."""
        wanted = {num} | ({int("-100" + str(num))} if num > 0 else set())
        for attempt in (0, 1):
            for pid in wanted:
                if pid in self._dialogs:
                    return self._dialogs[pid]
            if attempt == 0 and time.monotonic() - self._dialogs_at > 600:
                self._dialogs_at = time.monotonic()
                found: dict[int, object] = {}
                async for d in self.client.iter_dialogs():
                    pid = utils.get_peer_id(d.entity)
                    if pid in self._all_wanted_ids():
                        found[pid] = d.entity
                self._dialogs.update(found)
            else:
                break
        raise ValueError("чат не найден среди диалогов аккаунта (вступите в него)")

    def _all_wanted_ids(self) -> set[int]:
        out: set[int] = set()
        for ref in self._numeric_refs:
            n = int(ref)
            out |= {n} | ({int("-100" + str(n))} if n > 0 else set())
        return out

    async def sync_sources(self) -> None:
        rows = await self.pool.fetch("SELECT * FROM sources WHERE enabled ORDER BY id LIMIT $1", int(self.cfg["defaults"]["max_sources"]))
        active: dict[int, dict] = {}
        self._numeric_refs = [r["ref"] for r in rows if r["ref"].lstrip("-").isdigit()]
        for r in rows:
            known = next((c for c, v in self.sources.items() if v["id"] == r["id"]), None)
            if known:
                active[known] = self.sources[known]
                continue
            try:
                if r["ref"].lstrip("-").isdigit():
                    ent = await self._entity_by_id(int(r["ref"]))
                else:
                    mt = _USERNAME.match(r["ref"])
                    if not mt:
                        raise ValueError("недопустимая ссылка (нужен @username или числовой id чата)")
                    ent = await self.client.get_entity(mt.group(1))
                if isinstance(ent, User):
                    raise ValueError("личные переписки не поддерживаются")
                cid = utils.get_peer_id(ent)
                title = getattr(ent, "title", None) or r["title"]
                uname = getattr(ent, "username", None)
                await self.pool.execute("UPDATE sources SET chat_id=$2, title=$3, username=$4, resolve_error=NULL, updated_at=now() WHERE id=$1", r["id"], cid, title, uname)
                active[cid] = {"id": r["id"], "title": title, "username": uname, "entity": ent}
                self.watermark.setdefault(cid, r["last_message_id"])
                log.info("источник подключён: id=%s chat=%s", r["id"], cid)
            except FloodWaitError as e:
                log.warning("FloodWait при разборе источника: %ss", e.seconds)
                await asyncio.sleep(e.seconds + 1)
            except (UsernameNotOccupiedError, UsernameInvalidError, ChannelPrivateError, ValueError) as e:
                await self.pool.execute("UPDATE sources SET resolve_error=$2, updated_at=now() WHERE id=$1", r["id"], str(e)[:80] if isinstance(e, ValueError) else type(e).__name__)
                log.warning("источник id=%s недоступен: %s", r["id"], type(e).__name__)
            except Exception as e:  # noqa: BLE001
                log.exception("ошибка разбора источника id=%s: %s", r["id"], type(e).__name__)
        self.sources = active

    # ---------------- сообщения ----------------
    def _mark_seen(self, chat_id: int, mid: int) -> bool:
        key = (chat_id, mid)
        if key in self.seen:
            return False
        self.seen[key] = None
        if len(self.seen) > 20000:
            self.seen.popitem(last=False)
        return True

    async def handle(self, chat_id: int, msg) -> None:
        src = self.sources.get(chat_id)
        if not src or not getattr(msg, "message", None) or not self._mark_seen(chat_id, msg.id):
            return
        if msg.id > self.watermark.get(chat_id, 0):
            self.watermark[chat_id] = msg.id
            self._dirty.add(chat_id)
        thr = int((await get_setting(self.pool, "store_min", self.engine.thresholds["store_min"])))
        try:
            await process(
                self.pool, self.engine, salt=self.s.hash_salt, store_min=thr, source_id=src["id"],
                chat_id=chat_id, chat_title=src["title"], message_id=msg.id,
                link=message_link(src["username"], chat_id, msg.id), sender_id=msg.sender_id,
                text=msg.message, sent_at=msg.date.astimezone(timezone.utc))
        except Exception:  # noqa: BLE001
            log.exception("ошибка обработки chat=%s msg=%s", chat_id, msg.id)

    async def on_new(self, event) -> None:
        if event.is_private:                    # личные переписки не читаем
            return
        await self.handle(event.chat_id, event.message)

    async def gap_fill(self) -> None:
        """Докачка пропущенного (после обрыва связи) — только по настроенным чатам, идемпотентно."""
        hours = int(self.cfg["defaults"]["backfill_hours"])
        for cid, src in list(self.sources.items()):
            try:
                wm = self.watermark.get(cid, 0)
                if wm:
                    it = self.client.iter_messages(src["entity"], min_id=wm, limit=300, reverse=True)
                elif hours > 0:
                    since = datetime.now(timezone.utc) - timedelta(hours=hours)
                    it = self.client.iter_messages(src["entity"], offset_date=since, limit=500, reverse=True)
                else:
                    last = await self.client.get_messages(src["entity"], limit=1)
                    if last:
                        self.watermark[cid] = last[0].id
                        self._dirty.add(cid)
                    continue
                async for m in it:
                    await self.handle(cid, m)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:  # noqa: BLE001
                log.warning("gap_fill chat=%s: %s", cid, type(e).__name__)

    async def flush_watermarks(self) -> None:
        for cid in list(self._dirty):
            await self.pool.execute("UPDATE sources SET last_message_id=GREATEST(last_message_id,$2) WHERE chat_id=$1", cid, self.watermark[cid])
            self._dirty.discard(cid)

    async def maintenance(self) -> None:
        n = 0
        while True:
            await asyncio.sleep(60)
            n += 1
            try:
                await self.sync_sources()
                await self.flush_watermarks()
                if n % 5 == 0:
                    await self.gap_fill()
                if self.engine.changed():
                    self.engine = FilterEngine.from_dir(self.s.rules_dir)
                    log.info("словари перезагружены")
            except Exception:  # noqa: BLE001
                log.exception("ошибка фонового обслуживания")

    # ---------------- жизненный цикл ----------------
    async def run(self) -> None:
        self.pool = await create_pool(self.s.database_url)
        await migrate(self.pool, self.s.migrations_dir)
        await self.seed_sources()
        delay = 5
        while True:
            self.client = TelegramClient(
                self.s.tg_session_path, self.s.tg_api_id, self.s.tg_api_hash,
                connection_retries=-1, retry_delay=5, auto_reconnect=True, sequential_updates=True)
            self.client.add_event_handler(self.on_new, events.NewMessage(incoming=True))
            task = None
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    log.error("Сессия не авторизована. Выполните: docker compose run --rm -it userbot python -m app.userbot.login")
                    await asyncio.sleep(3600)
                    continue
                await self.sync_sources()
                await self.gap_fill()
                task = asyncio.create_task(self.maintenance())
                log.info("юзербот запущен, источников: %d", len(self.sources))
                delay = 5
                await self.client.run_until_disconnected()
            except AuthKeyError:
                log.error("Ключ авторизации недействителен — повторите вход (login)")
                await asyncio.sleep(3600)
            except FloodWaitError as e:
                log.warning("FloodWait %ss", e.seconds)
                await asyncio.sleep(e.seconds + 1)
            except Exception as e:  # noqa: BLE001
                log.exception("соединение потеряно: %s", type(e).__name__)
            finally:
                if task:
                    task.cancel()
                await self.flush_watermarks()
                try:
                    await self.client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
            log.info("переподключение через %ss", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 300)


def main() -> None:
    s = load_settings(need_userbot=True)
    setup_logging(s.log_level)
    asyncio.run(Userbot(s, load_chats_config(s.config_path)).run())


if __name__ == "__main__":
    main()
