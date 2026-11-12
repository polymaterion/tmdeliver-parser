"""Локализация на стандартном формате Fluent (.ftl): locales/<код>.ftl. Новый язык = новый файл."""
from __future__ import annotations

import logging
from pathlib import Path

from fluent.runtime import FluentBundle, FluentResource

log = logging.getLogger(__name__)


class I18n:
    def __init__(self, directory: str, default: str = "ru"):
        self.dir = Path(directory)
        self.default = default
        self.bundles: dict[str, FluentBundle] = {}
        self._mt: dict[str, float] = {}
        self.load()

    def load(self) -> None:
        self.bundles.clear()
        for f in sorted(self.dir.glob("*.ftl")):
            b = FluentBundle([f.stem], use_isolating=False)
            b.add_resource(FluentResource(f.read_text(encoding="utf-8")))
            self.bundles[f.stem] = b
            self._mt[str(f)] = f.stat().st_mtime
        if self.default not in self.bundles:
            raise RuntimeError(f"Нет файла локали по умолчанию: {self.default}.ftl")

    @property
    def languages(self) -> list[str]:
        return list(self.bundles)

    def pick(self, code: str | None) -> str:
        c = (code or "").split("-")[0].lower()
        return c if c in self.bundles else self.default

    def t(self, lang: str, key: str, /, **kw) -> str:
        for code in (lang, self.default):
            b = self.bundles.get(code)
            if b and b.has_message(key):
                msg = b.get_message(key)
                if msg.value is not None:
                    text, errors = b.format_pattern(msg.value, kw)
                    if errors:
                        log.warning("i18n %s/%s: %s", code, key, errors[0])
                    return text
        return key
