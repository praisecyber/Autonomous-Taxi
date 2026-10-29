"""Account/session and administrator endpoints shared by all interfaces."""

import json
import sqlite3
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from .auth import COOKIE, PASSWORDS, csrf_for, digest, public_user
from .configuration import RouteConfiguration
from .storage import utc_now

router = APIRouter()


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class NewUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
    password: str = Field(min_length=12, max_length=128)
    role: Literal["passenger", "operator", "admin"]


class UserAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["passenger", "operator", "admin"]
    enabled: bool


def admin(request):
    return request.app.state.auth.require(request, "admin")


@router.post("/api/auth/login")
async def login(body: Login, request: Request, response: Response):
    return await request.app.state.auth.login(request, response, body.username, body.password)


@router.get("/api/auth/me")
async def me(request: Request):
    user = request.app.state.auth.identity(request)
    token = request.cookies.get(COOKIE)
    return {"user": user, "csrf_token": csrf_for(token) if token and user["id"] else None}


@router.post("/api/auth/logout", status_code=204)
async def logout(request: Request, response: Response):
    request.app.state.auth.identity(request)
    token = request.cookies.get(COOKIE, "")
    db = request.app.state.store.db
    with db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (digest(token),))
    response.delete_cookie(COOKIE, path="/")


@router.get("/api/admin/users")
async def users(
    request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)
):
    admin(request)
    db = request.app.state.store.db
    return {
        "items": [
            public_user(r)
            for r in db.execute(
                "SELECT * FROM users ORDER BY username LIMIT ? OFFSET ?", (limit, offset)
            )
        ],
        "total": db.execute("SELECT count(*) FROM users").fetchone()[0],
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/admin/users", status_code=201)
async def create_user(body: NewUser, request: Request):
    actor = admin(request)
    store = request.app.state.store
    user_id = uuid.uuid4().hex
    encoded = await run_in_threadpool(PASSWORDS.hash, body.password)
    actor = admin(request)  # Recheck session after password hashing yields control.
    try:
        with store.db:
            store.db.execute(
                "INSERT INTO users(id,username,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                (user_id, body.username.casefold(), encoded, body.role, utc_now()),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Username already exists") from exc
    store.event("user_created", {"actor_id": actor["id"], "user_id": user_id, "role": body.role})
    return public_user(store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


@router.patch("/api/admin/users/{user_id}")
async def update_user(user_id: str, body: UserAccess, request: Request):
    actor = admin(request)
    store = request.app.state.store
    row = store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    if user_id == actor["id"]:
        raise HTTPException(409, "Another administrator must change your access")
    if row["role"] == "admin" and row["enabled"] and (body.role != "admin" or not body.enabled):
        count = store.db.execute(
            "SELECT count(*) FROM users WHERE role='admin' AND enabled=1"
        ).fetchone()[0]
        if count <= 1:
            raise HTTPException(409, "Keep at least one enabled administrator")
    with store.db:
        store.db.execute(
            "UPDATE users SET role=?,enabled=? WHERE id=?", (body.role, int(body.enabled), user_id)
        )
        store.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    store.event(
        "user_access_changed",
        {"actor_id": actor["id"], "user_id": user_id, "role": body.role, "enabled": body.enabled},
    )
    return public_user(store.db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


@router.get("/api/admin/records/{kind}")
async def records(
    kind: Literal["trips", "events"],
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str = Query("", max_length=128),
    status: str = Query("", max_length=32),
    event_kind: str = Query("", max_length=80),
):
    admin(request)
    db = request.app.state.store.db
    clauses, values = [], []
    if q:
        # instr treats '%' and '_' literally; user text never becomes SQL syntax.
        fields = (
            "id || ' ' || origin || ' ' || destination"
            if kind == "trips"
            else ("id || ' ' || kind || ' ' || detail")
        )
        clauses.append(f"instr(lower({fields}), lower(?)) > 0")
        values.append(q)
    if kind == "trips" and status:
        clauses.append("status=?")
        values.append(status)
    if kind == "events" and event_kind:
        clauses.append("kind=?")
        values.append(event_kind)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    order = "created_at DESC, id DESC" if kind == "trips" else "id DESC"
    total = db.execute(f"SELECT count(*) FROM {kind}{where}", values).fetchone()[0]
    items = [
        dict(r)
        for r in db.execute(
            f"SELECT * FROM {kind}{where} ORDER BY {order} LIMIT ? OFFSET ?",
            [*values, limit, offset],
        )
    ]
    if kind == "events":
        for item in items:
            item["detail"] = json.loads(item["detail"])
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/api/admin/reports")
async def reports(request: Request):
    admin(request)
    db = request.app.state.store.db
    return {
        "mode": "simulation",
        "trips_by_status": {
            r["status"]: r["count"]
            for r in db.execute(
                "SELECT status,count(*) AS count FROM trips GROUP BY status ORDER BY status"
            )
        },
        "events_by_kind": {
            r["kind"]: r["count"]
            for r in db.execute(
                "SELECT kind,count(*) AS count FROM events GROUP BY kind ORDER BY kind"
            )
        },
    }


@router.get("/api/admin/configuration")
async def configuration(request: Request):
    admin(request)
    return request.app.state.core.config


@router.put("/api/admin/configuration")
async def configure(body: RouteConfiguration, request: Request):
    actor = admin(request)
    core = request.app.state.core
    # No editing through a fault, stopped mission, completed trip or mid-route position.
    if core.state != "READY" or core.current_stop != "A" or core.trip is not None:
        raise HTTPException(409, "Reset to READY at A with no trip before changing configuration")
    if body.version != core.config["version"]:
        raise HTTPException(409, "Configuration changed; reload before saving")
    payload = body.model_dump(exclude={"version"})
    version = body.version + 1
    store = request.app.state.store
    with store.db:
        store.db.execute(
            """INSERT INTO configuration(id,version,payload) VALUES(1,?,?)
            ON CONFLICT(id) DO UPDATE SET version=excluded.version,payload=excluded.payload""",
            (version, json.dumps(payload)),
        )
    core.config = {"version": version, **payload}
    store.event("configuration_changed", {"actor_id": actor["id"], "version": version})
    return core.config


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@router.post("/api/auth/password", status_code=204)
async def change_password(body: PasswordChange, request: Request, response: Response):
    user = request.app.state.auth.identity(request)
    if user["id"] is None:
        raise HTTPException(403, "An account session is required")
    db = request.app.state.store.db
    row = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    if not await run_in_threadpool(PASSWORDS.verify, body.current_password, row["password_hash"]):
        raise HTTPException(401, "Current password is incorrect")
    encoded = await run_in_threadpool(PASSWORDS.hash, body.new_password)
    request.app.state.auth.identity(request)
    with db:
        changed = db.execute(
            "UPDATE users SET password_hash=? WHERE id=? AND password_hash=?",
            (encoded, user["id"], row["password_hash"]),
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Password changed concurrently; sign in again")
        db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    request.app.state.store.event("password_changed", {"user_id": user["id"]})
    response.delete_cookie(COOKIE, path="/")
