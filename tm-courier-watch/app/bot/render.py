"""Формирование текста и клавиатур. Все строки — через I18n (locales/*.ftl)."""
from __future__ import annotations

import html
from datetime import date

from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Kb

from app.common.i18n import I18n

CATEGORIES = ["carrier_offer", "sender_request", "receiver_request", "traveler_announce", "unclear"]
CONTACT = ["none", "contacted", "replied", "agreed", "done", "no_answer", "declined"]
VERDICTS = {"u": "useful", "i": "irrelevant", "d": "duplicate"}


def esc(v) -> str:
    return html.escape(str(v), quote=False)


def route_text(m: dict, lang: str) -> str:
    names = m.get("route_names") or {}
    out = []
    for rid in m.get("route") or []:
        n = names.get(rid) or {}
        out.append(n.get(lang) or n.get("ru") or rid)
    return " → ".join(out)


def reason_line(i18n: I18n, lang: str, r: dict) -> str:
    if r["kind"] == "builtin":
        args = {k: esc(v) for k, v in (r.get("args") or {}).items()}
        txt = i18n.t(lang, "reason-" + r["code"], **args)
    else:
        d = r.get("desc") or {}
        txt = esc(d.get(lang) or d.get("ru") or r["code"])
    pts = f" ({r['points']:+d})" if r.get("points") else ""
    return f"• {txt}{pts}"


def fmt_date(m: dict) -> str:
    d = m.get("travel_date")
    if isinstance(d, date):
        return d.strftime("%d.%m.%Y")
    return m.get("date_text") or ""


def render_match(i18n: I18n, lang: str, m: dict) -> str:
    t = lambda k, **kw: i18n.t(lang, k, **kw)  # noqa: E731
    lines = [t("notify-header", score=m["score"]), t("notify-category", category=t("cat-" + m["category"]))]
    route = route_text(m, lang)
    if route:
        lines.append(t("notify-route", route=esc(route), direction=t("dir-" + m["direction"])))
    d = fmt_date(m)
    if d:
        lines.append(t("notify-date", date=esc(d)))
    if m.get("chat_title"):
        lines.append(t("notify-chat", title=esc(m["chat_title"])))
    reasons = [r for r in (m.get("reasons") or []) if r.get("kind") == "rule" or r.get("code") in ("geo_strong", "geo_weak", "route", "date_exact", "date_day_only", "date_relative", "stale_date")]
    if reasons:
        lines.append(t("notify-reasons"))
        lines += [reason_line(i18n, lang, r) for r in reasons[:8]]
    text = m["text"] if len(m["text"]) <= 700 else m["text"][:700] + "…"
    lines += [t("notify-text"), f"<blockquote>{esc(text)}</blockquote>"]
    if not m.get("link"):
        lines.append(t("notify-no-link"))
    return "\n".join(lines)


def match_keyboard(i18n: I18n, lang: str, m: dict, verdict: str | None = None) -> Kb:
    t = lambda k, **kw: i18n.t(lang, k, **kw)  # noqa: E731
    rows = []
    if m.get("link"):
        rows.append([Btn(text=t("btn-open"), url=m["link"])])

    def fb(code: str, key: str) -> Btn:
        label = t(key)
        if verdict == VERDICTS[code]:
            label = t("mark-selected", label=label)
        return Btn(text=label, callback_data=f"fb:{m['id']}:{code}")

    rows.append([fb("u", "btn-useful"), fb("i", "btn-irrelevant"), fb("d", "btn-duplicate")])
    rows.append([Btn(text=t("btn-contact", status=t("contact-" + m["contact_status"])), callback_data=f"cs:{m['id']}")])
    return Kb(inline_keyboard=rows)


def contact_keyboard(i18n: I18n, lang: str, match_id: int, current: str) -> Kb:
    rows = []
    for st in CONTACT:
        label = i18n.t(lang, "contact-" + st)
        if st == current:
            label = i18n.t(lang, "mark-selected", label=label)
        rows.append([Btn(text=label, callback_data=f"cs:{match_id}:{st}")])
    rows.append([Btn(text=i18n.t(lang, "btn-back"), callback_data=f"cs:{match_id}:back")])
    return Kb(inline_keyboard=rows)
