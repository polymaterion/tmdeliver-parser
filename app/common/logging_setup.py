"""Логи без секретов и персональных данных: токены и длинные числа (телефоны) маскируются."""
import logging
import re

_PATTERNS = [
    (re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"), "<bot-token>"),
    (re.compile(r"\+?\d[\d\s\-()]{8,}\d"), "<number>"),
]


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for rx, rep in _PATTERNS:
            msg = rx.sub(rep, msg)
        record.msg, record.args = msg, ()
        return True


def setup_logging(level: str = "INFO") -> None:
    h = logging.StreamHandler()
    h.addFilter(RedactFilter())
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
