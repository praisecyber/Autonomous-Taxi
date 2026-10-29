"""Offline administration: python -m taxi.manage --help. Stop the server first."""

import argparse
import json
import getpass
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path

from pydantic import ValidationError

from .auth import PASSWORDS
from .storage import Store, utc_now
from .migrations import SCHEMA_VERSION
from .locking import DatabaseLease


def create_admin(database, username, password):
    from .accounts import NewUser

    try:
        validated = NewUser(username=username, password=password, role="admin")
    except ValidationError:
        raise ValueError("Use a 3–64 character username and a 12–128 character password") from None
    with DatabaseLease(database):
        store = Store(str(database), recover=False)
        try:
            with store.db:
                # Bootstrap only; further admins must be created through authenticated UI/API.
                if store.db.execute(
                    "SELECT 1 FROM users WHERE role='admin' AND enabled=1"
                ).fetchone():
                    raise ValueError(
                        "An enabled administrator already exists; use account management"
                    )
                store.db.execute(
                    "INSERT INTO users(id,username,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        validated.username.casefold(),
                        PASSWORDS.hash(password),
                        "admin",
                        utc_now(),
                    ),
                )
            store.event("admin_bootstrapped", {"username": validated.username.casefold()})
        finally:
            store.close()


def copy_database(source, output, restore=False):
    """SQLite backup API captures WAL consistently; output must be a new file."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist")
    if output.exists():
        raise ValueError("Output exists; choose a new path (no overwrite)")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".taxi-db-", dir=output.parent)
    os.close(fd)
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
            if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Source integrity check failed")
            if src.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Source foreign-key check failed")
            if src.execute("PRAGMA user_version").fetchone()[0] not in range(SCHEMA_VERSION + 1):
                raise ValueError("Unsupported backup schema")
            tables = {
                r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if not {"trips", "events"}.issubset(tables):
                raise ValueError("Not a taxi database")
            with sqlite3.connect(temporary) as dst:
                src.backup(dst)
        if restore:
            store = Store(temporary)  # Migrate and interrupt active trips; never resume motion.
            with store.db:
                store.db.execute("DELETE FROM sessions")  # Backups cannot resurrect logins.
            store.event("restore", {"sessions_revoked": True})
            store.close()
        # Atomic publication without overwriting another process's newly created output.
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("create-admin", help="Bootstrap the first admin, offline")
    bootstrap.add_argument("--database", default="runtime/taxi.sqlite3")
    bootstrap.add_argument("--username", required=True)
    provision = commands.add_parser(
        "provision-accounts", help="Offline generated-password accounts; no overwrite"
    )
    provision.add_argument("--database", default="runtime/taxi.sqlite3")
    provision.add_argument("--manifest", required=True)
    provision.add_argument("--credentials-out", required=True)
    for action in ("backup", "restore"):
        command = commands.add_parser(
            action, help="Copy to a new output; never overwrite live data"
        )
        command.add_argument("--source", required=True)
        command.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "create-admin":
            password = getpass.getpass("New admin password (12–128 characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match")
            create_admin(args.database, args.username, password)
        elif args.command == "provision-accounts":
            from .provisioning import provision_accounts

            manifest = json.loads(Path(args.manifest).read_text())
            accounts = provision_accounts(args.database, manifest, args.credentials_out)
            print(
                f"Provisioned {len(accounts)} accounts. Private credentials written to the requested output; change at first login."
            )
        else:
            copy_database(args.source, args.output, restore=args.command == "restore")
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"{exc}\n")
    print("Completed. Keep database copies private: they contain account and trip records.")


if __name__ == "__main__":
    main()
