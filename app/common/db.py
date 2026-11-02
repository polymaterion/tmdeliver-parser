"""PostgreSQL: пул соединений, SQL-миграции (с advisory lock), настройки."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import asyncpg

log = logging.getLogger(__name__)
_LOCK = 727001


async def create_pool(dsn: str) -> asyncpg.Pool:
    async def init(conn):
        await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    return await asyncpg.create_pool(dsn, min_size=1, max_size=5, init=init)


async def migrate(pool: asyncpg.Pool, directory: str) -> None:
    files = sorted(Path(directory).glob("*.sql"))
    async with pool.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock($1)", _LOCK)
        try:
            await conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
            done = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
            for f in files:
                if f.name in done:
                    continue
                log.info("Применяю миграцию %s", f.name)
                async with conn.transaction():
                    await conn.execute(f.read_text(encoding="utf-8"))
                    await conn.execute("INSERT INTO schema_migrations(version) VALUES($1)", f.name)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", _LOCK)


async def get_setting(pool, key: str, default=None):
    row = await pool.fetchrow("SELECT value FROM settings WHERE key=$1", key)
    return row["value"] if row else default


async def set_setting(pool, key: str, value) -> None:
    await pool.execute(
        "INSERT INTO settings(key,value) VALUES($1,$2) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()",
        key, value,
    )
