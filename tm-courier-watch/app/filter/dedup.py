"""Хэши для обнаружения дубликатов: точный (по скелету) и нечёткий (simhash)."""
from __future__ import annotations

import hashlib

_MASK = (1 << 64) - 1


def text_hash(skeleton_text: str) -> str:
    return hashlib.sha1(skeleton_text.encode()).hexdigest()


def simhash(skeleton_text: str) -> int:
    """64-бит simhash по 2-граммам слов; возвращает знаковое int64 (под BIGINT)."""
    toks = skeleton_text.split()
    grams = [" ".join(toks[i : i + 2]) for i in range(max(1, len(toks) - 1))] or [""]
    v = [0] * 64
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = sum(1 << i for i in range(64) if v[i] > 0)
    return out - (1 << 64) if out >= (1 << 63) else out


def hamming(a: int, b: int) -> int:
    return ((a ^ b) & _MASK).bit_count()
