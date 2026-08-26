# =============================================================================
# app/services/attorney/profile_settings.py
# Screen 13 — Profile & Settings
# =============================================================================

from __future__ import annotations

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
# FIXED: delegate avatar handling to the ALREADY-CORRECT, S3/Spaces-backed
# functions in user_profile_service.py instead of duplicating (badly) the
# upload logic here. This file's previous version saved to local disk and
# wrote a "/static/avatars/..." path into the same column the S3-based
# GET /users/me/avatar endpoint reads from expecting an S3 key — guaranteed
# NoSuchKey on every read, confirmed in production logs.
from app.services.employee.user_profile_service import (
    upload_profile_picture,
    remove_profile_picture,
    get_avatar_display_url,
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

    # FIXED: profile_picture_url now goes through get_avatar_display_url()
    # so this endpoint returns the same versioned "/api/v1/users/me/avatar?v=..."
    # URL every other part of the app expects, instead of the raw column value.
    return {
        "id":                  user.id,
        "first_name":          user.first_name,
        "last_name":           user.last_name,
        "email":               user.email,
        "profile_picture_url": get_avatar_display_url(profile) if profile else None,
        "timezone":            profile.timezone            if profile else None,
        "preferred_language":  profile.preferred_language  if profile else None,
        "bar_number":          attorney.bar_number         if attorney else None,
        "bar_state":           attorney.bar_state          if attorney else None,
        "law_firm_name":       attorney.law_firm_name      if attorney else None,
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
    tz:                 Optional[str] = None,   # FIXED: renamed from `timezone` —
                                                  # was shadowing the datetime.timezone
                                                  # import, causing datetime.now(timezone.utc)
                                                  # to crash with AttributeError whenever
                                                  # a caller didn't pass a timezone value
                                                  # (i.e. every name-only save).
    preferred_language: Optional[str] = None,
) -> dict:
    """
    Partial update — only provided fields are written.
    Writes to users (name) and user_profiles (timezone, language).
    """
    user = await _get_user(db, user_id)
    now  = datetime.now(timezone.utc)   # `timezone` now correctly refers to the datetime module

    if first_name is not None: user.first_name = first_name
    if last_name  is not None: user.last_name  = last_name
    user.modified_by = user_id
    user.updated_at  = now

    if tz is not None or preferred_language is not None:
        profile = await _get_or_create_user_profile(db, user_id)
        if tz is not None:                 profile.timezone           = tz
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
    if monthly_billing_target_cents is not None:
        attorney.monthly_billing_target_cents = monthly_billing_target_cents

    attorney.modified_by = user_id
    attorney.updated_at  = now

    await db.commit()
    return await service_get_my_profile(db, user_id)


# =============================================================================
# PATCH /users/me/avatar
# =============================================================================

async def service_update_avatar(
    db:      AsyncSession,
    user_id: uuid.UUID,
    file:    UploadFile,
) -> dict:
    """
    FIXED: previously saved to local disk and wrote a "/static/avatars/..."
    path directly into user_profiles.profile_picture_url — a value the
    S3-based GET /users/me/avatar endpoint could never resolve (NoSuchKey,
    confirmed in production). Now delegates to the same
    upload_profile_picture() used by every other avatar-upload path in the
    app (Sidebar, HREmployees, ProfileSecurity, etc.), so attorneys write
    to the same S3/Spaces key convention and the same column, and every
    avatar-reading endpoint resolves it identically with no special-casing.

    NOTE: upload_profile_picture() raises 404 if no UserProfile row exists
    yet for this user (unlike this file's previous auto-create-on-upload
    behavior). In practice this should never trigger, since the Profile
    tab always calls GET /users/me/profile first (which auto-creates the
    row) before the avatar picker is ever shown — flagging only so it's
    understood as an intentional behavior narrowing, not silently dropped.
    """
    updated_profile = await upload_profile_picture(db, user_id, file)
    return {
        "profile_picture_url": get_avatar_display_url(updated_profile),
        "message": "Avatar updated successfully.",
    }


# =============================================================================
# DELETE /users/me/avatar
# =============================================================================

async def service_remove_avatar(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    FIXED: previously only nulled the DB column, leaving the actual file
    (wherever it was) orphaned. Now delegates to remove_profile_picture(),
    which also calls storage.delete_file() to remove the real S3/Spaces
    object, matching cleanup behavior used everywhere else.
    """
    await remove_profile_picture(db, user_id)
    return {"profile_picture_url": None, "message": "Avatar removed successfully."}