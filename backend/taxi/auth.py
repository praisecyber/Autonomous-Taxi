"""Single-process local account authentication; no credentials are bundled."""

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool
from pwdlib import PasswordHash

PASSWORDS = PasswordHash.recommended()  # Argon2id via pwdlib[argon2]
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
SESSION_SECONDS = 8 * 60 * 60
COOKIE = "taxi_session"
ROLES = {"passenger", "operator", "admin", "diagnostics"}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(token):
    return hmac.new(token.encode(), b"taxi-csrf-v1", hashlib.sha256).hexdigest()


def public_user(row):
    return {
        key: row[key]
        for key in ("id", "username", "role", "enabled", "created_at", "must_change_password")
    }


class Auth:
    def __init__(self, store, operator_token, legacy_enabled=True, secure_cookie=False):
        self.store = store
        self.operator_token = operator_token
        self.legacy_enabled = legacy_enabled
        self.secure_cookie = secure_cookie
        self.failures = defaultdict(deque)

    def identity(self, request: Request, required=True):
        # Explicit authorization never falls back to cookies on a bad bearer token.
        authorization = request.headers.get("authorization")
        if authorization is not None:
            if self.legacy_enabled and secrets.compare_digest(
                authorization.encode(), ("Bearer " + self.operator_token).encode()
            ):
                return {"id": None, "role": "operator", "username": "local-operator"}
            raise HTTPException(401, "Invalid credentials")
        token = request.cookies.get(COOKIE, "")
        row = (
            self.store.db.execute(
                """SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
               WHERE s.token_hash=? AND s.expires_at>? AND u.enabled=1""",
                (digest(token), time.time()),
            ).fetchone()
            if token
            else None
        )
        if row:
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                supplied = request.headers.get("x-taxi-csrf", "")
                if not secrets.compare_digest(supplied.encode(), csrf_for(token).encode()):
                    raise HTTPException(403, "Valid CSRF token required")
                origin = request.headers.get("origin")
                if origin and origin != str(request.base_url).rstrip("/"):
                    raise HTTPException(403, "Cross-origin request rejected")
            if row["must_change_password"] and request.url.path not in {
                "/api/auth/me",
                "/api/auth/logout",
                "/api/auth/password",
            }:
                raise HTTPException(
                    403, "Change your temporary password through Account before continuing"
                )
            return public_user(row)
        if required:
            raise HTTPException(401, "Sign in required")
        return None

    def require(self, request, *roles):
        user = self.identity(request)
        if user["role"] not in roles:
            raise HTTPException(403, "Role not permitted")
        return user

    async def login(self, request, response: Response, username, password):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Cross-origin request rejected")
        now = time.time()
        # Bounded per-client attempt limit; includes successful attempts to cap hashing work.
        for key in list(self.failures):
            while self.failures[key] and self.failures[key][0] < now - 300:
                self.failures[key].popleft()
            if not self.failures[key]:
                del self.failures[key]
        key = request.client.host if request.client else "local"
        attempts = self.failures[key]
        if len(attempts) >= 10:
            raise HTTPException(429, "Too many login attempts; retry in five minutes")
        attempts.append(now)
        row = self.store.db.execute(
            "SELECT * FROM users WHERE username=?", (username.casefold(),)
        ).fetchone()
        verified_hash = row["password_hash"] if row else DUMMY_HASH
        valid = await run_in_threadpool(PASSWORDS.verify, password, verified_hash)
        if row:
            row = self.store.db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
        if not row or not valid or not row["enabled"] or row["password_hash"] != verified_hash:
            raise HTTPException(401, "Invalid username or password")
        token = secrets.token_urlsafe(32)
        with self.store.db:
            self.store.db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            # Re-login replaces this browser's existing session.
            previous = request.cookies.get(COOKIE)
            if previous:
                self.store.db.execute(
                    "DELETE FROM sessions WHERE token_hash=?", (digest(previous),)
                )
            self.store.db.execute(
                "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (digest(token), row["id"], now + SESSION_SECONDS),
            )
        response.set_cookie(
            COOKIE,
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            secure=self.secure_cookie,
            samesite="strict",
            path="/",
        )
        self.store.event("login", {"user_id": row["id"]})
        return {"user": public_user(row), "csrf_token": csrf_for(token)}
