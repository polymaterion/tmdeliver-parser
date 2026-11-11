"""Бот управления и уведомлений (aiogram 3). Доступ — только для ADMIN_IDS."""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import re

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject
from aiogram.types import BotCommand, BufferedInputFile, CallbackQuery, Message
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Kb

from app.bot.render import (CATEGORIES, VERDICTS, contact_keyboard, esc, fmt_date, match_keyboard,
                            render_match, route_text)
from app.common.config import load_chats_config, load_settings
from app.common.db import create_pool, get_setting, migrate, set_setting
from app.common.i18n import I18n
from app.common.logging_setup import setup_logging
from app.filter.engine import FilterEngine

log = logging.getLogger("bot")
router = Router()
_SRC_RE = re.compile(r"^(?:https?://)?(?:t\.me/)?@?([A-Za-z][A-Za-z0-9_]{3,31})/?$")

# глобальное состояние процесса (заполняется в main)
S: dict = {}


class AdminOnly(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user or user.id not in S["admins"]:
            return None  # молча игнорируем посторонних
        return await handler(event, data)


async def lang_of(uid: int, code: str | None = None) -> str:
    row = await S["pool"].fetchrow("SELECT lang FROM bot_users WHERE user_id=$1", uid)
    if row and row["lang"] in S["i18n"].languages:
        return row["lang"]
    lang = S["i18n"].pick(code) if code else S["cfg"]["defaults"]["default_language"]
    await S["pool"].execute("INSERT INTO bot_users(user_id, lang) VALUES($1,$2) ON CONFLICT DO NOTHING", uid, lang)
    return lang


def T(lang: str, key: str, **kw) -> str:
    return S["i18n"].t(lang, key, **kw)


# ---------------------------------------------------------------- команды
@router.message(Command("start", "help"))
async def cmd_start(m: Message):
    await lang_of(m.from_user.id, m.from_user.language_code)
    lang = await lang_of(m.from_user.id)
    await m.answer(T(lang, "start-text"))


async def settings_view(uid: int):
    lang = await lang_of(uid)
    pool = S["pool"]
    thr = await get_setting(pool, "threshold", S["cfg"]["defaults"]["notify_threshold"])
    on = await get_setting(pool, "notifications", True)
    cats = await get_setting(pool, "categories", CATEGORIES)
    text = T(lang, "settings-title", threshold=thr, notifications=T(lang, "on" if on else "off"), lang=T(lang, "lang-name"))
    rows = [
        [Btn(text=T(lang, "btn-thr-minus"), callback_data="set:thr:-5"), Btn(text=T(lang, "btn-thr-plus"), callback_data="set:thr:5")],
        [Btn(text=T(lang, "btn-toggle-notify", state=T(lang, "on" if on else "off")), callback_data="set:notif")],
    ]
    for c in CATEGORIES:
        rows.append([Btn(text=T(lang, "btn-cat", state="✅" if c in cats else "⬜", name=T(lang, "cat-" + c)), callback_data=f"set:cat:{c}")])
    rows.append([Btn(text=T(lang, "btn-lang"), callback_data="set:lang")])
    return text, Kb(inline_keyboard=rows)


@router.message(Command("settings"))
async def cmd_settings(m: Message):
    text, kb = await settings_view(m.from_user.id)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("set:"))
async def cb_settings(c: CallbackQuery):
    pool, parts = S["pool"], c.data.split(":")
    if parts[1] == "thr":
        cur = await get_setting(pool, "threshold", S["cfg"]["defaults"]["notify_threshold"])
        await set_setting(pool, "threshold", max(10, min(95, int(cur) + int(parts[2]))))
    elif parts[1] == "notif":
        await set_setting(pool, "notifications", not await get_setting(pool, "notifications", True))
    elif parts[1] == "cat":
        cats = list(await get_setting(pool, "categories", CATEGORIES))
        cats.remove(parts[2]) if parts[2] in cats else cats.append(parts[2])
        await set_setting(pool, "categories", cats)
    elif parts[1] == "lang":
        await c.message.edit_text(T(await lang_of(c.from_user.id), "lang-choose"), reply_markup=lang_keyboard())
        return await c.answer()
    text, kb = await settings_view(c.from_user.id)
    try:
        await c.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await c.answer()


def lang_keyboard() -> Kb:
    return Kb(inline_keyboard=[[Btn(text=S["i18n"].t(code, "lang-name"), callback_data=f"lang:{code}")] for code in S["i18n"].languages])


@router.message(Command("lang"))
async def cmd_lang(m: Message):
    await m.answer(T(await lang_of(m.from_user.id), "lang-choose"), reply_markup=lang_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery):
    code = c.data.split(":")[1]
    if code in S["i18n"].languages:
        await S["pool"].execute("INSERT INTO bot_users(user_id, lang) VALUES($1,$2) ON CONFLICT (user_id) DO UPDATE SET lang=$2", c.from_user.id, code)
    text, kb = await settings_view(c.from_user.id)
    await c.message.edit_text(text, reply_markup=kb)
    await c.answer(T(code, "lang-set"))


# ---------------------------------------------------------------- источники
async def sources_view(uid: int):
    lang = await lang_of(uid)
    rows = await S["pool"].fetch("SELECT * FROM sources ORDER BY id")
    mx = S["cfg"]["defaults"]["max_sources"]
    if not rows:
        return T(lang, "sources-empty"), None
    lines, kb = [T(lang, "sources-title", count=sum(r["enabled"] for r in rows), max=mx)], []
    for r in rows:
        title = r["title"] or r["ref"]
        note = T(lang, "source-error", error=esc(r["resolve_error"])) if r["resolve_error"] else ""
        state = "✅" if r["enabled"] else "⏸"
        lines.append(T(lang, "source-line", state=state, title=esc(title), note=note))
        kb.append([Btn(text=f"{state} {title[:40]}", callback_data=f"src:{r['id']}")])
    return "\n".join(lines), Kb(inline_keyboard=kb)


@router.message(Command("sources"))
async def cmd_sources(m: Message):
    text, kb = await sources_view(m.from_user.id)
    await m.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("src:"))
async def cb_source(c: CallbackQuery):
    await S["pool"].execute("UPDATE sources SET enabled = NOT enabled, updated_at=now() WHERE id=$1", int(c.data.split(":")[1]))
    text, kb = await sources_view(c.from_user.id)
    try:
        await c.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await c.answer(T(await lang_of(c.from_user.id), "source-toggled"))


@router.message(Command("add_source"))
async def cmd_add_source(m: Message, command: CommandObject):
    lang = await lang_of(m.from_user.id)
    arg = (command.args or "").strip()
    if not arg:
        return await m.answer(T(lang, "add-source-usage"))
    mt = _SRC_RE.match(arg)
    ref = mt.group(1) if mt else (arg if re.fullmatch(r"-?\d{6,}", arg) else None)
    if not ref:
        return await m.answer(T(lang, "add-source-bad"))
    cnt = await S["pool"].fetchval("SELECT count(*) FROM sources WHERE enabled")
    if cnt >= S["cfg"]["defaults"]["max_sources"]:
        return await m.answer(T(lang, "add-source-limit", max=S["cfg"]["defaults"]["max_sources"]))
    await S["pool"].execute("INSERT INTO sources(ref, enabled, origin) VALUES($1, TRUE, 'bot') ON CONFLICT (ref) DO UPDATE SET enabled=TRUE", ref)
    await m.answer(T(lang, "add-source-ok"))


# ---------------------------------------------------------------- оценки и статусы
async def _match(mid: int) -> dict | None:
    r = await S["pool"].fetchrow("SELECT * FROM matches WHERE id=$1", mid)
    return dict(r) if r else None


async def _verdict(mid: int, uid: int) -> str | None:
    return await S["pool"].fetchval("SELECT verdict FROM feedback WHERE match_id=$1 AND user_id=$2", mid, uid)


@router.callback_query(F.data.startswith("fb:"))
async def cb_feedback(c: CallbackQuery):
    _, mid, code = c.data.split(":")
    lang = await lang_of(c.from_user.id)
    if code not in VERDICTS:              # старые уведомления с удалённой кнопкой «Дубликат»
        return await c.answer()
    m = await _match(int(mid))
    if not m:
        return await c.answer(T(lang, "no-match"))
    await S["pool"].execute(
        "INSERT INTO feedback(match_id,user_id,verdict) VALUES($1,$2,$3) ON CONFLICT (match_id,user_id) DO UPDATE SET verdict=$3, created_at=now()",
        m["id"], c.from_user.id, VERDICTS[code])
    await c.message.edit_reply_markup(reply_markup=match_keyboard(S["i18n"], lang, m, VERDICTS[code]))
    await c.answer(T(lang, "fb-saved"))


@router.callback_query(F.data.startswith("cs:"))
async def cb_contact(c: CallbackQuery):
    parts = c.data.split(":")
    lang = await lang_of(c.from_user.id)
    m = await _match(int(parts[1]))
    if not m:
        return await c.answer(T(lang, "no-match"))
    if len(parts) == 2:
        await c.message.edit_reply_markup(reply_markup=contact_keyboard(S["i18n"], lang, m["id"], m["contact_status"]))
        return await c.answer(T(lang, "contact-menu"))
    if parts[2] != "back":
        await S["pool"].execute("UPDATE matches SET contact_status=$2, contact_updated_at=now() WHERE id=$1", m["id"], parts[2])
        m["contact_status"] = parts[2]
    await c.message.edit_reply_markup(reply_markup=match_keyboard(S["i18n"], lang, m, await _verdict(m["id"], c.from_user.id)))
    await c.answer(T(lang, "contact-saved"))


# ---------------------------------------------------------------- статистика, выгрузка, тест
@router.message(Command("stats"))
async def cmd_stats(m: Message):
    lang = await lang_of(m.from_user.id)
    p = S["pool"]
    q = "SELECT count(*) FILTER (WHERE true) total, count(*) FILTER (WHERE notified_at IS NOT NULL) notified, count(*) FILTER (WHERE status='duplicate') dups, " \
        "count(*) FILTER (WHERE contact_status='contacted') contacted, count(*) FILTER (WHERE contact_status='replied') replied, " \
        "count(*) FILTER (WHERE contact_status='agreed') agreed, count(*) FILTER (WHERE contact_status='done') done " \
        "FROM matches WHERE created_at > now() - interval '7 days'"
    r = await p.fetchrow(q)
    fb = {x["verdict"]: x["n"] for x in await p.fetch("SELECT verdict, count(*) n FROM feedback WHERE created_at > now() - interval '7 days' GROUP BY 1")}
    await m.answer(T(lang, "stats-text", **dict(r), useful=fb.get("useful", 0), irrelevant=fb.get("irrelevant", 0)))


@router.message(Command("export"))
async def cmd_export(m: Message):
    lang = await lang_of(m.from_user.id)
    rows = await S["pool"].fetch(
        """SELECT m.id, m.created_at, m.chat_title, m.link, m.score, m.category, m.direction, array_to_string(m.route,'>') route,
                  m.travel_date, array_to_string(m.rules,',') rules, m.status, m.contact_status,
                  (SELECT string_agg(f.verdict, ',') FROM feedback f WHERE f.match_id=m.id) verdict, m.text
           FROM matches m ORDER BY m.id""")
    if not rows:
        return await m.answer(T(lang, "export-empty"))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(rows[0].keys())
    for r in rows:
        w.writerow(list(r.values()))
    await m.answer_document(BufferedInputFile(buf.getvalue().encode("utf-8-sig"), "matches.csv"), caption=T(lang, "export-caption"))


@router.message(Command("test"))
async def cmd_test(m: Message, command: CommandObject):
    lang = await lang_of(m.from_user.id)
    if not command.args:
        return await m.answer(T(lang, "test-usage"))
    a = S["engine"].analyze(command.args)
    route = " → ".join((a.route_names.get(r, {}).get(lang) or a.route_names.get(r, {}).get("ru") or r) for r in a.route)
    out = T(lang, "test-result", score=a.score, level=a.level, category=T(lang, "cat-" + a.category), route=esc(route or "—"),
            direction=T(lang, "dir-" + a.direction), date=esc(a.date_text or "—"))
    from app.bot.render import reason_line
    out += "\n" + "\n".join(reason_line(S["i18n"], lang, r.to_dict()) for r in a.reasons)
    await m.answer(out)


# ---------------------------------------------------------------- рассылка уведомлений
async def send_match(bot: Bot, m: dict) -> bool:
    delivered = False
    for uid in S["admins"]:
        lang = await lang_of(uid)
        text, kb = render_match(S["i18n"], lang, m), match_keyboard(S["i18n"], lang, m)
        for attempt in range(3):
            try:
                msg = await bot.send_message(uid, text, reply_markup=kb, disable_web_page_preview=True)
                await S["pool"].execute("INSERT INTO notifications(match_id,user_id,tg_message_id) VALUES($1,$2,$3)", m["id"], uid, msg.message_id)
                delivered = True
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except TelegramForbiddenError:
                log.warning("пользователь %s заблокировал бота", uid)
                delivered = True
                break
            except Exception as e:  # noqa: BLE001
                log.warning("не удалось отправить уведомление: %s", type(e).__name__)
                await asyncio.sleep(2)
        await asyncio.sleep(0.4)
    return delivered


async def notifier(bot: Bot) -> None:
    pool, d = S["pool"], S["cfg"]["defaults"]
    while True:
        try:
            if await get_setting(pool, "notifications", True):
                thr = await get_setting(pool, "threshold", d["notify_threshold"])
                cats = await get_setting(pool, "categories", CATEGORIES)
                rows = await pool.fetch(
                    """UPDATE matches SET notified_at=now(), notify_attempts=notify_attempts+1
                       WHERE id IN (SELECT id FROM matches
                                    WHERE notified_at IS NULL AND status='new' AND score >= $1 AND category = ANY($2)
                                      AND created_at > now() - make_interval(mins => $3) AND notify_attempts < 3
                                    ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED)
                       RETURNING *""", int(thr), list(cats), int(d["notify_window_minutes"]))
                for r in rows:
                    if not await send_match(bot, dict(r)):
                        await pool.execute("UPDATE matches SET notified_at=NULL WHERE id=$1", r["id"])
        except Exception:  # noqa: BLE001
            log.exception("ошибка цикла уведомлений")
        await asyncio.sleep(3)


async def set_commands(bot: Bot) -> None:
    names = ["start", "settings", "sources", "add_source", "stats", "export", "test", "lang"]
    for code in S["i18n"].languages:
        cmds = [BotCommand(command=n, description=S["i18n"].t(code, f"cmd-{n}-desc")) for n in names]
        await bot.set_my_commands(cmds, language_code=code)
    await bot.set_my_commands([BotCommand(command=n, description=S["i18n"].t(S["i18n"].default, f"cmd-{n}-desc")) for n in names])


async def main() -> None:
    s = load_settings(need_bot=True)
    setup_logging(s.log_level)
    S["cfg"] = load_chats_config(s.config_path)
    S["i18n"] = I18n(s.locales_dir, S["cfg"]["defaults"]["default_language"])
    S["engine"] = FilterEngine.from_dir(s.rules_dir)
    S["admins"] = set(s.admin_ids)
    S["pool"] = await create_pool(s.database_url)
    await migrate(S["pool"], s.migrations_dir)
    bot = Bot(s.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(AdminOnly())
    dp.callback_query.middleware(AdminOnly())
    dp.include_router(router)
    await set_commands(bot)
    task = asyncio.create_task(notifier(bot))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
