# src/app/services/employer/company_profile_service.py
from __future__ import annotations
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.visamodels import EmployerProfile
from app.schemas.hr.company_profile import CompanyProfileResponse, CompanyProfileUpdate
from app.services.employee import storage
from app.services.employee.services import db_create, db_update, db_get_by_field


async def _to_response(db: AsyncSession, profile: EmployerProfile) -> CompanyProfileResponse:
    resp = CompanyProfileResponse.model_validate(profile)
    # Same pattern as avatars — never expose the raw storage key/path directly.
    resp.logo_url = await storage.resolve_url(profile.logo_url) if profile.logo_url else None
    return resp


async def get_my_company_profile(
    db: AsyncSession,
    current_user_id: uuid.UUID,
) -> CompanyProfileResponse:
    """
    GET /employer/me/company-profile
    Returns the EmployerProfile row for the current HR user.
    Auto-creates an empty one if missing (company_name defaults to "" —
    frontend should treat an empty company_name as "needs setup").
    """
    profile = await db_get_by_field(db, EmployerProfile, "user_id", current_user_id)

    if not profile:
        profile = EmployerProfile(
            user_id      = current_user_id,
            company_name = "",
            created_by   = current_user_id,
        )
        profile = await db_create(db, profile)

    return await _to_response(db, profile)


async def update_my_company_profile(
    db:              AsyncSession,
    current_user_id: uuid.UUID,
    payload:         CompanyProfileUpdate,
) -> CompanyProfileResponse:
    """
    PATCH /employer/me/company-profile
    Partial update — only provided fields are written.
    """
    profile = await db_get_by_field(db, EmployerProfile, "user_id", current_user_id)
    if not profile:
        profile = EmployerProfile(
            user_id      = current_user_id,
            company_name = "",
            created_by   = current_user_id,
        )
        profile = await db_create(db, profile)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    update_data["modified_by"] = current_user_id
    updated = await db_update(db, EmployerProfile, profile.id, update_data)

    return await _to_response(db, updated)


async def upload_company_logo(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
) -> EmployerProfile:
    # 1. Validate extension
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp", "svg"}
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, jpeg, png, gif, webp, svg files are allowed",
        )

    # 2. Read file & size check
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB size limit.")

    # 3. Get profile (must exist — company profile is created on first GET)
    result  = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found.")

    # 4. Delete OLD logo (local disk or Space, whichever backend is active)
    if profile.logo_url:
        try:
            await storage.delete_file(profile.logo_url)
        except Exception:
            pass  # don't block upload if old file cleanup fails

    # 5. Save NEW file via storage service (S3/Spaces in staging, local in dev)
    safe_name      = os.path.basename(file.filename or f"logo.{ext}")
    storage_prefix = settings.STORAGE_PREFIX
    storage_path   = f"{storage_prefix}/employers/{user_id}/logo/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    # 6. Update DB — store the key, not a full URL
    await db_update(
        db,
        EmployerProfile,
        profile.id,
        {
            "logo_url":    storage_path,
            "modified_by": user_id,
        },
    )

    result = await db.execute(select(EmployerProfile).where(EmployerProfile.id == profile.id))
    return result.scalars().first()


async def remove_company_logo(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> CompanyProfileResponse:
    result  = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found.")

    if profile.logo_url:
        try:
            await storage.delete_file(profile.logo_url)
        except Exception:
            pass

    updated = await db_update(db, EmployerProfile, profile.id, {
        "logo_url":    None,
        "modified_by": user_id,
    })
    return await _to_response(db, updated)