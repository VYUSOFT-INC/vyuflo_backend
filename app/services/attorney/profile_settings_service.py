# =============================================================================
# app/services/screen13_service.py
# Screen 13 — Profile & Settings
#
# Functions:
#   service_get_my_profile()              → GET  /users/me/profile
#   service_update_my_profile()           → PATCH /users/me/profile
#   service_update_my_attorney_profile()  → PATCH /users/me/attorney-profile
#   service_update_avatar()               → PATCH /users/me/avatar
#   service_remove_avatar()               → DELETE /users/me/avatar
#
# Notification Preferences (Section B):
#   NOT here — reuse existing service functions in notification_service.py:
#     get_preferences(db, user_id)
#     update_preferences(db, user_id, body)
#   Called via existing GET/PATCH /notifications/preferences endpoints.
#
# AI Extraction Settings (Section C):
#   Skipped — already done by colleague.
# =============================================================================

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    AttorneyProfile,
    NotificationPreferences,
    Role,
    User,
    UserProfile,
    UserRole,
)


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

async def _get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found.")
    return user


async def _get_or_create_user_profile(
    db: AsyncSession, user_id: uuid.UUID
) -> UserProfile:
    result  = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(id=uuid.uuid4(), user_id=user_id, created_by=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def _get_or_create_attorney_profile(
    db: AsyncSession, user_id: uuid.UUID
) -> AttorneyProfile:
    result   = await db.execute(
        select(AttorneyProfile).where(AttorneyProfile.user_id == user_id)
    )
    attorney = result.scalar_one_or_none()
    if not attorney:
        attorney = AttorneyProfile(id=uuid.uuid4(), user_id=user_id, created_by=user_id)
        db.add(attorney)
        await db.flush()
    return attorney


async def _get_role_name(db: AsyncSession, user_id: uuid.UUID) -> Optional[str]:
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


# =============================================================================
# GET /users/me/profile
# =============================================================================

async def service_get_my_profile(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    Aggregates from users + user_profiles + attorney_profiles.
    Returns a dict matching ProfileResponse.
    """
    user = await _get_user(db, user_id)

    up_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = up_result.scalar_one_or_none()

    ap_result = await db.execute(
        select(AttorneyProfile).where(AttorneyProfile.user_id == user_id)
    )
    attorney = ap_result.scalar_one_or_none()

    role_name = await _get_role_name(db, user_id)

    return {
        "id":                  user.id,
        "first_name":          user.first_name,
        "last_name":           user.last_name,
        "email":               user.email,
        "profile_picture_url": profile.profile_picture_url if profile else None,
        "timezone":            profile.timezone            if profile else None,
        "preferred_language":  profile.preferred_language  if profile else None,
        "bar_number":          attorney.bar_number         if attorney else None,
        "bar_state":           attorney.bar_state          if attorney else None,
        "law_firm_name":       attorney.law_firm_name      if attorney else None,
          # ── ADDED: Screen 25 - Lawyer Dashboard ──────────────────────────────
        "monthly_billing_target_cents": (
            getattr(attorney, "monthly_billing_target_cents", None)
            if attorney else None
        ),
        "role":                role_name,
    }


# =============================================================================
# PATCH /users/me/profile
# =============================================================================

async def service_update_my_profile(
    db:                 AsyncSession,
    user_id:            uuid.UUID,
    first_name:         Optional[str] = None,
    last_name:          Optional[str] = None,
    timezone:           Optional[str] = None,
    preferred_language: Optional[str] = None,
) -> dict:
    """
    Partial update — only provided fields are written.
    Writes to users (name) and user_profiles (timezone, language).
    """
    user = await _get_user(db, user_id)
    now  = datetime.now(timezone.utc)

    if first_name is not None: user.first_name = first_name
    if last_name  is not None: user.last_name  = last_name
    user.modified_by = user_id
    user.updated_at  = now

    if timezone is not None or preferred_language is not None:
        profile = await _get_or_create_user_profile(db, user_id)
        if timezone           is not None: profile.timezone           = timezone
        if preferred_language is not None: profile.preferred_language = preferred_language
        profile.modified_by = user_id
        profile.updated_at  = now

    await db.commit()
    return await service_get_my_profile(db, user_id)


# =============================================================================
# PATCH /users/me/attorney-profile
# =============================================================================

async def service_update_my_attorney_profile(
    db:            AsyncSession,
    user_id:       uuid.UUID,
    bar_number:    Optional[str] = None,
    bar_state:     Optional[str] = None,
    law_firm_name: Optional[str] = None,
    bio:           Optional[str] = None,
     # ── ADDED: Screen 25 - Lawyer Dashboard ──────────────────────────────────
    monthly_billing_target_cents: Optional[int] = None,
) -> dict:
    """
    Partial update of attorney_profiles.
    Creates the row if it does not exist yet (idempotent).
    """
    attorney = await _get_or_create_attorney_profile(db, user_id)
    now      = datetime.now(timezone.utc)

    if bar_number    is not None: attorney.bar_number    = bar_number
    if bar_state     is not None: attorney.bar_state     = bar_state
    if law_firm_name is not None: attorney.law_firm_name = law_firm_name
    if bio           is not None: attorney.bio           = bio

    attorney.modified_by = user_id
    attorney.updated_at  = now

    await db.commit()
    return await service_get_my_profile(db, user_id)


# =============================================================================
# PATCH /users/me/avatar
# =============================================================================

_ALLOWED_EXTS   = {"jpg", "jpeg", "png", "webp"}
_MAX_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB


async def service_update_avatar(
    db:      AsyncSession,
    user_id: uuid.UUID,
    file:    UploadFile,
) -> dict:
    """
    Saves uploaded avatar and writes URL to user_profiles.profile_picture_url.
    Replace the file-write block with S3/GCS upload in production.
    """
    filename = file.filename or ""
    ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in _ALLOWED_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed: jpg, jpeg, png, webp.",
        )

    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be under 5MB.",
        )

    # ── Save file (replace with S3 in production) ─────────────────────────────
    upload_dir = "./uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    with open(f"{upload_dir}/{user_id}.{ext}", "wb") as f:
        f.write(content)

    avatar_url = f"/static/avatars/{user_id}.{ext}"

    # ── Persist URL ────────────────────────────────────────────────────────────
    profile                     = await _get_or_create_user_profile(db, user_id)
    profile.profile_picture_url = avatar_url
    profile.modified_by         = user_id
    profile.updated_at          = datetime.now(timezone.utc)

    await db.commit()
    return {"profile_picture_url": avatar_url, "message": "Avatar updated successfully."}


# =============================================================================
# DELETE /users/me/avatar
# =============================================================================

async def service_remove_avatar(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Sets profile_picture_url to None (does not delete file from disk)."""
    profile                     = await _get_or_create_user_profile(db, user_id)
    profile.profile_picture_url = None
    profile.modified_by         = user_id
    profile.updated_at          = datetime.now(timezone.utc)

    await db.commit()
    return {"profile_picture_url": None, "message": "Avatar removed successfully."}
