import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS trips(
                id TEXT PRIMARY KEY, origin TEXT NOT NULL, destination TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
                kind TEXT NOT NULL, detail TEXT NOT NULL
            );
        """)
        # A restart never resumes a previously running mission.
        self.db.execute(
            "UPDATE trips SET status='INTERRUPTED', updated_at=? WHERE status='ACTIVE'",
            (utc_now(),),
        )
        self.db.commit()

    def trip(self, trip):
        now = utc_now()
        self.db.execute(
            """INSERT INTO trips VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at""",
            (trip["id"], trip["origin"], trip["destination"], trip["status"], now, now),
        )
        self.db.commit()

    def event(self, kind, detail):
        self.db.execute(
            "INSERT INTO events(at,kind,detail) VALUES(?,?,?)",
            (utc_now(), kind, json.dumps(detail)),
        )
        self.db.commit()

    def trips(self):
        return [
            dict(r)
            for r in self.db.execute("SELECT * FROM trips ORDER BY created_at DESC LIMIT 100")
        ]

    def events(self):
        return [
            {**dict(r), "detail": json.loads(r["detail"])}
            for r in self.db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100")
        ]

    def close(self):
        self.db.close()
