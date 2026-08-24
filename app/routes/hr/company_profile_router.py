# src/app/routers/company_profile_router.py
#
# Register in main.py:
#   from app.routers.company_profile_router import company_profile_router
#   app.include_router(company_profile_router, prefix="/api/v1", tags=["company-profile"])

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.hr.company_profile import (
    CompanyProfileResponse,
    CompanyProfileUpdate,
    CompanyLogoResponse,
)
from app.services.hr.company_profile_service import (
    get_my_company_profile,
    update_my_company_profile,
    upload_company_logo,
    remove_company_logo,
)
from app.services.employee.storage import resolve_url

company_profile_router = APIRouter()


@company_profile_router.get(
    "/employer/me/company-profile",
    response_model=CompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current HR user's company profile",
    description="Returns EmployerProfile for the logged-in HR user. Auto-creates if missing.",
)
async def api_get_my_company_profile(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> CompanyProfileResponse:
    return await get_my_company_profile(db, current_user.user_id)


@company_profile_router.patch(
    "/employer/me/company-profile",
    response_model=CompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current HR user's company profile",
    description="Partial update — only provided fields are written.",
)
async def api_update_my_company_profile(
    payload:      CompanyProfileUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> CompanyProfileResponse:
    result = await update_my_company_profile(db, current_user.user_id, payload)
    await db.commit()
    return result


@company_profile_router.post(
    "/employer/me/company-profile/upload-logo",
    response_model=CompanyLogoResponse,
    status_code=200,
    summary="Upload company logo",
)
async def api_upload_company_logo(
    file:         UploadFile = File(...),
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> CompanyLogoResponse:
    profile = await upload_company_logo(db, current_user.user_id, file)
    await db.commit()
    resolved_url = await resolve_url(profile.logo_url)
    return CompanyLogoResponse(logo_url=resolved_url)


@company_profile_router.delete(
    "/employer/me/company-profile/logo",
    response_model=CompanyProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove company logo",
)
async def api_remove_company_logo(
    db:           AsyncSession = Depends(get_db),
    current_user               = Depends(get_current_user),
) -> CompanyProfileResponse:
    result = await remove_company_logo(db, current_user.user_id)
    await db.commit()
    return result