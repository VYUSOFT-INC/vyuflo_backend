# src/app/services/user_profile_service.py
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.visamodels import User, UserProfile
from app.schemas.employee.user_profile import UserProfileResponse, UserProfileUpdate
from app.services.employee import storage
from app.services.employee.services import db_create, db_get_by_id, db_update, db_get_by_field



async def _to_profile_response(profile: UserProfile) -> UserProfileResponse:
    resp = UserProfileResponse.model_validate(profile)
    resp.profile_picture_url = await storage.resolve_url(profile.profile_picture_url)
    return resp

async def get_my_profile(
    db: AsyncSession,
    current_user_id: uuid.UUID,
) -> UserProfileResponse:
    """
    GET /users/me/profile
    Returns the profile for the current user.
    Creates an empty one if it doesn't exist yet.
    """
    profile = await db_get_by_field(db, UserProfile, "user_id", current_user_id)

    # Auto-create empty profile if missing
    if not profile:
        profile = UserProfile(
            user_id    = current_user_id,
            created_by = current_user_id,
        )
        profile = await db_create(db, profile)
    return await _to_profile_response(profile)
    # return UserProfileResponse.model_validate(profile)

async def update_my_profile(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    payload:         UserProfileUpdate,
) -> UserProfileResponse:
    """
    PATCH /users/me/profile
    Updates profile fields. Also syncs phone + country_code to User table.
    """
    # ── 1. Get or create UserProfile ─────────────────────────────────────
    profile = await db_get_by_field(db, UserProfile, "user_id", current_user_id)
    if not profile:
        profile = UserProfile(
            user_id    = current_user_id,
            created_by = current_user_id,
        )
        profile = await db_create(db, profile)

    # ── 2. Build update dict from payload ─────────────────────────────────
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    update_data["modified_by"] = current_user_id
    updated = await db_update(db, UserProfile, profile.id, update_data)

    # ── 3. Also sync phone + country_code to User table ───────────────────
    user_update: dict = {}
    if payload.phone_number is not None:
        user_update["phone"] = payload.phone_number
    if payload.country_code is not None:
        user_update["country_code"] = payload.country_code

    if payload.phone_number is not None:
        user_update["modified_by"] = current_user_id

    if user_update:
        user = await db_get_by_id(db, User, current_user_id)
        if user:
            await db_update(db, User, user.id, user_update)

    return await _to_profile_response(updated)
    # return UserProfileResponse.model_validate(updated)

async def upload_profile_picture(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
):
    # 1. Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, jpeg, png, gif, webp files are allowed",
        )

    # 2. Read file & size check
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB size limit.")

    # 3. Get profile
    result  = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found.")

    # 4. ── Delete OLD file (local disk or Space, whichever backend is active) ──
    if profile.profile_picture_url:
        try:
            await storage.delete_file(profile.profile_picture_url)
        except Exception:
            pass  # don't block upload if old file cleanup fails

    # 5. Save NEW file via storage service (S3/Spaces in staging, local in dev)
    safe_name    = os.path.basename(file.filename or f"avatar.{ext}")
    storage_path = f"users/{user_id}/profile_pictures/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    # 6. Update DB — store the key, not a full URL
    await db_update(
        db,
        UserProfile,
        profile.id,
        {
            "profile_picture_url": storage_path,
            "modified_by": user_id,
        },
    )

    # 7. Return refreshed profile
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == profile.id)
    )
    return result.scalars().first()




async def remove_profile_picture(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserProfileResponse:
    result  = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found.")

    if profile.profile_picture_url:
        try:
            await storage.delete_file(profile.profile_picture_url)
        except Exception:
            pass

    updated = await db_update(db, UserProfile, profile.id, {
        "profile_picture_url": None,
        "modified_by": user_id,
    })
    return await _to_profile_response(updated)