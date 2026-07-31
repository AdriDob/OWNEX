"""
API Router for User Authentication
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

from cores.auth.user_auth import get_user_auth
from database import db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    device_type: str = "android"
    device_name: str = "Unknown Device"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_type: str = "android"
    device_name: str = "Unknown Device"


@router.post("/register")
async def register(payload: RegisterRequest):
    """Register new user."""
    try:
        auth = get_user_auth(db.SessionLocal())
        result = auth.register_user(
            email=payload.email,
            password=payload.password,
            device_type=payload.device_type,
            device_name=payload.device_name,
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(payload: LoginRequest):
    """Login user."""
    try:
        auth = get_user_auth(db.SessionLocal())
        result = auth.login_user(
            email=payload.email,
            password=payload.password,
            device_type=payload.device_type,
            device_name=payload.device_name,
        )

        if not result["success"]:
            raise HTTPException(status_code=401, detail=result["error"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(authorization: str = Header(...)):
    """Logout user."""
    try:
        access_token = authorization.replace("Bearer ", "")
        auth = get_user_auth(db.SessionLocal())
        auth.logout_user(access_token)

        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
async def verify_token(authorization: str = Header(...)):
    """Verify access token."""
    try:
        access_token = authorization.replace("Bearer ", "")
        auth = get_user_auth(db.SessionLocal())
        result = auth.verify_token(access_token)

        if not result:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"success": True, "user_id": result["user_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    try:
        auth = get_user_auth(db.SessionLocal())
        result = auth.refresh_token(refresh_token)

        if not result:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail(str(e))
