"""python -m app.tools.export_feedback out.csv — выгрузка находок+оценок из БД для разбора и улучшения словарей."""
import asyncio
import csv
import sys

from app.common.config import load_settings
from app.common.db import create_pool


async def main(path: str) -> None:
    s = load_settings()
    pool = await create_pool(s.database_url)
    rows = await pool.fetch(
        """SELECT m.id, m.created_at, m.chat_title, m.link, m.score, m.category, m.direction, array_to_string(m.route,'>') route,
                  m.travel_date, array_to_string(m.rules,',') rules, m.status, m.contact_status,
                  (SELECT string_agg(f.verdict, ',') FROM feedback f WHERE f.match_id=m.id) verdict, m.text
           FROM matches m ORDER BY m.id""")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if rows:
            w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(list(r.values()))
    print(f"Выгружено строк: {len(rows)} -> {path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "matches.csv"))
