# # src/app/services/user_profile_service.py
# from __future__ import annotations
# import os
# import uuid
# from datetime import datetime, timezone
# from typing import Optional

# from fastapi import HTTPException, UploadFile, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# from app.core.config import settings
# from app.models.visamodels import User, UserProfile
# from app.schemas.employee.user_profile import UserProfileResponse, UserProfileUpdate
# from app.services.employee import storage
# from app.services.employee.services import db_create, db_get_by_id, db_update, db_get_by_field



# # async def _to_profile_response(profile: UserProfile) -> UserProfileResponse:
# #     resp = UserProfileResponse.model_validate(profile)
# #     resp.profile_picture_url = await storage.resolve_url(profile.profile_picture_url)
# #     return resp

# async def _to_profile_response(db: AsyncSession, profile: UserProfile) -> UserProfileResponse:
#     user = await db_get_by_id(db, User, profile.user_id)
#     resp = UserProfileResponse.model_validate(profile)
#     resp.email = user.email if user else None
#     resp.profile_picture_url = "/api/v1/users/me/avatar" if profile.profile_picture_url else None
#     return resp

# async def get_my_profile(
#     db: AsyncSession,
#     current_user_id: uuid.UUID,
# ) -> UserProfileResponse:
#     """
#     GET /users/me/profile
#     Returns the profile for the current user.
#     Creates an empty one if it doesn't exist yet.
#     """
#     profile = await db_get_by_field(db, UserProfile, "user_id", current_user_id)

#     # Auto-create empty profile if missing
#     if not profile:
#         profile = UserProfile(
#             user_id    = current_user_id,
#             created_by = current_user_id,
#         )
#         profile = await db_create(db, profile)
#     return await _to_profile_response(db,profile)
#     # return UserProfileResponse.model_validate(profile)

# async def update_my_profile(
#     db:              AsyncSession,
#     current_user_id: uuid.UUID,
#     payload:         UserProfileUpdate,
# ) -> UserProfileResponse:
#     """
#     PATCH /users/me/profile
#     Updates profile fields. Also syncs phone + country_code to User table.
#     """
#     # ── 1. Get or create UserProfile ─────────────────────────────────────
#     profile = await db_get_by_field(db, UserProfile, "user_id", current_user_id)
#     if not profile:
#         profile = UserProfile(
#             user_id    = current_user_id,
#             created_by = current_user_id,
#         )
#         profile = await db_create(db, profile)

#     # ── 2. Build update dict from payload ─────────────────────────────────
#     update_data = payload.model_dump(exclude_none=True)
#     if not update_data:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="No fields provided for update.",
#         )

#     update_data["modified_by"] = current_user_id
#     updated = await db_update(db, UserProfile, profile.id, update_data)

#     # ── 3. Also sync phone + country_code to User table ───────────────────
#     user_update: dict = {}
#     if payload.phone_number is not None:
#         user_update["phone"] = payload.phone_number
#     if payload.country_code is not None:
#         user_update["country_code"] = payload.country_code

#     if payload.phone_number is not None:
#         user_update["modified_by"] = current_user_id

#     if user_update:
#         user = await db_get_by_id(db, User, current_user_id)
#         if user:
#             await db_update(db, User, user.id, user_update)

#     return await _to_profile_response(db,updated)
#     # return UserProfileResponse.model_validate(updated)

# async def upload_profile_picture(
#     db: AsyncSession,
#     user_id: uuid.UUID,
#     file: UploadFile,
# ):
#     # 1. Validate extension
#     allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
#     ext = (file.filename or "").rsplit(".", 1)[-1].lower()
#     if ext not in allowed_extensions:
#         raise HTTPException(
#             status_code=400,
#             detail="Only jpg, jpeg, png, gif, webp files are allowed",
#         )

#     # 2. Read file & size check
#     content = await file.read()
#     if len(content) > 5 * 1024 * 1024:
#         raise HTTPException(status_code=413, detail="File exceeds the 5 MB size limit.")

#     # 3. Get profile
#     result  = await db.execute(
#         select(UserProfile).where(UserProfile.user_id == user_id)
#     )
#     profile = result.scalars().first()
#     if not profile:
#         raise HTTPException(status_code=404, detail="User profile not found.")

#     # 4. ── Delete OLD file (local disk or Space, whichever backend is active) ──
#     if profile.profile_picture_url:
#         try:
#             await storage.delete_file(profile.profile_picture_url)
#         except Exception:
#             pass  # don't block upload if old file cleanup fails

#     # 5. Save NEW file via storage service (S3/Spaces in staging, local in dev)
#     safe_name    = os.path.basename(file.filename or f"avatar.{ext}")
#     storage_prefix = settings.STORAGE_PREFIX
#     storage_path = f"{storage_prefix}/users/{user_id}/profile_pictures/{safe_name}"
#     await storage.upload_file(
#         content,
#         storage_path,
#         file.content_type or "application/octet-stream",
#     )

#     # 6. Update DB — store the key, not a full URL
#     await db_update(
#         db,
#         UserProfile,
#         profile.id,
#         {
#             "profile_picture_url": storage_path,
#             "modified_by": user_id,
#         },
#     )

#     # 7. Return refreshed profile
#     result = await db.execute(
#         select(UserProfile).where(UserProfile.id == profile.id)
#     )
#     return result.scalars().first()




# async def remove_profile_picture(
#     db: AsyncSession,
#     user_id: uuid.UUID,
# ) -> UserProfileResponse:
#     result  = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
#     profile = result.scalars().first()
#     if not profile:
#         raise HTTPException(status_code=404, detail="User profile not found.")

#     if profile.profile_picture_url:
#         try:
#             await storage.delete_file(profile.profile_picture_url)
#         except Exception:
#             pass

#     updated = await db_update(db, UserProfile, profile.id, {
#         "profile_picture_url": None,
#         "modified_by": user_id,
#     })
#     return await _to_profile_response(db,updated)


# src/app/services/user_profile_service.py
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.visamodels import User, UserProfile
from app.schemas.employee.user_profile import UserProfileResponse, UserProfileUpdate
from app.services.employee import storage
from app.services.employee.services import db_create, db_get_by_id, db_update, db_get_by_field
from app.models.visamodels import UserEmail
from sqlalchemy import select

# FIXED: the avatar was always exposed at the same literal URL
# ("/api/v1/users/me/avatar"), and that route sets a 1-hour Cache-Control
# header. Since the URL never changed between uploads, the browser kept
# serving the OLD cached image for up to an hour after a new upload
# succeeded on the backend — this is why "uploading a different picture
# still shows the previous one." Appending a version query param derived
# from `updated_at` makes the URL itself change on every upload/removal,
# forcing the browser to fetch fresh bytes, while still letting it cache
# each individual version efficiently.
def _avatar_display_url(profile: UserProfile) -> Optional[str]:
    if not profile.profile_picture_url:
        return None
    version = int(profile.updated_at.timestamp())
    return f"/api/v1/users/me/avatar?v={version}"


# async def _to_profile_response(db: AsyncSession, profile: UserProfile) -> UserProfileResponse:
#     user = await db_get_by_id(db, User, profile.user_id)
#     resp = UserProfileResponse.model_validate(profile)
#     resp.email = user.email if user else None
#     resp.profile_picture_url = _avatar_display_url(profile)
#     return resp


async def _to_profile_response(db: AsyncSession, profile: UserProfile) -> UserProfileResponse:
    user = await db_get_by_id(db, User, profile.user_id)
    resp = UserProfileResponse.model_validate(profile)
    resp.email = user.email if user else None
    resp.profile_picture_url = _avatar_display_url(profile)

    # NEW — surface the backup/personal email (if any) so the frontend's
    # Backup Email section can render its current state correctly. Looks
    # for any non-primary row on this account, verified or not — an
    # unverified one still needs to show as "verification incomplete"
    # rather than silently vanishing.
    personal_row = await db.scalar(
        select(UserEmail)
        .where(UserEmail.user_id == profile.user_id, UserEmail.is_primary == False)
        .order_by(UserEmail.created_at.desc())
        .limit(1)
    )
    if personal_row:
        resp.personal_email = personal_row.email
        resp.personal_email_verified = personal_row.is_verified

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
    return await _to_profile_response(db, profile)


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

    return await _to_profile_response(db, updated)


async def upload_profile_picture(
    db: AsyncSession,
    user_id: uuid.UUID,
    file: UploadFile,
) -> UserProfile:
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
    safe_name      = os.path.basename(file.filename or f"avatar.{ext}")
    storage_prefix = settings.STORAGE_PREFIX
    storage_path   = f"{storage_prefix}/users/{user_id}/profile_pictures/{safe_name}"
    await storage.upload_file(
        content,
        storage_path,
        file.content_type or "application/octet-stream",
    )

    # 6. Update DB — store the key, not a full URL.
    #    FIXED: explicitly stamp updated_at here rather than relying on the
    #    column's onupdate= to fire through db_update's implementation —
    #    this guarantees the cache-busting version (see _avatar_display_url)
    #    always changes on a real upload, regardless of how db_update writes.
    await db_update(
        db,
        UserProfile,
        profile.id,
        {
            "profile_picture_url": storage_path,
            "modified_by":         user_id,
            "updated_at":          datetime.now(timezone.utc),
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
        "modified_by":         user_id,
        "updated_at":          datetime.now(timezone.utc),
    })
    return await _to_profile_response(db, updated)


# Exported so the router can build the same versioned URL directly off the
# ORM object returned by upload_profile_picture(), instead of duplicating
# the "/api/v1/users/me/avatar?v=..." construction logic in two places.
def get_avatar_display_url(profile: UserProfile) -> Optional[str]:
    return _avatar_display_url(profile)