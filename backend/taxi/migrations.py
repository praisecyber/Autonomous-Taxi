"""Versioned, transactional SQLite migrations preserving existing identities/history."""

SCHEMA_VERSION = 2
USERS = """(
    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('passenger','operator','admin','diagnostics')),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    created_at TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0,1))
)"""


def migrate(db):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise ValueError("Database schema is newer than this application")
    if version == SCHEMA_VERSION:
        db.execute("PRAGMA foreign_keys=ON")
        return
    # SQLite's documented table-rebuild procedure: disable FK enforcement outside the
    # transaction, preserve IDs, then check all foreign keys before committing.
    db.execute("PRAGMA foreign_keys=OFF")
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS trips(
            id TEXT PRIMARY KEY, origin TEXT NOT NULL, destination TEXT NOT NULL,
            status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,
            kind TEXT NOT NULL,detail TEXT NOT NULL)""")
        if "owner_id" not in {r[1] for r in db.execute("PRAGMA table_info(trips)")}:
            db.execute("ALTER TABLE trips ADD COLUMN owner_id TEXT REFERENCES users(id)")
        existing = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if existing:
            db.execute("CREATE TABLE users_v2" + USERS)
            db.execute("""INSERT INTO users_v2(id,username,password_hash,role,enabled,created_at)
                          SELECT id,username,password_hash,role,enabled,created_at FROM users""")
            db.execute("DROP TABLE users")
            db.execute("ALTER TABLE users_v2 RENAME TO users")
        else:
            db.execute("CREATE TABLE users" + USERS)
        db.execute("""CREATE TABLE IF NOT EXISTS sessions(
            token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),
            expires_at REAL NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS configuration(
            id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL,payload TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS trips_owner ON trips(owner_id)")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Migration foreign-key check failed")
        db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.execute("PRAGMA foreign_keys=ON")
