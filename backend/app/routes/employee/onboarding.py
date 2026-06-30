
"""
Onboarding routes — /api/v1/onboarding/*

Screens covered:
  03  Email Verify          POST /verify-email
  03  Resend OTP            POST /resend-otp
  03  Status                GET  /status
  04  Select Role           POST /role
  05  Employee Profile      POST /profile          (Employee/Student — unchanged)
  05  Attorney Profile      POST /attorney-profile (NEW)
  05  HR Profile            POST /hr-profile       (NEW)
  05  Admin Profile         POST /admin-profile    (NEW)
  06  Review & Complete     POST /complete
"""
from fastapi import APIRouter, Response

from app.core.dependencies import Current_User, DBSession
from app.routes.employee.auth import _set_refresh_cookie, _set_ui_cookie
from app.schemas.employee.auth import TokenResponse
from app.schemas.employee.onboarding import (
    AttorneyProfileRequest,
    HRProfileRequest,
    AdminProfileRequest,
    OnboardingCompleteRequest,
    OnboardingProfileRequest,
    OnboardingRoleRequest,
    OnboardingStatusResponse,
    VerifyEmailRequest,
)
from app.services.employee.onboarding_services import (
    service_complete_onboarding,
    service_get_onboarding_status,
    service_resend_otp,
    service_save_attorney_profile,
    service_save_hr_profile,
    service_save_admin_profile,
    service_save_profile,
    service_set_role,
    service_verify_email,
)

router = APIRouter()


# ── GET /onboarding/status ────────────────────────────────────────────────────

@router.get("/status", response_model=OnboardingStatusResponse, status_code=200)
async def get_onboarding_status(
    db: DBSession,
    current_user: Current_User,
):
    return await service_get_onboarding_status(
        db,
        user_id = current_user.user_id,
        roles   = current_user.roles,
    )


# ── POST /onboarding/verify-email ─────────────────────────────────────────────

@router.post("/verify-email", response_model=TokenResponse, status_code=200)
async def verify_email(
    body: VerifyEmailRequest,
    db: DBSession,
    current_user: Current_User,
    response: Response,
):
    result = await service_verify_email(
        db,
        user_id = current_user.user_id,
        otp     = body.otp,
    )
    _set_refresh_cookie(response, result["refresh_token"])
    _set_ui_cookie(
        response,
        user=result["user"],
        profile=result.get("profile"),
        theme_color=result.get("theme_color"),
        roles=result["roles"],
    )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        roles=result["roles"],
        profile=result.get("profile"),
        theme_color=result.get("theme_color"),
        onboarding_step=result["onboarding_step"],
        user=result["user"],
    )


# ── POST /onboarding/resend-otp ───────────────────────────────────────────────

@router.post("/resend-otp", status_code=200)
async def resend_otp(
    db: DBSession,
    current_user: Current_User,
):
    await service_resend_otp(db, user_id=current_user.user_id)
    return {"message": "Verification email sent. Please check your inbox."}


# ── POST /onboarding/role ─────────────────────────────────────────────────────

@router.post("/role", status_code=200)
async def set_role(
    body: OnboardingRoleRequest,
    db: DBSession,
    current_user: Current_User,
):
    return await service_set_role(
        db,
        user_id = current_user.user_id,
        role    = body.role,
    )


# ── POST /onboarding/profile  (Employee/Student — unchanged) ──────────────────

@router.post("/profile", status_code=200)
async def save_profile(
    body: OnboardingProfileRequest,
    db: DBSession,
    current_user: Current_User,
):
    return await service_save_profile(
        db,
        user_id              = current_user.user_id,
        full_legal_name      = body.full_legal_name,
        nationality          = body.nationality,
        visa_targets         = body.visa_targets,
        date_of_birth        = body.date_of_birth,
        gender               = body.gender,
        country_of_residence = body.country_of_residence,
        primary_visa         = body.primary_visa,
        timezone             = body.timezone,
        preferred_language   = body.preferred_language,
        theme_color          = body.theme_color
    )


# ── POST /onboarding/attorney-profile  (NEW) ──────────────────────────────────

@router.post("/attorney-profile", status_code=200)
async def save_attorney_profile(
    body: AttorneyProfileRequest,
    db: DBSession,
    current_user: Current_User,
):
    """
    Step 2 for Attorney/Lawyer.
    Saves personal fields to user_profiles +
    professional credentials to attorney_profiles (creates row if missing).
    """
    return await service_save_attorney_profile(
        db,
        user_id              = current_user.user_id,
        full_legal_name      = body.full_legal_name,
        date_of_birth        = body.date_of_birth,
        gender               = body.gender,
        nationality          = body.nationality,
        country_of_residence = body.country_of_residence,
        timezone             = body.timezone,
        preferred_language   = body.preferred_language,
        bar_number           = body.bar_number,
        bar_state            = body.bar_state,
        law_firm_name        = body.law_firm_name,
        years_experience     = body.years_experience,
        specialisations      = body.specialisations,
        languages            = body.languages,
        bio                  = body.bio,
        availability_note    = body.availability_note,
    )


# ── POST /onboarding/hr-profile  (NEW) ────────────────────────────────────────

@router.post("/hr-profile", status_code=200)
async def save_hr_profile(
    body: HRProfileRequest,
    db: DBSession,
    current_user: Current_User,
):
    """
    Step 2 for Employer/HR.
    Saves personal fields to user_profiles +
    company details to employer_profiles (creates row if missing).
    """
    return await service_save_hr_profile(
        db,
        user_id              = current_user.user_id,
        full_legal_name      = body.full_legal_name,
        date_of_birth        = body.date_of_birth,
        gender               = body.gender,
        nationality          = body.nationality,
        country_of_residence = body.country_of_residence,
        timezone             = body.timezone,
        preferred_language   = body.preferred_language,
        company_name         = body.company_name,
        company_size         = body.company_size,
        industry             = body.industry,
        website              = body.website,
        ein                  = body.ein,
        address_line1        = body.address_line1,
        address_line2        = body.address_line2,
        city                 = body.city,
        state                = body.state,
        zip_code             = body.zip_code,
        country              = body.country,
        contact_name         = body.contact_name,
        contact_email        = body.contact_email,
        contact_phone        = body.contact_phone,
    )


# ── POST /onboarding/admin-profile  (NEW) ─────────────────────────────────────

@router.post("/admin-profile", status_code=200)
async def save_admin_profile(
    body: AdminProfileRequest,
    db: DBSession,
    current_user: Current_User,
):
    """
    Step 2 for App Admin.
    Only personal preferences — no extra table.
    """
    return await service_save_admin_profile(
        db,
        user_id              = current_user.user_id,
        full_legal_name      = body.full_legal_name,
        date_of_birth        = body.date_of_birth,
        gender               = body.gender,
        nationality          = body.nationality,
        country_of_residence = body.country_of_residence,
        timezone             = body.timezone,
        preferred_language   = body.preferred_language,
    )


# ── POST /onboarding/complete ─────────────────────────────────────────────────

@router.post("/complete", status_code=200)
async def complete_onboarding(
    db: DBSession,
    current_user: Current_User,
):
    """
    Marks onboarding_completed = True.
    Returns dashboard_route so frontend can navigate correctly:
      employee  → /dashboard
      attorney  → /lawyer/dashboard
      hr        → /employer/dashboard
      app_admin → /admin/dashboard
    """
    return await service_complete_onboarding(
        db,
        user_id = current_user.user_id,
    )