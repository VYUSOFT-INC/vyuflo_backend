"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
"""
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


# ── Password ──────────────────────────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    user_id: str,
    roles: list[str],
    email: str,
    first_name: str,
    last_name: str,
    token_version: int = 0,
) -> str:
    """
    token_version is checked on every request in get_current_user.
    Bumping a user's token_version in the DB invalidates every access token
    issued before the bump — instantly, without waiting for expiry.
    """
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "token_version": token_version,
        "type": "access",
    }
    return _create_token(payload, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(user_id: str, session_id: str) -> str:
    """
    session_id ties this refresh token to one specific login (one device/browser).
    Each device gets its own session_id, so signing in on a new device never
    kicks out other devices, and each can be revoked independently.
    """
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure (expired, bad signature, etc.)."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def new_session_id() -> str:
    """One per login — identifies a single device/browser session."""
    return str(uuid.uuid4())


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)