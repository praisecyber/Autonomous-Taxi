import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str, recover=True):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).touch(mode=0o600, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.db.close()
            raise ValueError("Database schema is newer than this application")
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
        # Version 0 is the original six-column trips/events database.
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if "owner_id" not in {r[1] for r in self.db.execute("PRAGMA table_info(trips)")}:
                self.db.execute("ALTER TABLE trips ADD COLUMN owner_id TEXT REFERENCES users(id)")
            self.db.execute("""CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('passenger','operator','admin')),
                enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
                created_at TEXT NOT NULL)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS sessions(
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                expires_at REAL NOT NULL)""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS configuration(
                id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
                payload TEXT NOT NULL)""")
            self.db.execute("CREATE INDEX IF NOT EXISTS trips_owner ON trips(owner_id)")
            self.db.execute("PRAGMA user_version=1")
        # A restart never resumes a previously running mission.
        if recover:
            self.db.execute(
                "UPDATE trips SET status='INTERRUPTED', updated_at=? WHERE status='ACTIVE'",
                (utc_now(),),
            )
        self.db.commit()

    def trip(self, trip):
        now = utc_now()
        self.db.execute(
            """INSERT INTO trips(id,origin,destination,status,created_at,updated_at,owner_id)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at""",
            (
                trip["id"],
                trip["origin"],
                trip["destination"],
                trip["status"],
                now,
                now,
                trip.get("owner_id"),
            ),
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
            for r in self.db.execute(
                "SELECT * FROM trips ORDER BY created_at DESC, id DESC LIMIT 100"
            )
        ]

    def events(self):
        return [
            {**dict(r), "detail": json.loads(r["detail"])}
            for r in self.db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100")
        ]

    def close(self):
        self.db.close()
