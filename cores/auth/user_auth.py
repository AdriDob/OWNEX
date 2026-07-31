"""
User Authentication System — Sistema de Autenticación de Usuarios

Sistema simple de autenticación para sincronización móvil vía cloud.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("ownex.user_auth")


class UserAuth:
    """Sistema de autenticación de usuarios."""

    def __init__(self, db_session):
        """Inicializar sistema de autenticación."""
        self.db = db_session

    def hash_password(self, password: str) -> str:
        """Hash password usando SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(
        self,
        email: str,
        password: str,
        device_type: str = "android",
        device_name: str = "Unknown Device",
    ) -> dict[str, str]:
        """Registrar nuevo usuario."""
        # Check if user exists
        existing_user = self.db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            return {"success": False, "error": "User already exists"}

        # Hash password
        password_hash = self.hash_password(password)

        # Create user
        user_id = str(secrets.uuid4())
        created_at = datetime.now()

        self.db.execute(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, email, password_hash, created_at),
        )
        self.db.commit()

        # Create session
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)

        self.db.execute(
            """
            INSERT INTO sessions (id, user_id, device_type, device_name, access_token, refresh_token, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(secrets.uuid4()),
                user_id,
                device_type,
                device_name,
                session_token,
                refresh_token,
                expires_at,
            ),
        )
        self.db.commit()

        logger.info(f"User registered: {email}")

        return {
            "success": True,
            "user_id": user_id,
            "access_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
        }

    def login_user(
        self,
        email: str,
        password: str,
        device_type: str = "android",
        device_name: str = "Unknown Device",
    ) -> dict[str, str]:
        """Login usuario existente."""
        # Get user
        user = self.db.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if not user:
            return {"success": False, "error": "Invalid credentials"}

        user_id, password_hash = user

        # Verify password
        if self.hash_password(password) != password_hash:
            return {"success": False, "error": "Invalid credentials"}

        # Create session
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)

        self.db.execute(
            """
            INSERT INTO sessions (id, user_id, device_type, device_name, access_token, refresh_token, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(secrets.uuid4()),
                user_id,
                device_type,
                device_name,
                session_token,
                refresh_token,
                expires_at,
            ),
        )
        self.db.commit()

        logger.info(f"User logged in: {email}")

        return {
            "success": True,
            "user_id": user_id,
            "access_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
        }

    def verify_token(self, access_token: str) -> Optional[dict[str, str]]:
        """Verificar access token."""
        session = self.db.execute(
            """
            SELECT user_id, expires_at FROM sessions
            WHERE access_token = ? AND expires_at > ?
            """,
            (access_token, datetime.now()),
        ).fetchone()

        if not session:
            return None

        user_id, expires_at = session

        return {
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
        }

    def refresh_token(self, refresh_token: str) -> Optional[dict[str, str]]:
        """Refresh access token."""
        session = self.db.execute(
            """
            SELECT user_id FROM sessions
            WHERE refresh_token = ? AND expires_at > ?
            """,
            (refresh_token, datetime.now()),
        ).fetchone()

        if not session:
            return None

        user_id = session[0]

        # Generate new tokens
        new_access_token = secrets.token_urlsafe(32)
        new_refresh_token = secrets.token_urlsafe(32)
        new_expires_at = datetime.now() + timedelta(days=30)

        # Update session
        self.db.execute(
            """
            UPDATE sessions
            SET access_token = ?, refresh_token = ?, expires_at = ?
            WHERE refresh_token = ?
            """,
            (new_access_token, new_refresh_token, new_expires_at, refresh_token),
        )
        self.db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "expires_at": new_expires_at.isoformat(),
        }

    def logout_user(self, access_token: str) -> bool:
        """Logout usuario."""
        self.db.execute(
            "DELETE FROM sessions WHERE access_token = ?",
            (access_token,),
        )
        self.db.commit()

        logger.info("User logged out")
        return True


# Singleton instance
_user_auth: Optional[UserAuth] = None


def get_user_auth(db_session) -> UserAuth:
    """Obtener instancia singleton de UserAuth."""
    global _user_auth

    if _user_auth is None:
        _user_auth = UserAuth(db_session)

    return _user_auth
