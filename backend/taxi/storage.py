import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from .migrations import migrate


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str, recover=True):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).touch(mode=0o600, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        try:
            migrate(self.db)
        except BaseException:
            self.db.close()
            raise
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
