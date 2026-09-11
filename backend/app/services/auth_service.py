"""
Auth service — user management, password hashing, session tokens.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt

from app.models.db import get_db

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8")[:72], salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ─── User CRUD ────────────────────────────────────────────────────────────────

async def create_user(email: str, password: str) -> Dict[str, Any]:
    """Create a new user. Raises ValueError if email already exists."""
    email = email.strip().lower()
    pw_hash = hash_password(password)
    now = _now()

    async with get_db() as db:
        # Check duplicate
        async with db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ) as cur:
            if await cur.fetchone():
                raise ValueError(f"Email already registered: {email}")

        await db.execute(
            "INSERT INTO users (email, password_hash, created_at, is_active) VALUES (?, ?, ?, 1)",
            (email, pw_hash, now),
        )
        await db.commit()

        async with db.execute(
            "SELECT id, email, created_at, is_active FROM users WHERE email = ?",
            (email,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row)


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email = email.strip().lower()
    async with get_db() as db:
        async with db.execute(
            "SELECT id, email, password_hash, created_at, is_active FROM users WHERE email = ?",
            (email,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify credentials. Returns user dict on success, None on failure."""
    user = await get_user_by_email(email)
    if not user:
        return None
    if not user["is_active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# ─── Session CRUD ─────────────────────────────────────────────────────────────

async def create_session(user_id: int, expiry_days: int = 30) -> str:
    """Generate a session token, persist it, return the token string."""
    token = secrets.token_urlsafe(48)
    now = _now()
    expires = _expires(expiry_days)

    async with get_db() as db:
        # Clean up old sessions for this user (keep last 5)
        await db.execute(
            """
            DELETE FROM sessions
            WHERE user_id = ?
              AND token NOT IN (
                SELECT token FROM sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 4
              )
            """,
            (user_id, user_id),
        )
        await db.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now, expires),
        )
        await db.commit()

    return token


async def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Return the user for a valid, non-expired session token."""
    now = _now()
    async with get_db() as db:
        async with db.execute(
            """
            SELECT u.id, u.email, u.created_at, u.is_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
              AND s.expires_at > ?
              AND u.is_active = 1
            """,
            (token, now),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def invalidate_session(token: str) -> None:
    async with get_db() as db:
        await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        await db.commit()


async def list_users() -> list[Dict[str, Any]]:
    """Return all users (for admin purposes)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, email, created_at, is_active FROM users ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
