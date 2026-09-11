"""
Auth API endpoints.

POST   /api/auth/register   — create account (strictly @credresolve.com)
POST   /api/auth/login      — verify credentials, return session token
POST   /api/auth/logout     — invalidate session token
GET    /api/auth/me         — return current user info
GET    /api/auth/users      — list all users (admin)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.config import get_settings
from app.schemas.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserInfo,
)
from app.services import auth_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
_settings = get_settings()

ALLOWED_DOMAIN = "@credresolve.com"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _token_from_header(authorization: Optional[str]) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return authorization.removeprefix("Bearer ").strip()


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> dict:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.removeprefix("Bearer ").strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header or token",
        )
    user = await svc.get_user_by_token(raw_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
        )
    return user


# ─── POST /api/auth/register ─────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=dict)
async def register(payload: RegisterRequest):
    """Register a new user (restricted strictly to @credresolve.com)."""
    clean_email = payload.email.strip().lower()

    if not clean_email.endswith(ALLOWED_DOMAIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration is restricted to {ALLOWED_DOMAIN} email addresses only.",
        )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters",
        )

    try:
        user = await svc.create_user(clean_email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("New user registered: %s", user["email"])
    return {
        "message": "Account created successfully. You can now sign in.",
        "email": user["email"],
    }


# ─── POST /api/auth/login ─────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """Authenticate and return a session token."""
    user = await svc.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = await svc.create_session(user["id"], _settings.session_expiry_days)
    logger.info("User logged in: %s", user["email"])

    return AuthResponse(
        token=token,
        email=user["email"],
        user_id=user["id"],
    )


# ─── POST /api/auth/logout ───────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(authorization: Optional[str] = Header(default=None)):
    """Invalidate the session token."""
    try:
        token = _token_from_header(authorization)
        await svc.invalidate_session(token)
    except HTTPException:
        pass  # already invalid — that's fine


# ─── GET /api/auth/me ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserInfo)
async def me(current_user: dict = Depends(get_current_user)):
    """Return current authenticated user's info."""
    return UserInfo(
        id=current_user["id"],
        email=current_user["email"],
        created_at=current_user["created_at"],
    )


# ─── GET /api/auth/users ────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserInfo])
async def list_users(current_user: dict = Depends(get_current_user)):
    """List all registered users (any authenticated user can view)."""
    users = await svc.list_users()
    return [
        UserInfo(id=u["id"], email=u["email"], created_at=u["created_at"])
        for u in users
    ]
