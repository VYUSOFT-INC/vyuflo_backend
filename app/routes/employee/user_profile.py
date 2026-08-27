# # src/app/routers/user_profile_router.py
# from typing import Optional

# from fastapi import APIRouter, Cookie, Depends, File, UploadFile, status,Response
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# from sqlalchemy import update
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.database import get_db
# from app.core.dependencies import get_current_user
# from app.core.exceptions import NotFoundException, UnauthorizedException
# from app.core.security import decode_token
# from app.models.visamodels import UserProfile
# from app.schemas.employee.user_profile import ProfilePictureResponse, UserProfileResponse, UserProfileUpdate
# from app.services.employee import storage
# from app.services.employee.services import db_get_by_field, db_update
# from app.services.employee.user_profile_service import get_my_profile, remove_profile_picture, update_my_profile, upload_profile_picture
# import uuid


# user_profile_router = APIRouter()


# @user_profile_router.get(
#     "/users/me/profile",
#     response_model=UserProfileResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Get current user profile",
#     description="Returns profile for the logged-in user. Auto-creates if missing.",
# )
# async def api_get_my_profile(
#     db:              AsyncSession = Depends(get_db),
#     current_user_id: uuid.UUID   = Depends(get_current_user),
# ) -> UserProfileResponse:
#     return await get_my_profile(db, current_user_id.user_id)

# @user_profile_router.get("/users/me/avatar")
# async def get_my_avatar(
#     response: Response,
#     db: AsyncSession = Depends(get_db),
#     avatar_session: Optional[str] = Cookie(None),
# ):
#     if not avatar_session:
#         raise UnauthorizedException("Not authenticated")

#     try:
#         payload = decode_token(avatar_session)
#         user_id = payload.get("sub")
#         if not user_id:
#             raise UnauthorizedException("Invalid session")
#     except Exception:
#         raise UnauthorizedException("Invalid or expired session")

#     profile = await db_get_by_field(db, UserProfile, "user_id", uuid.UUID(user_id))
#     if not profile or not profile.profile_picture_url:
#         raise NotFoundException("No profile picture set.")

#     content, content_type = await storage.get_file_bytes(profile.profile_picture_url)
#     response.headers["Cache-Control"] = "private, max-age=3600"
#     return StreamingResponse(iter([content]), media_type=content_type)


# @user_profile_router.patch(
#     "/users/me/profile",
#     response_model=UserProfileResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Update current user profile",
#     description="Partial update — only provided fields are written.",
# )
# async def api_update_my_profile(
#     payload:         UserProfileUpdate,
#     db:              AsyncSession = Depends(get_db),
#     current_user_id: uuid.UUID   = Depends(get_current_user),
# ) -> UserProfileResponse:
#     return await update_my_profile(db, current_user_id.user_id, payload)


# @user_profile_router.post(
#     "/users/me/upload-picture",
#     response_model=ProfilePictureResponse,
#     status_code=200,
# )
# async def api_upload_profile_picture(
#     file: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     profile = await upload_profile_picture(
#         db,
#         current_user.user_id,
#         file,
#     )

#     return ProfilePictureResponse(
#         profile_picture_url=profile.profile_picture_url
#     )

# from typing import Literal


# TourRole = Literal["employee", "hr", "attorney", "admin"]
 
# TOUR_FIELD_MAP: dict[str, str] = {
#     "employee": "tour_employee_seen",
#     "hr":       "tour_hr_seen",
#     "attorney": "tour_attorney_seen",
#     "admin":    "tour_admin_seen",
# }
 
 
# class TourSeenRequest(BaseModel):
#     role: TourRole
 
 
# @user_profile_router.patch(
#     "/users/me/tour-seen",
#     status_code=status.HTTP_200_OK,
#     summary="Mark dashboard tour as seen",
# )
# async def api_mark_tour_seen(
#     body:         TourSeenRequest,
#     db:           AsyncSession = Depends(get_db),
#     current_user               = Depends(get_current_user),
# ) -> dict:
#     field = TOUR_FIELD_MAP[body.role]
#     await db.execute(
#         update(UserProfile)
#         .where(UserProfile.user_id == current_user.user_id)
#         .values(**{field: True})
#     )
#     await db.commit()
#     return {"ok": True}



# from app.services.employee.storage import resolve_url

# @user_profile_router.post(
#     "/users/me/upload-picture",
#     response_model=ProfilePictureResponse,
#     status_code=200,
# )
# async def api_upload_profile_picture(
#     file: UploadFile = File(...),
#     db: AsyncSession = Depends(get_db),
#     current_user = Depends(get_current_user),
# ):
#     profile = await upload_profile_picture(db, current_user.user_id, file)
#     resolved_url = await resolve_url(profile.profile_picture_url)
#     return ProfilePictureResponse(profile_picture_url=resolved_url)

# @user_profile_router.delete(
#     "/users/me/profile-picture",
#     response_model=UserProfileResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def api_remove_profile_picture(
#     db:              AsyncSession = Depends(get_db),
#     current_user_id: uuid.UUID   = Depends(get_current_user),
# ) -> UserProfileResponse:
#     return await remove_profile_picture(db, current_user_id.user_id)


# src/app/routers/user_profile_router.py
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, UploadFile, status, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.security import decode_token
from app.models.visamodels import UserProfile
from app.schemas.employee.user_profile import ProfilePictureResponse, UserProfileResponse, UserProfileUpdate
from app.services.employee import storage
from app.services.employee.services import db_get_by_field, db_update
from app.services.employee.user_profile_service import (
    get_my_profile,
    remove_profile_picture,
    update_my_profile,
    upload_profile_picture,
    get_avatar_display_url,
)
import uuid


user_profile_router = APIRouter()


@user_profile_router.get(
    "/users/me/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns profile for the logged-in user. Auto-creates if missing.",
)
async def api_get_my_profile(
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID   = Depends(get_current_user),
) -> UserProfileResponse:
    return await get_my_profile(db, current_user_id.user_id)


@user_profile_router.get("/users/me/avatar")
async def get_my_avatar(
    response: Response,
    db: AsyncSession = Depends(get_db),
    avatar_session: Optional[str] = Cookie(None),
):
    if not avatar_session:
        raise UnauthorizedException("Not authenticated")

    try:
        payload = decode_token(avatar_session)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid session")
    except Exception:
        raise UnauthorizedException("Invalid or expired session")

    profile = await db_get_by_field(db, UserProfile, "user_id", uuid.UUID(user_id))
    if not profile or not profile.profile_picture_url:
        raise NotFoundException("No profile picture set.")

    content, content_type = await storage.get_file_bytes(profile.profile_picture_url)
    # NOTE: this max-age is safe now that the URL includes a ?v=<updated_at>
    # cache-buster (see get_avatar_display_url) — the browser will cache
    # each *version* of the avatar, but a new upload produces a new URL,
    # so stale images are no longer served after a re-upload.
    response.headers["Cache-Control"] = "private, max-age=3600"
    return StreamingResponse(iter([content]), media_type=content_type)


@user_profile_router.patch(
    "/users/me/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Partial update — only provided fields are written.",
)
async def api_update_my_profile(
    payload:         UserProfileUpdate,
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID   = Depends(get_current_user),
) -> UserProfileResponse:
    return await update_my_profile(db, current_user_id.user_id, payload)


# FIXED: this endpoint was previously defined TWICE in this file with the
# same path/method. FastAPI/Starlette only ever matches the FIRST route
# registered for a given path+method, so the second definition (which
# correctly resolved the storage URL) was dead code that never ran. The
# one that *did* run returned the raw, unresolved storage key as
# `profile_picture_url` — not a usable image URL — and had nothing to do
# with the actual "old picture shown after upload" caching bug, but was
# worth cleaning up since it silently masked the working implementation.
#
# This single remaining version now returns the same versioned
# "/api/v1/users/me/avatar?v=..." URL that GET /users/me/profile returns,
# so both endpoints are consistent and the frontend gets a fresh,
# cache-busted URL immediately after upload.
@user_profile_router.post(
    "/users/me/upload-picture",
    response_model=ProfilePictureResponse,
    status_code=200,
)
async def api_upload_profile_picture(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    profile = await upload_profile_picture(db, current_user.user_id, file)
    return ProfilePictureResponse(profile_picture_url=get_avatar_display_url(profile))


from typing import Literal


TourRole = Literal["employee", "hr", "attorney", "admin"]

TOUR_FIELD_MAP: dict[str, str] = {
    "employee": "tour_employee_seen",
    "hr":       "tour_hr_seen",
    "attorney": "tour_attorney_seen",
    "admin":    "tour_admin_seen",
}


class TourSeenRequest(BaseModel):
    role: TourRole


@user_profile_router.patch(
    "/users/me/tour-seen",
    status_code=status.HTTP_200_OK,
    summary="Mark dashboard tour as seen",
)
async def api_mark_tour_seen(
    body:         TourSeenRequest,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> dict:
    field = TOUR_FIELD_MAP[body.role]
    await db.execute(
        update(UserProfile)
        .where(UserProfile.user_id == current_user.user_id)
        .values(**{field: True})
    )
    await db.commit()
    return {"ok": True}


@user_profile_router.delete(
    "/users/me/profile-picture",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def api_remove_profile_picture(
    db:              AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID   = Depends(get_current_user),
) -> UserProfileResponse:
    return await remove_profile_picture(db, current_user_id.user_id)


# Add to user_profile_router.py, near get_my_avatar

@user_profile_router.get("/users/{user_id}/avatar")
async def get_user_avatar(
    user_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    avatar_session: Optional[str] = Cookie(None),
):
    """
    Streams another user's profile picture by ID — for rendering avatars in
    <img> tags (rosters, participant lists, pickers) where the requester
    isn't necessarily viewing their OWN avatar.

    Uses the same avatar_session cookie as /users/me/avatar rather than
    Depends(get_current_user), because <img src="..."> requests are plain
    browser GETs that carry cookies automatically but can't attach the
    Authorization: Bearer header the rest of the app's axios calls use.
    The cookie here just confirms SOMEONE is authenticated; the target
    photo is whichever user_id is in the path, not the cookie's subject.

    NOTE: currently no relationship check — any authenticated user can view
    any other user's avatar (e.g. HR viewing an attorney they haven't
    engaged, or vice versa). Flag if you want this scoped to only people
    who share a case/company link with the target user.
    """
    if not avatar_session:
        raise UnauthorizedException("Not authenticated")

    try:
        decode_token(avatar_session)  # just confirms a valid session exists
    except Exception:
        raise UnauthorizedException("Invalid or expired session")

    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile or not profile.profile_picture_url:
        raise NotFoundException("No profile picture set.")

    content, content_type = await storage.get_file_bytes(profile.profile_picture_url)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return StreamingResponse(iter([content]), media_type=content_type)