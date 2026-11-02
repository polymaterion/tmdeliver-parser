"""Нормализация текста до единого «скелета» (латиница, фонетическое сворачивание).

Русский, туркменский (латиница/кириллица), транслит и опечатки приводятся к одной форме,
поэтому словари можно писать в любом из написаний: загрузчик пропускает их через ту же функцию.
"""
from __future__ import annotations

import re
import unicodedata

_MAP = {
    # туркменская латиница
    "ş": "sh", "ç": "ch", "ž": "zh", "ý": "y", "ä": "a", "ö": "o", "ü": "u", "ň": "n", "ń": "n",
    "ı": "i", "ğ": "g", "ə": "a",
    # туркменская/узбекская/таджикская кириллица
    "ә": "a", "ө": "o", "ү": "u", "ң": "n", "җ": "zh", "ҥ": "n", "ў": "u", "ғ": "g", "қ": "k",
    "ҳ": "h", "ӣ": "i", "ӯ": "u",
    # русская кириллица
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ь": "", "ы": "y", "э": "e", "ю": "yu", "я": "ya",
    # апострофы внутри слов
    "'": "", "’": "", "ʼ": "", "`": "", "´": "",
}
_DIGRAPHS = (("sh", "s"), ("ch", "c"), ("zh", "j"), ("kh", "h"), ("ts", "c"))
_SINGLE = str.maketrans({"y": "i", "w": "v", "q": "k", "x": "h", "o": "a"})
_RUN = re.compile(r"([a-z])\1+")
_NONALNUM = re.compile(r"[^a-z0-9./\- ]")
_SEP = re.compile(r"(?<!\d)[./\-]|[./\-](?!\d)")
_DL = re.compile(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)")
_SPACES = re.compile(r"\s+")
_SPEAKER = re.compile(r"^[^\n:]{1,30}:[ \t]*\n")
_PHONE = re.compile(r"(?<![\w])\+?\d[\d\s\-()]{7,}\d(?!\w)")


def _prep(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower()
    t = "".join(_MAP.get(ch, ch) for ch in t)
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def skeleton(text: str) -> str:
    """Текст -> «скелет»: латиница a-z, цифры, разделитель дат только между цифрами."""
    t = _prep(text)
    t = _NONALNUM.sub(" ", t)
    t = _RUN.sub(r"\1", t)
    for a, b in _DIGRAPHS:
        t = t.replace(a, b)
    t = t.translate(_SINGLE)
    t = _RUN.sub(r"\1", t)
    t = _SEP.sub(" ", t)
    t = _DL.sub(" ", t)
    return _SPACES.sub(" ", t).strip()


def strip_speaker(text: str) -> str:
    """Убирает строку вида «Имя Фамилия:» в начале (артефакт пересылки/экспорта)."""
    return _SPEAKER.sub("", text, count=1)


def extract_phones(text: str) -> tuple[str, list[str]]:
    """Вырезает телефоны (>=9 цифр) и возвращает (текст_без_телефонов, [цифры])."""
    phones: list[str] = []

    def repl(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 9:
            phones.append(digits)
            return " "
        return m.group(0)

    return _PHONE.sub(repl, text), phones
