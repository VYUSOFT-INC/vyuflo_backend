# src/app/routers/user_profile_router.py
from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import UserProfile
from app.schemas.employee.user_profile import ProfilePictureResponse, UserProfileResponse, UserProfileUpdate
from app.services.employee.services import db_update
from app.services.employee.user_profile_service import get_my_profile, remove_profile_picture, update_my_profile, upload_profile_picture
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
    profile = await upload_profile_picture(
        db,
        current_user.user_id,
        file,
    )

    return ProfilePictureResponse(
        profile_picture_url=profile.profile_picture_url
    )

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



from app.services.employee.storage import resolve_url

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
    resolved_url = await resolve_url(profile.profile_picture_url)
    return ProfilePictureResponse(profile_picture_url=resolved_url)

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