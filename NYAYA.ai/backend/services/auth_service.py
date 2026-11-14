"""Simple password + session-token authentication (standard library only)."""
import hashlib
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException

from database.db import db


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """PBKDF2-SHA256 hash. Returns (hash_hex, salt_hex)."""
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000)
    return h.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    return secrets.compare_digest(hash_password(password, salt)[0], stored_hash)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def public_user(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "language": row["language"], "is_admin": bool(row["is_admin"]),
            "created_at": row["created_at"]}


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """FastAPI dependency: resolve 'Authorization: Bearer <token>' to a user or 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please log in.")
    token = authorization.split(" ", 1)[1].strip()
    with db() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Session expired. Please log in again.")
    return public_user(row)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user["is_admin"]:
        raise HTTPException(403, "Admin access required.")
    return user
