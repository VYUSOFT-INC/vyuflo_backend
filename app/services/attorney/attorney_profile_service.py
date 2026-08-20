# src/app/services/attorney/attorney_profile_service.py
from __future__ import annotations
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.visamodels import AttorneyProfile
from app.schemas.attorney.attorney_profile import AttorneyProfileResponse, AttorneyProfileUpdate
from app.services.employee import storage
from app.services.employee.services import db_create, db_update, db_get_by_field


async def _to_response(db: AsyncSession, profile: AttorneyProfile) -> AttorneyProfileResponse:
    resp = AttorneyProfileResponse.model_validate(profile)
    resp.profile_photo_url = await storage.resolve_url(profile.profile_photo_url) if profile.profile_photo_url else None
    return resp


async def get_my_attorney_profile(
    db: AsyncSession,
    current_user_id: uuid.UUID,
) -> AttorneyProfileResponse:
    """
    GET /attorney/me/profile
    Returns the AttorneyProfile row for the current attorney user.
    Auto-creates an empty one if missing.
    """
    profile = await db_get_by_field(db, AttorneyProfile, "user_id", current_user_id)

    if not profile:
        profile = AttorneyProfile(
            user_id    = current_user_id,
            created_by = current_user_id,
        )
        profile = await db_create(db, profile)

    return await _to_response(db, profile)


async def update_my_attorney_profile(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    payload:         AttorneyProfileUpdate,
) -> AttorneyProfileResponse:
    """
    PATCH /attorney/me/profile
    Partial update — only provided fields are written.
    """
    profile = await db_get_by_field(db, AttorneyProfile, "user_id", current_user_id)
    if not profile:
        profile = AttorneyProfile(
            user_id    = current_user_id,
            created_by = current_user_id,
        )
        profile = await db_create(db, profile)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    update_data["modified_by"] = current_user_id
    updated = await db_update(db, AttorneyProfile, profile.id, update_data)

    return await _to_response(db, updated)


async def upload_attorney_photo(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
) -> AttorneyProfile:
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, jpeg, png, gif, webp files are allowed",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB size limit.")

    result  = await db.execute(select(AttorneyProfile).where(AttorneyProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Attorney profile not found.")

    if profile.profile_photo_url:
        try:
            await storage.delete_file(profile.profile_photo_url)
        except Exception:
            pass

    safe_name      = os.path.basename(file.filename or f"photo.{ext}")
    storage_prefix = settings.STORAGE_PREFIX
    storage_path   = f"{storage_prefix}/attorneys/{user_id}/profile_photos/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    await db_update(
        db,
        AttorneyProfile,
        profile.id,
        {
            "profile_photo_url": storage_path,
            "modified_by":       user_id,
        },
    )

    result = await db.execute(select(AttorneyProfile).where(AttorneyProfile.id == profile.id))
    return result.scalars().first()


async def remove_attorney_photo(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> AttorneyProfileResponse:
    result  = await db.execute(select(AttorneyProfile).where(AttorneyProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Attorney profile not found.")

    if profile.profile_photo_url:
        try:
            await storage.delete_file(profile.profile_photo_url)
        except Exception:
            pass

    updated = await db_update(db, AttorneyProfile, profile.id, {
        "profile_photo_url": None,
        "modified_by":       user_id,
    })
    return await _to_response(db, updated)