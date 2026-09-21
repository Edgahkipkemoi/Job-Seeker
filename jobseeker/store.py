"""SQLite memory of everything already emailed, so you never get the same
vacancy twice."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    fingerprint TEXT PRIMARY KEY,
    title       TEXT,
    company     TEXT,
    url         TEXT,
    source      TEXT,
    category    TEXT,
    score       INTEGER,
    first_seen  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_seen_first_seen ON seen(first_seen);
"""


class Store:
    def __init__(self, path: str | Path, remember_days: int = 45):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.remember_days = remember_days
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def filter_new(self, jobs: list[Job]) -> list[Job]:
        known = {row[0] for row in self.conn.execute("SELECT fingerprint FROM seen")}
        fresh, batch_seen = [], set()
        for job in jobs:
            fp = job.fingerprint
            if fp in known or fp in batch_seen:
                continue
            batch_seen.add(fp)
            fresh.append(job)
        return fresh

    def mark_sent(self, jobs: list[Job]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen VALUES (?,?,?,?,?,?,?,?)",
            [
                (j.fingerprint, j.title, j.company, j.url, j.source, j.category, j.score, now)
                for j in jobs
            ],
        )
        self.conn.commit()

    def prune(self) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.remember_days)).isoformat()
        cur = self.conn.execute("DELETE FROM seen WHERE first_seen < ?", (cutoff,))
        self.conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self.conn.close()
