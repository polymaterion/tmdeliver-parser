"""Конфигурация: секреты — из переменных окружения, список чатов — из config/chats.yml."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    v = os.environ.get(name, default)
    if required and not v:
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return v or ""


@dataclass
class Settings:
    database_url: str
    rules_dir: str
    config_path: str
    locales_dir: str
    migrations_dir: str
    hash_salt: str
    log_level: str
    tg_api_id: int = 0
    tg_api_hash: str = ""
    tg_session_path: str = "/secrets/userbot"
    bot_token: str = ""
    admin_ids: list[int] = field(default_factory=list)


def load_settings(need_userbot: bool = False, need_bot: bool = False) -> Settings:
    s = Settings(
        database_url=_env("DATABASE_URL", required=True),
        rules_dir=_env("RULES_DIR", "rules"),
        config_path=_env("CONFIG_PATH", "config/chats.yml"),
        locales_dir=_env("LOCALES_DIR", "locales"),
        migrations_dir=_env("MIGRATIONS_DIR", "migrations"),
        hash_salt=_env("HASH_SALT", "change-me"),
        log_level=_env("LOG_LEVEL", "INFO"),
    )
    if need_userbot:
        s.tg_api_id = int(_env("TG_API_ID", required=True))
        s.tg_api_hash = _env("TG_API_HASH", required=True)
        s.tg_session_path = _env("TG_SESSION_PATH", "/secrets/userbot")
    if need_bot:
        s.bot_token = _env("BOT_TOKEN", required=True)
        s.admin_ids = [int(x) for x in _env("ADMIN_IDS", required=True).replace(" ", "").split(",") if x]
    return s


def load_chats_config(path: str) -> dict:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    data = data or {}
    d = data.setdefault("defaults", {})
    d.setdefault("notify_threshold", 50)
    d.setdefault("max_sources", 25)
    d.setdefault("backfill_hours", 0)
    d.setdefault("notify_window_minutes", 720)
    d.setdefault("default_language", "ru")
    data.setdefault("sources", [])
    return data
