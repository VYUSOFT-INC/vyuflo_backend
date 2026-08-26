# src/app/routers/attorney_profile_router.py
#
# Register in main.py:
#   from app.routers.attorney_profile_router import attorney_profile_router
#   app.include_router(attorney_profile_router, prefix="/api/v1", tags=["attorney-profile"])

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.attorney_profile import (
    AttorneyProfileResponse,
    AttorneyProfileUpdate,
    AttorneyPhotoResponse,
)
from app.services.attorney.attorney_profile_service import (
    get_my_attorney_profile,
    update_my_attorney_profile,
    upload_attorney_photo,
    remove_attorney_photo,
)
from app.services.employee.storage import resolve_url

attorney_profile_router = APIRouter()


@attorney_profile_router.get(
    "/attorney/me/profile",
    response_model=AttorneyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current attorney's professional profile",
    description="Returns AttorneyProfile for the logged-in attorney. Auto-creates if missing.",
)
async def api_get_my_attorney_profile(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> AttorneyProfileResponse:
    return await get_my_attorney_profile(db, current_user.user_id)


@attorney_profile_router.patch(
    "/attorney/me/profile",
    response_model=AttorneyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current attorney's professional profile",
    description="Partial update — only provided fields are written.",
)
async def api_update_my_attorney_profile(
    payload:      AttorneyProfileUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> AttorneyProfileResponse:
    result = await update_my_attorney_profile(db, current_user.user_id, payload)
    await db.commit()
    return result


@attorney_profile_router.post(
    "/attorney/me/profile/upload-photo",
    response_model=AttorneyPhotoResponse,
    status_code=200,
    summary="Upload attorney profile photo",
)
async def api_upload_attorney_photo(
    file:         UploadFile = File(...),
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> AttorneyPhotoResponse:
    profile = await upload_attorney_photo(db, current_user.user_id, file)
    await db.commit()
    resolved_url = await resolve_url(profile.profile_photo_url)
    return AttorneyPhotoResponse(profile_photo_url=resolved_url)


@attorney_profile_router.delete(
    "/attorney/me/profile/photo",
    response_model=AttorneyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove attorney profile photo",
)
async def api_remove_attorney_photo(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> AttorneyProfileResponse:
    result = await remove_attorney_photo(db, current_user.user_id)
    await db.commit()
    return result