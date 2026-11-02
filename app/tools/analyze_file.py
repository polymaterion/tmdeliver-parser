"""python -m app.tools.analyze_file corpus.txt [--rules rules] — прогнать файл (сообщения через пустую строку)."""
import argparse
import re
from datetime import datetime, timezone

from app.filter.engine import FilterEngine

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--rules", default="rules")
    ap.add_argument("--now", default="2025-10-01")
    a = ap.parse_args()
    eng = FilterEngine.from_dir(a.rules)
    now = datetime.fromisoformat(a.now).replace(tzinfo=timezone.utc)
    text = open(a.file, encoding="utf-8-sig").read()
    for msg in re.split(r"\n\s*\n+", text):
        msg = msg.strip()
        if not msg:
            continue
        r = eng.analyze(msg, now)
        print(f"{r.score:3d} {r.level:6s} {r.category:18s} {r.direction:8s} {'>'.join(r.route)[:40]:40s} {r.date_iso or '-':10s} | {msg[:90]!r}")
