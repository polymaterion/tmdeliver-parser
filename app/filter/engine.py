"""Детерминированный фильтр объявлений о поездках в/из Туркменистана. Без ИИ и сети."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .cities import CityHit, CityIndex
from .dates import DateExtractor, primary
from .dedup import simhash, text_hash
from .lexicon import Lexicons, compile_phrase, compile_regex
from .loader import RuleSet, load_ruleset, mtimes
from .normalize import extract_phones, skeleton, strip_speaker

ROLES = ("carrier_offer", "sender_request", "receiver_request")


@dataclass
class Reason:
    code: str
    kind: str  # builtin | rule
    points: int = 0
    match: str = ""
    desc: dict = field(default_factory=dict)
    args: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Analysis:
    score: int = 0
    level: str = "none"  # none | low | notify | high
    category: str = "unclear"
    direction: str = "unknown"
    route: list[str] = field(default_factory=list)
    route_names: dict = field(default_factory=dict)  # id -> {"ru","tk"}
    date_iso: str | None = None
    date_text: str = ""
    reasons: list[Reason] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    votes: dict = field(default_factory=dict)
    gate: bool = False
    excluded: bool = False
    phones: list[str] = field(default_factory=list)
    skeleton: str = ""
    text_hash: str = ""
    simhash: int = 0

    @property
    def route_key(self) -> str:
        return ">".join(self.route)


class _Rule:
    def __init__(self, spec: dict, lex: Lexicons):
        self.id = spec["id"]
        self.group = spec["group"]
        self.score = spec.get("score", 0)
        self.roles = spec.get("roles", {})
        self.desc = spec.get("desc", {})
        self.hard = spec.get("hard", False)
        self.type = spec.get("type", "phrase")
        self.requires = spec.get("requires_groups", [])
        self.forbids = spec.get("forbids_groups", [])
        comp = compile_regex if self.type == "regex" else compile_phrase
        self.rx = [] if self.type == "combo" else [comp(p, lex) for p in spec.get("patterns", [])]


class FilterEngine:
    def __init__(self, rs: RuleSet, base_dir: str | Path | None = None):
        self.rs = rs
        self.base_dir = base_dir
        self.lex = Lexicons(rs.lexicons)
        self.rules = [_Rule(r, self.lex) for r in rs.rules]
        self.cities = CityIndex(rs.cities)
        self.dates = DateExtractor(rs.patterns, self.lex)
        self.sc = rs.scoring
        self._mt = dict(rs.mtimes)

    @classmethod
    def from_dir(cls, path: str | Path) -> "FilterEngine":
        return cls(load_ruleset(path), path)

    def changed(self) -> bool:
        return bool(self.base_dir) and mtimes(self.base_dir) != self._mt

    @property
    def thresholds(self) -> dict:
        return self.sc["thresholds"]

    # ------------------------------------------------------------------
    def analyze(self, text: str, now: datetime | None = None) -> Analysis:
        now = now or datetime.now(timezone.utc)
        sc, w = self.sc, self.sc["weights"]
        raw = strip_speaker(text or "")
        res = Analysis()
        if len(raw.strip()) < sc.get("min_chars", 6):
            return res
        q_marks = raw.count("?") + raw.count("？")
        no_phone, phones = extract_phones(raw)
        res.phones = phones
        sk = skeleton(no_phone)
        res.skeleton, res.text_hash, res.simhash = sk, text_hash(sk), simhash(sk)
        tokens = sk.split()

        # --- правила
        fired: list[tuple[_Rule, str]] = []
        for r in self.rules:
            for rx in r.rx:
                m = rx.search(sk)
                if m:
                    fired.append((r, m.group(0)))
                    break
        groups = {r.group for r, _ in fired}
        votes = {k: 0 for k in ROLES}
        for r, _ in fired:
            for k, v in r.roles.items():
                votes[k] = votes.get(k, 0) + v
        # --- география
        hits = self.cities.find(tokens)
        strong_tm = any(h.country == "TM" and not h.weak for h in hits)
        phone_tm = any(p.startswith("993") for p in phones)
        weak_tm = any(h.country == "TM" and h.weak for h in hits) or phone_tm
        intent = bool(groups & {"intent_offer", "intent_request", "travel"})
        res.gate = strong_tm or (weak_tm and intent)
        chain = self._chain(hits, strong_tm, res.gate)
        res.route = [h.id for h in chain]
        res.route_names = {h.id: {"ru": self.cities.cities[h.id]["ru"], "tk": self.cities.cities[h.id].get("tk", self.cities.cities[h.id]["ru"])} for h in chain}
        res.direction = self._direction(chain)

        if res.gate and len(chain) >= 2:
            groups.add("route")
        for r in self.rules:
            if r.type == "combo" and all(g in groups for g in r.requires) and not any(g in groups for g in r.forbids):
                fired.append((r, ""))
                for k, v in r.roles.items():
                    votes[k] = votes.get(k, 0) + v
        if any(r.hard for r, _ in fired):
            res.excluded = True
            res.reasons = [Reason(r.id, "rule", 0, m, r.desc) for r, m in fired if r.hard]
            return res

        # --- даты
        dhits = self.dates.extract(sk, now)
        pd = primary(dhits, now)
        if pd:
            res.date_iso, res.date_text = pd.iso, pd.raw

        # --- счёт
        reasons: list[Reason] = []
        total = 0

        def add(code, pts, **args):
            nonlocal total
            total += pts
            reasons.append(Reason(code, "builtin", pts, args=args))

        if strong_tm:
            names = ", ".join(sorted({h.id for h in hits if h.country == "TM" and not h.weak}))
            add("geo_strong", w["geo_strong"], ids=names)
        elif res.gate:
            add("geo_weak", w["geo_weak"])
        if res.gate and len(chain) >= 2 and any(h.country == "TM" for h in chain):
            add("route", w["route"], count=len(chain))
        if pd:
            key = {"exact": "date_exact", "day_only": "date_day_only"}.get(pd.kind, "date_relative")
            add(key, w[key], date=pd.raw)
            if pd.iso and pd.kind != "relative" and datetime.fromisoformat(pd.iso).date() < now.date() - timedelta(days=2):
                add("stale_date", w["stale_date"], date=pd.iso)
        gsum: dict[str, int] = {}
        for r, m in fired:
            if r.group in ("combo",) or r.score == 0:
                if r.group == "combo":
                    reasons.append(Reason(r.id, "rule", 0, m, r.desc))
                    res.rules.append(r.id)
                elif r.roles:
                    reasons.append(Reason(r.id, "rule", 0, m, r.desc))
                    res.rules.append(r.id)
                continue
            gsum[r.group] = gsum.get(r.group, 0) + r.score
        # начисление с лимитами групп
        caps = sc["group_caps"]
        intent_total = 0
        for r, m in fired:
            if r.score == 0:
                continue
            g = r.group
            cur = gsum[g]
            cap = caps.get(g, 100)
            applied = max(cap, cur) if cap < 0 else min(cur, cap)
            # доля правила в группе
            share = round(r.score * applied / cur) if cur else 0
            if g.startswith("intent_"):
                intent_total += share
                continue_pts = share
            else:
                continue_pts = share
            reasons.append(Reason(r.id, "rule", continue_pts, m, r.desc))
            res.rules.append(r.id)
            if not g.startswith("intent_"):
                total += continue_pts
        # intent с общим лимитом
        intent_cap = sc.get("intent_total_cap", 30)
        if intent_total:
            total += min(intent_total, intent_cap)
        if len(raw) > sc.get("too_long_chars", 800):
            add("too_long", w["too_long"])
        if phones:
            reasons.append(Reason("phone", "builtin", 0))
        if q_marks and res.gate and (groups & {"travel", "intent_request"}):
            votes["sender_request"] += w["question_mark_vote"]
            reasons.append(Reason("question", "builtin", 0))

        # --- роль / категория
        res.votes = votes
        rmin = sc.get("role_min", 15)
        best = max(sc.get("role_priority", list(ROLES)), key=lambda k: (votes.get(k, 0), -sc["role_priority"].index(k)))
        if votes.get(best, 0) >= rmin:
            res.category = best
        elif "travel" in groups or ("route" in groups and pd):
            res.category = "traveler_announce"
        else:
            res.category = "unclear"

        res.reasons = reasons
        if not res.gate:
            res.score, res.level = 0, "none"
            res.reasons = [Reason("no_tm", "builtin")]
            return res
        res.score = max(0, min(100, total))
        th = sc["thresholds"]
        res.level = "high" if res.score >= th["high"] else "notify" if res.score >= th["notify"] else "low" if res.score >= th["store_min"] else "none"
        return res

    # ------------------------------------------------------------------
    @staticmethod
    def _chain(hits: list[CityHit], strong_tm: bool, gate: bool) -> list[CityHit]:
        if not gate:
            return []
        keep: list[CityHit] = []
        for i, h in enumerate(hits):
            if h.weak and strong_tm:
                near = any(abs(o.start - h.start) <= 3 for j, o in enumerate(hits) if j != i)
                if not near:
                    continue
            keep.append(h)
        out: list[CityHit] = []
        for h in keep:
            if not out or out[-1].id != h.id:
                out.append(h)
        return out

    @staticmethod
    def _direction(chain: list[CityHit]) -> str:
        if not chain:
            return "unknown"
        tm = [h for h in chain if h.country == "TM"]
        non = [h for h in chain if h.country != "TM"]
        if not tm:
            return "unknown"
        if non:
            return "from_tm" if chain[0].country == "TM" else "to_tm"
        if len(chain) >= 2 and len({h.id for h in tm if h.id != "tm"}) >= 2:
            return "within_tm"
        h = tm[0]
        return "from_tm" if h.hint == "from" else "to_tm" if h.hint == "to" else "unknown"


def fingerprint(analysis: Analysis, salt: str, sender_key: str | None = None) -> str | None:
    """Ключ «один и тот же человек/поездка»: телефоны+маршрут+дата (или отправитель)."""
    ident = ",".join(sorted(analysis.phones)) or (sender_key or "")
    if not ident or not (analysis.route or analysis.date_iso):
        return None
    base = f"{salt}|{ident}|{analysis.route_key}|{analysis.date_iso or ''}"
    return hashlib.sha256(base.encode()).hexdigest()
