"""Лексиконы и компиляция шаблонов правил в регулярные выражения над «скелетом».

Синтаксис шаблона (phrase):
  слово          точное слово (любое написание — проходит через skeleton)
  корень*        префикс;  *корень — суффикс;  *корень* — подстрока
  a|b|c          альтернативы для одного слова
  {NAME}         любое слово из лексикона NAME;  {NAME:strict} — с отсечением deny_suffixes
  ~              между словами: от 0 до 3 произвольных слов
"""
from __future__ import annotations

import re
from typing import Any

from .normalize import skeleton

_PLACE = re.compile(r"\{([A-Z0-9_]+)(?::(strict))?\}")
_B = r"(?<![a-z0-9])"
_E = r"(?![a-z0-9])"
GAP = r"(?:\s+\w+){0,3}\s+"
GAP_LONG = r"(?:\s+\w+){0,6}\s+"


def entry_to_regex(entry: str, deny: tuple[str, ...] = ()) -> str:
    parts = []
    for tok in entry.split():
        lead, trail = tok.startswith("*"), tok.endswith("*")
        sk = skeleton(tok.strip("*"))
        if not sk:
            continue
        piece = r"\s+".join(re.escape(w) for w in sk.split())
        if lead:
            piece = r"\w*" + piece
        if trail:
            piece += r"\w*"
        piece += "".join(f"(?<!{d})" for d in deny)
        parts.append(piece)
    return r"\s+".join(parts)


class Lexicons:
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self._cache: dict[tuple[str, bool], str] = {}

    def words(self, name: str, _seen: tuple = ()) -> list[str]:
        if name not in self.raw:
            raise KeyError(f"Лексикон {name!r} не найден")
        spec = self.raw[name]
        if isinstance(spec, list):
            return list(spec)
        out = list(spec.get("words", []))
        for inc in spec.get("include", []):
            if inc not in _seen:
                out += self.words(inc, _seen + (name,))
        return out

    def deny(self, name: str) -> tuple[str, ...]:
        spec = self.raw.get(name)
        if isinstance(spec, dict):
            return tuple(skeleton(d) for d in spec.get("deny_suffixes", []))
        return ()

    def alt(self, name: str, strict: bool = False) -> str:
        key = (name, strict)
        if key not in self._cache:
            deny = self.deny(name) if strict else ()
            alts = {entry_to_regex(w, deny) for w in self.words(name)}
            alts.discard("")
            self._cache[key] = "(?:" + "|".join(sorted(alts, key=len, reverse=True)) + ")"
        return self._cache[key]

    def expand(self, s: str) -> str:
        return _PLACE.sub(lambda m: self.alt(m.group(1), bool(m.group(2))), s)


def compile_phrase(pattern: str, lex: Lexicons) -> re.Pattern:
    out: list[str] = []
    gap: str | bool = False
    for tok in pattern.split():
        if tok in ("~", "~~"):
            gap = tok
            continue
        if _PLACE.fullmatch(tok):
            piece = lex.expand(tok)
        else:
            alts = [entry_to_regex(a) for a in tok.split("|")]
            piece = "(?:" + "|".join(a for a in alts if a) + ")"
        if out:
            out.append((GAP_LONG if gap == "~~" else GAP) if gap else r"\s+")
        gap = False
        out.append(piece)
    return re.compile(_B + "".join(out) + _E)


def compile_regex(pattern: str, lex: Lexicons) -> re.Pattern:
    return re.compile(_B + lex.expand(pattern) + _E)
