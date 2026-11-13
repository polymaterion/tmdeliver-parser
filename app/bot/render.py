"""Формирование текста и клавиатур. Все строки — через I18n (locales/*.ftl)."""
from __future__ import annotations

import html
from datetime import date

from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as Kb

from app.common.i18n import I18n

CATEGORIES = ["carrier_offer", "sender_request", "receiver_request", "traveler_announce", "unclear"]
VERDICTS = {"u": "useful", "i": "irrelevant"}


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
    """Ряд 1: [Полезно] [Не релевантно]; ряд 2: [Профиль] [Сообщение]."""
    t = lambda k, **kw: i18n.t(lang, k, **kw)  # noqa: E731

    def fb(code: str, key: str) -> Btn:
        label = t(key)
        if verdict == VERDICTS[code]:
            label = t("mark-selected", label=label)
        return Btn(text=label, callback_data=f"fb:{m['id']}:{code}")

    rows = [[fb("u", "btn-useful"), fb("i", "btn-irrelevant")]]
    links = []
    if m.get("profile_url"):
        links.append(Btn(text=t("btn-profile"), url=m["profile_url"]))
    if m.get("link"):
        links.append(Btn(text=t("btn-message"), url=m["link"]))
    if links:
        rows.append(links)
    return Kb(inline_keyboard=rows)


def mark_verdict(markup: Kb | None, i18n: I18n, lang: str, verdict: str) -> Kb | None:
    """Отмечает выбранную оценку на клавиатуре, которая УЖЕ стоит под сообщением.
    Остальные кнопки (ссылки «Профиль»/«Сообщение») остаются как есть: заново их из БД не строим,
    иначе можно вернуть кнопку, которую Telegram уже отклонил при отправке."""
    if markup is None:
        return None
    labels = {"u": i18n.t(lang, "btn-useful"), "i": i18n.t(lang, "btn-irrelevant")}
    rows = []
    for row in markup.inline_keyboard:
        new = []
        for b in row:
            cd = b.callback_data or ""
            code = cd.split(":")[-1] if cd.startswith("fb:") else None
            if code in VERDICTS:
                label = labels[code]
                if VERDICTS[code] == verdict:
                    label = i18n.t(lang, "mark-selected", label=label)
                new.append(Btn(text=label, callback_data=cd))
            else:
                new.append(b)
        rows.append(new)
    return Kb(inline_keyboard=rows)
