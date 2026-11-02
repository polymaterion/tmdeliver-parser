"""Извлечение дат: числовые, с названием месяца (рус/тукм), «шу айын 22», относительные."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .lexicon import Lexicons, compile_phrase
from .normalize import skeleton


@dataclass
class DateHit:
    raw: str
    kind: str  # exact | day_only | relative
    day: int | None = None
    month: int | None = None
    year: int | None = None
    day2: int | None = None
    rel: str | None = None
    iso: str | None = None


class DateExtractor:
    def __init__(self, patterns: dict, lex: Lexicons):
        self.months: list[tuple[str, int]] = []
        for num, stems in patterns["months"].items():
            for s in stems:
                st = skeleton(s.strip("*"))
                if st:
                    self.months.append((st, int(num)))
        self.months.sort(key=lambda x: -len(x[0]))
        alt = "|".join(re.escape(s) for s, _ in self.months)
        month_rx = rf"(?P<month>(?:{alt})[a-z]{{0,4}})(?![a-z])"
        self.patterns = [
            (p["name"], p["kind"], re.compile(p["regex"].replace("{MONTH}", month_rx)))
            for p in patterns["date_patterns"]
        ]
        self.relative = {
            k: [compile_phrase(ph, lex) for ph in v] for k, v in patterns["relative"].items()
        }

    def _month_num(self, txt: str) -> int | None:
        for stem, num in self.months:
            if txt.startswith(stem):
                return num
        return None

    def extract(self, sk: str, now: datetime) -> list[DateHit]:
        hits: list[DateHit] = []
        work = sk
        for _, kind, rx in self.patterns:
            for m in list(rx.finditer(work)):
                g = m.groupdict()
                day = int(g["day"])
                mon = g.get("month")
                month = int(mon) if mon and mon.isdigit() else self._month_num(mon) if mon else None
                year = None
                if g.get("year"):
                    y = int(g["year"])
                    y = y + 2000 if y < 100 else y
                    year = y if 2024 <= y <= 2035 else None
                if not (1 <= day <= 31) or (mon and month is None) or (month is not None and not 1 <= month <= 12):
                    continue
                d2 = int(g["day2"]) if g.get("day2") else None
                h = DateHit(m.group(0).strip(), kind, day, month, year, d2)
                h.iso = self._resolve(h, now)
                if h.iso is None:
                    continue
                hits.append(h)
                work = work[: m.start()] + " " * (m.end() - m.start()) + work[m.end():]
        if not hits:
            for rel, rxs in self.relative.items():
                for rx in rxs:
                    m = rx.search(sk)
                    if m:
                        h = DateHit(m.group(0), "relative", rel=rel)
                        if rel == "today":
                            h.iso = now.date().isoformat()
                        elif rel == "tomorrow":
                            h.iso = (now.date() + timedelta(days=1)).isoformat()
                        hits.append(h)
                        break
                if hits:
                    break
        return hits

    @staticmethod
    def _resolve(h: DateHit, now: datetime) -> str | None:
        today = now.date()
        year = h.year or today.year
        month = h.month or today.month
        try:
            d = date(year, month, h.day)
        except ValueError:
            return None
        if h.year is None:
            if h.month and d < today - timedelta(days=60):
                d = date(year + 1, month, h.day)
            elif not h.month and d < today:
                m2 = month + 1
                try:
                    d = date(year + (m2 > 12), (m2 - 1) % 12 + 1, h.day)
                except ValueError:
                    return None
        return d.isoformat()


def primary(hits: list[DateHit], now: datetime) -> DateHit | None:
    dated = [h for h in hits if h.iso]
    if not dated:
        return hits[0] if hits else None
    today = now.date().isoformat()
    future = sorted(h.iso for h in dated if h.iso >= (now.date() - timedelta(days=1)).isoformat())
    target = future[0] if future else min(h.iso for h in dated)
    return next(h for h in dated if h.iso == target)
