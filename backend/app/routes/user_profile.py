# src/app/routers/user_profile_router.py
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user_profile import ProfilePictureResponse, UserProfileResponse, UserProfileUpdate
from app.services.user_profile_service import get_my_profile, update_my_profile, upload_profile_picture
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