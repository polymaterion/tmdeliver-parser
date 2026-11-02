"""Индекс городов/стран: точное совпадение с суффиксами падежей + нечёткое (опечатки)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .normalize import skeleton

STRICT_SUFFIX = {"a", "e", "u", "i", "da", "de", "dan", "den", "na", "ne", "ga", "ge", "ia", "ya"}
FROM_SUFFIX = {"den", "dan"}
TO_SUFFIX = {"a", "e", "na", "ne", "ga", "ge", "u", "ia", "ya"}
FROM_PREP = {"iz", "is", "at", "s"}
TO_PREP = {"v", "na", "da", "k", "va"}
_VOICE = {"p": "b", "b": "p", "t": "d", "d": "t", "k": "g", "g": "k", "c": "j", "j": "c"}


@dataclass(frozen=True)
class CityHit:
    id: str
    country: str
    start: int
    end: int
    weak: bool
    fuzzy: bool
    hint: str | None  # 'from' | 'to' | None


@dataclass(frozen=True)
class _Alias:
    tokens: tuple[str, ...]
    city_id: str
    country: str
    weak: bool
    strict: bool


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class CityIndex:
    def __init__(self, cities: list[dict]):
        self.cities = {c["id"]: c for c in cities}
        self._by_char: dict[str, list[_Alias]] = {}
        self._fuzzy: list[_Alias] = []
        for c in cities:
            for weak, key in ((False, "aliases"), (True, "weak")):
                for raw in c.get(key, []):
                    sk = skeleton(raw)
                    if not sk:
                        continue
                    toks = tuple(sk.split())
                    variants = {toks}
                    last = toks[-1]
                    if len(last) > 3 and last[-1] in _VOICE:
                        variants.add(toks[:-1] + (last[:-1] + _VOICE[last[-1]],))
                    for v in variants:
                        al = _Alias(v, c["id"], c["country"], weak, len(v[-1]) <= 4)
                        self._by_char.setdefault(v[0][0], []).append(al)
                        if not weak and len(v) == 1 and len(v[0]) >= 6 and v[0].isalpha():
                            self._fuzzy.append(al)
        self.find_fuzzy = lru_cache(maxsize=4096)(self._find_fuzzy)

    def _find_fuzzy(self, tok: str):
        if len(tok) < 6 or not tok.isalpha():
            return None
        best = None
        for al in self._fuzzy:
            a = al.tokens[0]
            if abs(len(tok) - len(a)) > 4:
                continue
            d = lev(tok, a)
            if len(tok) > len(a):
                d = min(d, lev(tok[: len(a)], a))
            if d <= (1 if len(a) < 10 else 2) and (best is None or d < best[0]):
                best = (d, al)
        return best[1] if best else None

    def find(self, tokens: list[str]) -> list[CityHit]:
        res: list[CityHit] = []
        i, n = 0, len(tokens)
        while i < n:
            best = None
            for al in self._by_char.get(tokens[i][0], ()):
                k = len(al.tokens)
                if i + k > n or tuple(tokens[i : i + k - 1]) != al.tokens[:-1]:
                    continue
                last, a = tokens[i + k - 1], al.tokens[-1]
                if last == a:
                    suf = ""
                elif last.startswith(a):
                    suf = last[len(a):]
                    if len(suf) > 4 or not suf.isalpha():
                        continue
                    if al.strict and suf not in STRICT_SUFFIX:
                        continue
                else:
                    continue
                score = (k, len(a), not al.weak)
                if best is None or score > best[0]:
                    best = (score, al, suf, k)
            fuzzy = False
            if best is None:
                al = self.find_fuzzy(tokens[i])
                if al:
                    best, fuzzy = ((1, 0, False), al, "", 1), True
            if best is None:
                i += 1
                continue
            _, al, suf, k = best
            hint = None
            if suf in FROM_SUFFIX:
                hint = "from"
            elif suf in TO_SUFFIX:
                hint = "to"
            elif i > 0:
                p = tokens[i - 1]
                hint = "from" if p in FROM_PREP else "to" if p in TO_PREP else None
            weak = al.weak or (fuzzy and al.country == "TM")
            res.append(CityHit(al.city_id, al.country, i, i + k, weak, fuzzy, hint))
            i += k
        return res
