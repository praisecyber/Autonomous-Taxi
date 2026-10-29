"""Offline account provisioning with private, non-overwriting credential delivery."""

import json
import os
import secrets
import tempfile
import uuid
from pathlib import Path

from pydantic import ValidationError
from .accounts import NewUser
from .auth import PASSWORDS
from .locking import DatabaseLease
from .storage import Store, utc_now


def provision_accounts(database, manifest, credentials_out):
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= 100:
        raise ValueError("Account manifest must contain 1–100 username/role entries")
    records, names = [], set()
    for entry in manifest:
        if not isinstance(entry, dict) or set(entry) != {"username", "role"}:
            raise ValueError("Each account entry must contain username and role only")
        password = secrets.token_urlsafe(24)
        try:
            validated = NewUser(**entry, password=password)
        except ValidationError:
            raise ValueError("Invalid username or role in account manifest") from None
        username = validated.username.casefold()
        if username in names:
            raise ValueError("Duplicate username in manifest")
        names.add(username)
        records.append(
            {"username": username, "role": validated.role, "temporary_password": password}
        )
    output = Path(credentials_out).resolve()
    if output.exists():
        raise ValueError("Credential output already exists; it will not be overwritten")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    published = False
    with DatabaseLease(database):
        store = Store(str(database), recover=False)
        temporary = None
        try:
            for name in names:
                if store.db.execute("SELECT 1 FROM users WHERE username=?", (name,)).fetchone():
                    raise ValueError(
                        "A requested account already exists; existing users are unchanged"
                    )
            if (
                not any(r["role"] == "admin" for r in records)
                and not store.db.execute(
                    "SELECT 1 FROM users WHERE role='admin' AND enabled=1"
                ).fetchone()
            ):
                raise ValueError("Provision at least one administrator")
            hashed = [
                (
                    uuid.uuid4().hex,
                    r["username"],
                    PASSWORDS.hash(r["temporary_password"]),
                    r["role"],
                    utc_now(),
                    1,
                )
                for r in records
            ]
            fd, temporary = tempfile.mkstemp(prefix=".credentials-", dir=output.parent)
            with os.fdopen(fd, "w") as stream:
                json.dump({"password_change_required": True, "accounts": records}, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            with store.db:
                store.db.executemany(
                    """INSERT INTO users(
                    id,username,password_hash,role,created_at,must_change_password)
                    VALUES(?,?,?,?,?,?)""",
                    hashed,
                )
                store.db.execute(
                    "INSERT INTO events(at,kind,detail) VALUES(?,?,?)",
                    (
                        utc_now(),
                        "accounts_provisioned",
                        json.dumps(
                            {
                                "accounts": [
                                    {"username": r["username"], "role": r["role"]} for r in records
                                ]
                            }
                        ),
                    ),
                )
                os.link(temporary, output)
                published = True
        except BaseException:
            if published:
                output.unlink(missing_ok=True)
            raise
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
            store.close()
    return [{"username": r["username"], "role": r["role"]} for r in records]
