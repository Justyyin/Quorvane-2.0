"""The log book: what the bot writes to the log channels, kept for the dashboard.

It is a separate SQLite file, data/logbook.db, so the settings database stays small. Entries are buffered and written in batches,
a log entry never makes a message wait. Old entries are removed after the number of days the server chose.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

MAX_TEXT = 2000
MAX_FIELDS = 12
MAX_PER_GUILD = 20000
BATCH = 50


def from_embed(embed: Any) -> dict:
    """The parts of a log embed that the dashboard shows."""
    author = getattr(getattr(embed, "author", None), "name", None) or ""
    uid = None
    if author.endswith(")") and "(" in author:
        name, _, tail = author.rpartition(" (")
        if tail[:-1].isdigit():
            author, uid = name, int(tail[:-1])
    fields = [[str(f.name)[:80], str(f.value)[:400]] for f in getattr(embed, "fields", [])[:MAX_FIELDS]]
    return {"title": str(getattr(embed, "title", None) or "")[:200], "text": str(getattr(embed, "description", None) or "")[:MAX_TEXT], "user": author[:80], "uid": uid, "fields": fields}


class LogBook:
    """Stores and reads the log entries of all servers."""

    def __init__(self, directory: Any) -> None:
        """Open the file and create the table."""
        self.path = Path(directory) / "logbook.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, gid INTEGER NOT NULL, ts INTEGER NOT NULL, category TEXT NOT NULL,"
            " title TEXT NOT NULL, body TEXT NOT NULL, user TEXT NOT NULL, uid INTEGER, fields TEXT NOT NULL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS events_guild ON events (gid, id)")
        self.db.commit()
        self.pending: list[tuple] = []
        self.listeners: dict[int, set] = {}  # server id -> queues of open live views
        self.last_flush = time.monotonic()

    def add(self, gid: int, category: str, title: str, text: str = "", user: str = "", uid: Optional[int] = None, fields: Optional[list] = None, ts: Optional[int] = None) -> None:
        """Queue one entry. It is written with the next batch or after two seconds at the latest."""
        when = int(ts or time.time())
        self.pending.append((int(gid), when, str(category)[:30], title[:200], text[:MAX_TEXT], user[:80], uid, json.dumps(fields or [], ensure_ascii=False)))
        for queue in self.listeners.get(int(gid), ()):
            if not queue.full():
                queue.put_nowait({"id": 0, "ts": when, "category": str(category)[:30], "title": title[:200], "text": text[:MAX_TEXT], "user": user[:80], "uid": str(uid) if uid else None, "fields": fields or []})
        if len(self.pending) >= BATCH or time.monotonic() - self.last_flush > 2:
            self.flush()

    def flush(self) -> None:
        """Write the queued entries."""
        self.last_flush = time.monotonic()
        if not self.pending:
            return
        rows, self.pending = self.pending, []
        try:
            self.db.executemany("INSERT INTO events (gid, ts, category, title, body, user, uid, fields) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
            self.db.commit()
        except sqlite3.Error as exc:
            log.warning("log book could not be written: %s", exc)

    def read(self, gid: int, category: str = "", query: str = "", before: int = 0, after: int = 0, limit: int = 50, since: int = 0, until: int = 0) -> list[dict]:
        """Entries of a server, newest first. after returns only entries newer than an id, for the live view."""
        self.flush()
        sql = "SELECT id, ts, category, title, body, user, uid, fields FROM events WHERE gid = ?"
        args: list[Any] = [int(gid)]
        if category:
            sql += " AND category = ?"
            args.append(category)
        if before:
            sql += " AND id < ?"
            args.append(int(before))
        if after:
            sql += " AND id > ?"
            args.append(int(after))
        if since:
            sql += " AND ts >= ?"
            args.append(int(since))
        if until:
            sql += " AND ts <= ?"
            args.append(int(until))
        if query:
            like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")[:80] + "%"
            sql += " AND (title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' OR user LIKE ? ESCAPE '\\' OR fields LIKE ? ESCAPE '\\')"
            args += [like] * 4
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(max(1, min(5000, int(limit))))
        out = []
        for i, ts, cat, title, body, user, uid, fields in self.db.execute(sql, args):
            out.append({"id": i, "ts": ts, "category": cat, "title": title, "text": body, "user": user, "uid": str(uid) if uid else None, "fields": json.loads(fields)})
        return out

    def per_day(self, gid: int, days: list[str]) -> dict[str, list[int]]:
        """How many entries each category has on each of the given days (YYYY-MM-DD, UTC)."""
        self.flush()
        out: dict[str, list[int]] = {}
        if not days:
            return out
        index = {d: i for i, d in enumerate(days)}
        rows = self.db.execute("SELECT category, strftime('%Y-%m-%d', ts, 'unixepoch') AS day, COUNT(*) FROM events WHERE gid = ? AND day >= ? GROUP BY category, day", (int(gid), days[0]))
        for cat, day, n in rows:
            if day in index:
                out.setdefault(cat, [0] * len(days))[index[day]] = n
        return out

    def prune(self, gid: int, keep_days: int) -> int:
        """Remove entries that are too old and keep at most MAX_PER_GUILD of a server. Returns how many were removed."""
        self.flush()
        cur = self.db.execute("DELETE FROM events WHERE gid = ? AND ts < ?", (int(gid), int(time.time()) - max(1, keep_days) * 86400))
        removed = cur.rowcount
        row = self.db.execute("SELECT id FROM events WHERE gid = ? ORDER BY id DESC LIMIT 1 OFFSET ?", (int(gid), MAX_PER_GUILD)).fetchone()
        if row:
            removed += self.db.execute("DELETE FROM events WHERE gid = ? AND id <= ?", (int(gid), row[0])).rowcount
        self.db.commit()
        return removed

    def forget_user(self, gid: int, uid: int) -> int:
        """Delete every entry about one member, for the privacy commands."""
        self.flush()
        n = self.db.execute("DELETE FROM events WHERE gid = ? AND (uid = ? OR body LIKE ? OR fields LIKE ?)", (int(gid), int(uid), f"%{int(uid)}%", f"%{int(uid)}%")).rowcount
        self.db.commit()
        return n

    def drop_guild(self, gid: int) -> None:
        """Delete everything of a server."""
        self.pending = [r for r in self.pending if r[0] != int(gid)]
        self.db.execute("DELETE FROM events WHERE gid = ?", (int(gid),))
        self.db.commit()

    def close(self) -> None:
        """Write what is queued and close the file."""
        self.flush()
        self.db.close()
