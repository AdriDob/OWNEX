"""User registration, login, and profile management.

Uses stdlib PBKDF2-HMAC-SHA256 for password hashing (no bcrypt dependency).
Integrates with existing JWT token system in core_engines/auth.

Email verification: when OWNNEX_MAIL_SMTP_HOST is configured, new accounts are
created inactive until the verification link is clicked. Without SMTP (local
first mode), accounts are created pre-verified.
"""

import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from api.middleware.auth_middleware import SESSION_COOKIE
from cores.auth.auth import (
    create_refresh_token,
    create_session_token,
    verify_token,
)
from cores.mail.service import mail_configured, send_verification_email
from database.db import SessionLocal
from database.models import User

logger = logging.getLogger("ownex.auth_users")

router = APIRouter(prefix="/api/auth/users", tags=["auth-users"])

TOKEN_TTL_HOURS = 24


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_session_cookie(response: Response, token: str, secure: bool) -> None:
    """Set the httpOnly session cookie. The token stays in the response body
    so the Bearer flow keeps working (incremental migration: cookie and
    header coexist, header wins in the middleware)."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=TOKEN_TTL_HOURS * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


# ─── Password helpers (PBKDF2-HMAC-SHA256, stdlib only) ───────────────


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return dk.hex() == dk_hex


# ─── Schemas ─────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    email_verified: bool = True


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyResponse(BaseModel):
    email: str
    username: str
    verified: bool = True


class ResendRequest(BaseModel):
    email: str


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    email_verified: bool = False
    created_at: str


# ─── Endpoints ───────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request, response: Response):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(body.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")

    session = SessionLocal()
    try:
        if session.query(User).filter((User.username == body.username) | (User.email == body.email)).first():
            raise HTTPException(409, "Username or email already exists")

        requires_verification = mail_configured()
        verification_token: str | None = None
        raw_verification_token: str | None = None
        if requires_verification:
            raw_verification_token = secrets.token_urlsafe(32)
            verification_token = _hash_token(raw_verification_token)

        user = User(
            username=body.username,
            email=body.email,
            password_hash=_hash_password(body.password),
            is_active=not requires_verification,
            email_verified=not requires_verification,
            verification_token=verification_token,
            verification_expires=(
                datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS) if requires_verification else None
            ),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        if requires_verification:
            try:
                send_verification_email(body.email, body.username, raw_verification_token)
            except Exception as exc:
                logger.warning("Verification email failed for %s: %s", body.email, exc)
                raise HTTPException(503, "Account created but verification email could not be sent") from exc

        access_token = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        refresh_token = create_refresh_token(user_id=str(user.id))
        _set_session_cookie(response, access_token, request.url.scheme == "https")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            email_verified=user.email_verified,
        )
    finally:
        session.close()


@router.post("/verify")
def verify_email(token: str = Query(...)):
    if not token:
        raise HTTPException(400, "Missing token")

    token_hash = _hash_token(token)
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.verification_token == token_hash).first()
        if not user:
            raise HTTPException(400, "Invalid or expired verification token")
        if user.email_verified:
            return VerifyResponse(email=user.email, username=user.username)
        if user.verification_expires and user.verification_expires < datetime.now(UTC).replace(tzinfo=None):
            raise HTTPException(400, "Verification token expired — request a new one")

        user.email_verified = True
        user.is_active = True
        user.verification_token = None
        user.verification_expires = None
        session.commit()
        return VerifyResponse(email=user.email, username=user.username)
    finally:
        session.close()


@router.post("/resend-verification")
def resend_verification(body: ResendRequest):
    if not mail_configured():
        raise HTTPException(400, "Email verification is not enabled on this instance")

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == body.email).first()
        if not user:
            raise HTTPException(404, "No account found with that email")
        if user.email_verified:
            return VerifyResponse(email=user.email, username=user.username)

        new_raw_token = secrets.token_urlsafe(32)
        new_token = _hash_token(new_raw_token)
        user.verification_token = new_token
        user.verification_expires = datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS)
        session.commit()

        try:
            send_verification_email(user.email, user.username, new_raw_token)
        except Exception as exc:
            logger.warning("Resend verification email failed for %s: %s", user.email, exc)
            raise HTTPException(503, "Verification email could not be sent") from exc
        return VerifyResponse(email=user.email, username=user.username)
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, response: Response):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == body.username).first()
        if not user or not _verify_password(body.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        if not user.is_active:
            if not user.email_verified and user.verification_token:
                raise HTTPException(403, "Email not verified — check your inbox or request a new link")
            raise HTTPException(403, "Account is disabled")

        access_token = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        refresh_token = create_refresh_token(user_id=str(user.id))
        _set_session_cookie(response, access_token, request.url.scheme == "https")
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    finally:
        session.close()


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, request: Request, response: Response):
    data = verify_token(body.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = data.get("sub", "")
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active or not user.email_verified:
            raise HTTPException(401, "User not found or inactive")

        new_access = create_session_token(
            user_id=str(user.id),
            meta={"username": user.username, "email": user.email},
        )
        new_refresh = create_refresh_token(user_id=str(user.id))
        _set_session_cookie(response, new_access, request.url.scheme == "https")
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)
    finally:
        session.close()


@router.get("/me", response_model=UserProfile)
def get_profile(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        raise HTTPException(401, "Not authenticated")
    data = verify_token(token)
    if data is None:
        raise HTTPException(401, "Invalid or expired token")
    user_id = data.get("sub", "")

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(404, "User not found")
        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )
    finally:
        session.close()


@router.post("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "logged_out"}
