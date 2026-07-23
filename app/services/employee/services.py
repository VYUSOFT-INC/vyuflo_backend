"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        VisaFlow — services.py                               ║
║                                                                              ║
║  ARCHITECTURE RULE:                                                          ║
║  One generic CRUD function is defined at the top (db_*).                    ║
║  Every feature (auth, onboarding, password reset …) calls those helpers.    ║
║  Import from this file everywhere — never write raw SQLAlchemy queries       ║
║  in route handlers.                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence, Type, TypeVar

import httpx
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.redis import redis_set
from app.models.visamodels import Role, UserProfile, UserRole

# ── Generic type var for ORM models ──────────────────────────────────────────
ModelT = TypeVar("ModelT")


from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║               GENERIC CRUD FUNCTIONS  ← import these everywhere         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def db_create(db: AsyncSession, model: ModelT) -> ModelT:
    """
    Insert a new ORM model instance into the DB and return it with its
    auto-generated fields (id, created_at …) populated.

    Usage:
        user = User(email="a@b.com", ...)
        user = await db_create(db, user)
    """
    db.add(model)
    await db.flush()          # writes to DB within the transaction
    await db.refresh(model)   # pulls back server-generated defaults
    return model


async def db_get_by_id(
    db: AsyncSession,
    model_class: Type[ModelT],
    record_id: uuid.UUID,
) -> Optional[ModelT]:
    """
    Fetch a single row by primary key (UUID).

    Usage:
        user = await db_get_by_id(db, User, user_id)
    """
    result = await db.execute(
        select(model_class).where(model_class.id == record_id)
    )
    return result.scalars().first()


async def db_get_by_field(
    db: AsyncSession,
    model_class: Type[ModelT],
    field_name: str,
    value: Any,
) -> Optional[ModelT]:
    """
    Fetch a single row matching one field.

    Usage:
        user = await db_get_by_field(db, User, "email", "a@b.com")
    """
    column = getattr(model_class, field_name)
    result = await db.execute(
        select(model_class).where(column == value)
    )
    return result.scalars().first()

from sqlalchemy import select, cast, String


async def db_get_by_field_like(
    db: AsyncSession,
    model_class,
    field_name: str,
    value: str,
):
    column = getattr(model_class, field_name)

    result = await db.execute(
        select(model_class).where(
            cast(column, String).ilike(f"%{value}%")
        )
    )
    return result.scalars().first()

async def db_list(
    db: AsyncSession,
    model_class: Type[ModelT],
    filters: Optional[list] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[ModelT]:
    """
    List rows with optional SQLAlchemy filter clauses.

    Usage:
        records = await db_list(db, User, filters=[User.is_active == True])
    """
    stmt = select(model_class)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


async def db_update(
    db: AsyncSession,
    model_class: Type[ModelT],
    record_id: uuid.UUID,
    data: dict[str, Any],
) -> Optional[ModelT]:
    """
    Update fields on a row identified by primary key.

    Usage:
        user = await db_update(db, User, user_id, {"is_verified": True})
    """
    await db.execute(
        update(model_class)
        .where(model_class.id == record_id)
        .values(**data)
    )
    return await db_get_by_id(db, model_class, record_id)


async def db_delete(
    db: AsyncSession,
    model_class: Type[ModelT],
    record_id: uuid.UUID,
) -> bool:
    """
    Hard-delete a row by primary key. Returns True if a row was deleted.

    Usage:
        deleted = await db_delete(db, UserOTP, otp_id)
    """
    result = await db.execute(
        delete(model_class).where(model_class.id == record_id)
    )
    return result.rowcount > 0

async def get_user_role(db: AsyncSession, user_id: uuid.UUID):       
    result = await db.execute(
        select(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    return result.scalars().all()  # list of roles

async def get_user_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserProfile | None:
    result = await db.execute(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
    )
    return result.scalars().first()

async def db_upsert(
    db: AsyncSession,
    model_class: Type[ModelT],
    lookup_field: str,
    lookup_value: Any,
    data: dict[str, Any],
) -> ModelT:
    """
    Get-or-create semantics: if a row matching lookup_field exists, update it;
    otherwise create a new one.

    Usage:
        profile = await db_upsert(
            db, UserProfile, "user_id", user.id,
            {"full_legal_name": "John Doe"}
        )
    """
    existing = await db_get_by_field(db, model_class, lookup_field, lookup_value)
    if existing:
        return await db_update(db, model_class, existing.id, data)
    new_obj = model_class(**{lookup_field: lookup_value, **data})
    return await db_create(db, new_obj)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                 PRIVATE HELPERS                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def _store_refresh_token(user_id: str, session_id: str, refresh_token: str) -> None:
    key = f"refresh:{user_id}:{session_id}"
    await redis_set(key, refresh_token, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)


async def _verify_provider_token(provider: str, token: str) -> dict:
    """
    Verify an OAuth ID token with the provider and return user info.
    Keeps all provider HTTP calls in one place.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        if provider == "google":
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
            )
        elif provider == "microsoft":
            resp = await client.get(
                "https://graph.microsoft.com/oidc/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
        elif provider == "apple":
            # Apple requires JWT verification — simplified for now
            resp = await client.post(
                "https://appleid.apple.com/auth/token",
                data={
                    "client_id": settings.APPLE_CLIENT_ID,
                    "grant_type": "authorization_code",
                    "code": token,
                },
            )
        else:
            raise BadRequestException(f"Unknown provider: {provider}")

    if resp.status_code != 200:
        raise UnauthorizedException(f"Could not verify {provider} token")

    return resp.json()