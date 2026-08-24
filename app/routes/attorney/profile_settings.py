# =============================================================================
# app/routers/profile_settings_router.py
# Screen 13 — Profile & Settings
#
# MOUNT: app.include_router(profile_settings_router, prefix="/api/v1/attorney", tags=["Profile Settings"])
# (Moved from /api/v1 to /api/v1/attorney — the old mount collided with
# user_profile_router's GET /api/v1/users/me/profile, same method+path,
# registered earlier in main.py, which silently shadowed this router's
# aggregated response for every single request. Full paths are now:
#   GET    /api/v1/attorney/users/me/profile
#   PATCH  /api/v1/attorney/users/me/profile
#   PATCH  /api/v1/attorney/users/me/attorney-profile
#   PATCH  /api/v1/attorney/users/me/avatar
#   DELETE /api/v1/attorney/users/me/avatar
#
# Section B — Notification Preferences:
#   REUSED AS-IS — no new endpoints here.
#   Frontend calls existing:
#     GET  /api/v1/notifications/preferences
#     PATCH /api/v1/notifications/preferences
#   Option A column mapping:
#     "Pending Reviews"  In-App  → notify_document_updates
#     "Pending Reviews"  Email   → email_enabled
#     "Action Required"  In-App  → notify_case_updates
#     "Action Required"  Email   → email_enabled
#     "New Messages"     In-App  → push_enabled
#     "New Messages"     Email   → email_enabled
#
# Section C — AI Extraction Settings:
#   Skipped — already done by colleague.
# =============================================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.profile_settings import (
    AttorneyProfileUpdateRequest,
    AvatarUpdateResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.attorney.profile_settings_service import (
    service_get_my_profile,
    service_remove_avatar,
    service_update_avatar,
    service_update_my_attorney_profile,
    service_update_my_profile,
)

profile_settings_router = APIRouter()


# =============================================================================
# SECTION A — PROFILE INFORMATION
# =============================================================================

@profile_settings_router.get(
    "/users/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get own profile — Screen 13 Profile Information",
    description=(
        "Returns aggregated profile from users + user_profiles + attorney_profiles. "
        "Includes: first_name, last_name, email, avatar URL, timezone, "
        "bar_number (attorney only), role label."
    ),
)
async def api_get_my_profile(
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ProfileResponse:
    data = await service_get_my_profile(db, current_user.user_id)
    return ProfileResponse(**data)


@profile_settings_router.patch(
    "/users/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update own profile — Screen 13 'Save Changes' button",
    description=(
        "Partial update — only provided fields are written. "
        "Writes first_name, last_name to users table. "
        "Writes timezone, preferred_language to user_profiles table."
    ),
)
async def api_update_my_profile(
    payload:      ProfileUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ProfileResponse:
    data = await service_update_my_profile(
        db                 = db,
        user_id            = current_user.user_id,
        first_name         = payload.first_name,
        last_name          = payload.last_name,
        tz                 = payload.timezone,   # FIXED: matches renamed `tz` param
        preferred_language = payload.preferred_language,
    )
    return ProfileResponse(**data)


@profile_settings_router.patch(
    "/users/me/attorney-profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update attorney credentials — Screen 13 Bar Association ID",
    description=(
        "Updates attorney_profiles: bar_number, bar_state, law_firm_name, bio. "
        "Only provided fields are written. "
        "Creates attorney_profiles row automatically if missing."
    ),
)
async def api_update_attorney_profile(
    payload:      AttorneyProfileUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> ProfileResponse:
    data = await service_update_my_attorney_profile(
        db            = db,
        user_id       = current_user.user_id,
        bar_number    = payload.bar_number,
        bar_state     = payload.bar_state,
        law_firm_name = payload.law_firm_name,
        bio           = payload.bio,
        monthly_billing_target_cents = payload.monthly_billing_target_cents,
    )
    return ProfileResponse(**data)


@profile_settings_router.patch(
    "/users/me/avatar",
    response_model=AvatarUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload avatar — Screen 13 'Change Avatar' button",
    description=(
        "Multipart/form-data. Field name: file. "
        "Allowed: jpg, jpeg, png, webp. Max: 5MB. "
        "Returns new profile_picture_url. "
        "Now delegates to the shared S3/Spaces-backed avatar pipeline "
        "(user_profile_service.upload_profile_picture) — see profile_settings_service.py."
    ),
)
async def api_update_avatar(
    file:         UploadFile  = File(...),
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> AvatarUpdateResponse:
    data = await service_update_avatar(db, current_user.user_id, file)
    return AvatarUpdateResponse(**data)


@profile_settings_router.delete(
    "/users/me/avatar",
    response_model=AvatarUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove avatar — Screen 13 'Remove' link",
    description="Sets profile_picture_url to null and deletes the underlying S3/Spaces object.",
)
async def api_remove_avatar(
    db:           AsyncSession = Depends(get_db),
    current_user              = Depends(get_current_user),
) -> AvatarUpdateResponse:
    data = await service_remove_avatar(db, current_user.user_id)
    return AvatarUpdateResponse(**data)