"""Register, login, profile."""
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException

from config import ADMIN_EMAIL
from database.db import db
from schemas.schemas import LoginIn, ProfileIn, RegisterIn
from services.auth_service import (create_session, get_current_user, hash_password,
                                   public_user, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterIn):
    h, salt = hash_password(body.password)
    is_admin = 1 if body.email == ADMIN_EMAIL else 0
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, salt, language, is_admin) "
                "VALUES (?,?,?,?,?,?)",
                (body.name.strip(), body.email, h, salt, body.language, is_admin),
            )
            row = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this e-mail already exists.")
    return {"token": create_session(row["id"]), "user": public_user(row)}


@router.post("/login")
def login(body: LoginIn):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (body.email.strip().lower(),)).fetchone()
    if not row or not verify_password(body.password, row["password_hash"], row["salt"]):
        raise HTTPException(401, "Incorrect e-mail or password.")
    return {"token": create_session(row["id"]), "user": public_user(row)}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.patch("/me")
def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    """Profile settings: display name and preferred language."""
    with db() as conn:
        if body.name is not None:
            conn.execute("UPDATE users SET name=? WHERE id=?", (body.name.strip(), user["id"]))
        if body.language is not None:
            conn.execute("UPDATE users SET language=? WHERE id=?", (body.language, user["id"]))
        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return public_user(row)


@router.post("/logout")
def logout(authorization: str = Header(default="")):
    token = authorization.split(" ", 1)[-1].strip()
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    return {"ok": True}
