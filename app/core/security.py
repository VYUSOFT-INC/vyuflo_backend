# """
# Security utilities:
#   - Password hashing (bcrypt via passlib)
#   - JWT access & refresh token creation/verification
#   - OTP generation and verification (TOTP / random 6-digit)
# """
# import secrets
# import string
# from datetime import datetime, timedelta, timezone
# from typing import Any, Optional

# import pyotp
# from jose import JWTError, jwt
# from passlib.context import CryptContext

# from app.core.config import settings
# # from backend.app.routes.admin import permissions

# # ── Password ──────────────────────────────────────────────────────────────────
# _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def hash_password(plain: str) -> str:
#     return _pwd_ctx.hash(plain)


# def verify_password(plain: str, hashed: str) -> bool:
#     return _pwd_ctx.verify(plain, hashed)


# # ── JWT ───────────────────────────────────────────────────────────────────────
# def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
#     payload = data.copy()
#     payload["exp"] = datetime.now(timezone.utc) + expires_delta
#     return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# # def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
# #     data = {"sub": subject, "type": "access"}
# #     if extra:
# #         data.update(extra)
# #     return _create_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

# def create_access_token(user_id: str, roles: list[str], permissions: list[str] = []) -> str:
#     expire = datetime.now(timezone.utc) + timedelta(minutes=30)
#     payload = {
#         "sub":   user_id,
#         "roles": roles,
#         "permissions": permissions,  
#         "type":  "access",
#         "exp":   expire,
#     }
#     return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# def create_refresh_token(subject: str) -> str:
#     data = {"sub": subject, "type": "refresh"}
#     return _create_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

# from typing import Any, Dict
# from jose import jwt

# def decode_token(token: str) -> Dict[str, Any]:
#     """Decode and validate a JWT. Raises JWTError on failure."""
#     payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#     return payload


# # ── OTP (6-digit numeric, stateless random) ───────────────────────────────────
# def generate_otp(length: int = 6) -> str:
#     """Generate a cryptographically secure numeric OTP."""
#     return "".join(secrets.choice(string.digits) for _ in range(length))


# def hash_otp(otp: str) -> str:
#     """Hash an OTP for storage (same bcrypt pool)."""
#     return _pwd_ctx.hash(otp)


# def verify_otp(plain: str, hashed: str) -> bool:
#     """Verify a plain OTP against its stored hash."""
#     return _pwd_ctx.verify(plain, hashed)


# # ── Secure random token (for password reset links, etc.) ─────────────────────
# def generate_secure_token(nbytes: int = 32) -> str:
#     return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
# app/core/security.py
"""
Security utilities:
  - Password hashing (bcrypt via passlib)
  - JWT access & refresh token creation/verification
  - OTP generation and verification
  - Refresh token store (in-memory dev / swap for Redis in prod)
"""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pyotp
from jose import JWTError, jwt
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
) -> str:
    payload = {
        "sub": user_id,
        "roles": roles,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "access",
    }

    return _create_token(payload, timedelta(minutes=30))

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub":  user_id,
        "type": "refresh",
    }
    return _create_token(payload, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise


# ── Refresh token store ───────────────────────────────────────────────────────
# DEV: in-memory dict — fine for development
# PROD: swap with Redis (e.g. await redis.set(f"rt:{user_id}", token, ex=604800))

_refresh_token_store: dict[str, str] = {}

async def store_refresh_token(user_id: str, refresh_token: str) -> None:
    _refresh_token_store[user_id] = refresh_token

async def verify_refresh_token(user_id: str, refresh_token: str) -> bool:
    stored = _refresh_token_store.get(user_id)
    return stored == refresh_token

async def revoke_refresh_token(user_id: str) -> None:
    _refresh_token_store.pop(user_id, None)


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(length))

def hash_otp(otp: str) -> str:
    return _pwd_ctx.hash(otp)

def verify_otp(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)