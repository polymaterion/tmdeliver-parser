"""Обработка одного сообщения: фильтр -> дубликаты -> запись в БД. Не зависит от Telethon."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from app.filter.dedup import hamming
from app.filter.engine import FilterEngine, fingerprint

log = logging.getLogger(__name__)


def hash_sender(salt: str, sender_id: int | None) -> str | None:
    if sender_id is None:
        return None
    return hashlib.sha256(f"{salt}|{sender_id}".encode()).hexdigest()[:32]


async def find_duplicate(conn, a, fp: str | None) -> int | None:
    row = await conn.fetchrow(
        "SELECT id FROM matches WHERE text_hash=$1 AND sent_at > now() - interval '14 days' ORDER BY id LIMIT 1", a.text_hash)
    if row:
        return row["id"]
    if fp:
        row = await conn.fetchrow(
            "SELECT id FROM matches WHERE fingerprint=$1 AND sent_at > now() - interval '14 days' ORDER BY id LIMIT 1", fp)
        if row:
            return row["id"]
    if len(a.skeleton.split()) >= 6:
        rows = await conn.fetch(
            "SELECT id, simhash FROM matches WHERE sent_at > now() - interval '7 days' AND simhash IS NOT NULL ORDER BY id DESC LIMIT 2000")
        for r in rows:
            if hamming(r["simhash"], a.simhash) <= 4:
                return r["id"]
    return None


async def process(pool, engine: FilterEngine, *, salt: str, store_min: int, source_id: int | None,
                  chat_id: int, chat_title: str | None, message_id: int, link: str | None,
                  sender_id: int | None, text: str, sent_at: datetime, get_profile=None) -> str:
    """Возвращает: 'skip' | 'stored' | 'duplicate' | 'exists'."""
    a = engine.analyze(text, now=sent_at)
    if a.excluded or a.score < store_min:
        return "skip"
    sender_hash = hash_sender(salt, sender_id)
    profile_url = None
    if get_profile is not None:           # профиль запрашиваем только для сохраняемых сообщений
        try:
            profile_url = await get_profile()
        except Exception as e:  # noqa: BLE001
            log.warning("не удалось получить профиль автора: %s", type(e).__name__)
    fp = fingerprint(a, salt, sender_hash)
    async with pool.acquire() as conn:
        async with conn.transaction():
            dup = await find_duplicate(conn, a, fp)
            row = await conn.fetchrow(
                """INSERT INTO matches (source_id, chat_id, message_id, chat_title, link, sent_at, sender_hash, text,
                       score, level, category, direction, route, route_names, travel_date, date_text, reasons, rules,
                       text_hash, simhash, fingerprint, status, duplicate_of, profile_url)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24)
                   ON CONFLICT (chat_id, message_id) DO NOTHING RETURNING id""",
                source_id, chat_id, message_id, chat_title, link, sent_at, sender_hash, text,
                a.score, a.level, a.category, a.direction, a.route, a.route_names,
                datetime.fromisoformat(a.date_iso).date() if a.date_iso else None, a.date_text,
                [r.to_dict() for r in a.reasons], a.rules, a.text_hash, a.simhash, fp,
                "duplicate" if dup else "new", dup, profile_url,
            )
    if row is None:
        return "exists"
    log.info("match id=%s chat=%s msg=%s score=%s cat=%s status=%s", row["id"], chat_id, message_id, a.score, a.category, "duplicate" if dup else "new")
    return "duplicate" if dup else "stored"
