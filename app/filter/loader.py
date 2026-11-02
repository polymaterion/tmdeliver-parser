"""Загрузка словарей из каталога rules/ (+ rules/custom/) без изменения кода."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _files(base: Path, name: str) -> list[Path]:
    found: list[Path] = []
    for d in (base, base / "custom"):
        if not d.is_dir():
            continue
        main = d / f"{name}.json"
        if main.exists():
            found.append(main)
        found += sorted(d.glob(f"{name}.*.json"))
    return found


def _read(p: Path) -> dict:
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def _deep_update(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_update(a[k], v)
        else:
            a[k] = v
    return a


@dataclass
class RuleSet:
    lexicons: dict[str, Any] = field(default_factory=dict)
    rules: list[dict] = field(default_factory=list)
    cities: list[dict] = field(default_factory=list)
    patterns: dict = field(default_factory=dict)
    scoring: dict = field(default_factory=dict)
    mtimes: dict[str, float] = field(default_factory=dict)


def load_ruleset(base: str | Path) -> RuleSet:
    base = Path(base)
    rs = RuleSet()
    for p in _files(base, "lexicons"):
        for k, v in _read(p).items():
            if k.startswith("_"):
                continue
            cur = rs.lexicons.get(k)
            if cur is None:
                rs.lexicons[k] = v
            else:
                def words(x): return x if isinstance(x, list) else x.get("words", [])
                if isinstance(cur, list):
                    cur.extend(words(v))
                else:
                    cur.setdefault("words", []).extend(words(v))
                    if isinstance(v, dict):
                        cur.setdefault("include", []).extend(v.get("include", []))
    by_id: dict[str, dict] = {}
    for p in _files(base, "keywords"):
        for r in _read(p).get("rules", []):
            by_id[r["id"]] = r
    rs.rules = list(by_id.values())
    cities: dict[str, dict] = {}
    for p in _files(base, "cities"):
        for c in _read(p).get("cities", []):
            if c["id"] in cities:
                for key in ("aliases", "weak"):
                    cities[c["id"]].setdefault(key, []).extend(c.get(key, []))
            else:
                c.setdefault("aliases", [])
                c.setdefault("weak", [])
                cities[c["id"]] = c
    rs.cities = list(cities.values())
    for p in _files(base, "patterns"):
        d = _read(p)
        if not rs.patterns:
            rs.patterns = d
        else:
            for k in ("months", "relative"):
                for kk, vv in d.get(k, {}).items():
                    rs.patterns.setdefault(k, {}).setdefault(kk, []).extend(vv)
            rs.patterns.setdefault("date_patterns", []).extend(d.get("date_patterns", []))
    for p in _files(base, "scoring"):
        _deep_update(rs.scoring, _read(p))
    for d in (base, base / "custom"):
        if d.is_dir():
            for p in d.glob("*.json"):
                rs.mtimes[str(p)] = p.stat().st_mtime
    return rs


def mtimes(base: str | Path) -> dict[str, float]:
    base = Path(base)
    out = {}
    for d in (base, base / "custom"):
        if d.is_dir():
            for p in d.glob("*.json"):
                out[str(p)] = p.stat().st_mtime
    return out
