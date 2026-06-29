# """
# Onboarding service functions.

# All business logic for the onboarding flow lives here.
# Routes in onboarding.py call these functions only.
# """
# from __future__ import annotations

# import uuid
# from datetime import datetime, timedelta

# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.exceptions import BadRequestException, NotFoundException
# from app.core.security import create_access_token, create_refresh_token
# from app.models.visamodels import User, UserOTP, UserProfile, UserVisaTarget, VisaType
# from app.services.otp_service import send_email_verification_otp
# from app.services.services import (
#     db_create,
#     db_delete,
#     db_get_by_field,
#     db_get_by_id,
#     db_list,
#     db_update,
#     get_user_role,
#     utc_now,
# )


# # ── GET /onboarding/status ────────────────────────────────────────────────────

# async def service_get_onboarding_status(
#     db: AsyncSession,
#     user_id: uuid.UUID,
#     roles: list[str],
# ) -> dict:
#     """
#     Returns the current onboarding state for the given user.
#     Frontend uses this to decide which screen to show.
#     """
#     profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
#     if not profile:
#         raise NotFoundException("Profile not found.")

#     targets = await db_list(
#         db,
#         UserVisaTarget,
#         filters=[UserVisaTarget.user_id == user_id],
#     )
#     # print(targets,"targets")
#     return {
#         "current_step":         profile.onboarding_step,
#         "onboarding_completed": profile.onboarding_completed,
#         "roles":                roles,
#         "full_legal_name":      profile.full_legal_name,
#         "nationality":          profile.nationality,
#         "visa_targets":         [t.visa_type_code for t in targets],
#     }


# # ── POST /onboarding/verify-email ─────────────────────────────────────────────

# async def service_verify_email(
#     db: AsyncSession,
#     *,
#     user_id: uuid.UUID,
#     otp: str,
# ) -> dict:
#     """
#     Verifies the 6-digit OTP the user received by email.
#     - Marks the OTP row as used.
#     - Sets User.is_verified = True.
#     - Advances onboarding_step to 'profile' so frontend goes to Step 2.
#     - Returns fresh tokens.
#     """
#     # ── 1. Find a valid, unused, non-expired OTP ───────────────────────────
#     otp_record = await db.scalar(
#         select(UserOTP)
#         .where(UserOTP.user_id   == user_id)
#         .where(UserOTP.otp_code  == otp)
#         .where(UserOTP.otp_type  == "email_verification")
#         .where(UserOTP.is_used   == False)                      # noqa: E712
#         .where(UserOTP.expires_at > utc_now())
#         .order_by(UserOTP.created_at.desc())
#     )
#     if not otp_record:
#         raise BadRequestException("Invalid or expired code. Please request a new one.")

#     # ── 2. Mark OTP as used ────────────────────────────────────────────────
#     await db_update(db, UserOTP, otp_record.id, {"is_used": True})

#     # ── 3. Get user & guard against double-verify ──────────────────────────
#     user = await db_get_by_id(db, User, user_id)
#     if not user:
#         raise NotFoundException("User not found.")

#     if user.is_verified:
#         raise BadRequestException("This email is already verified.")

#     # ── 4. Mark user as verified ───────────────────────────────────────────
#     await db_update(db, User, user.id, {"is_verified": True})

#     # ── 5. Advance onboarding step → 'profile' (go to Step 2 screen) ──────
#     profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
#     print(profile.onboarding_step,"profile")
#     if not profile:
#         raise NotFoundException("Profile not found.")

#     await db_update(db, UserProfile, profile.id, {
#         "onboarding_step": 2,
#     })

#     # ── 6. Return fresh tokens ─────────────────────────────────────────────
#     roles = await get_user_role(db, user_id)
#     if isinstance(roles, str):
#         roles = [roles]

#     # return {
#     #     "access_token":    create_access_token(str(user_id),{"roles": roles}),
#     #     "refresh_token":   create_refresh_token(str(user_id)),
#     #     "roles":           roles,
#     #     "user":user,
#     #     "onboarding_step": 2,
#     # }
#     return {
#         "access_token": create_access_token(str(user_id), roles),
#         "refresh_token": create_refresh_token(str(user_id)),
#         "roles": roles,
#         "user": {
#             "id": str(user.id),
#             "first_name": user.first_name,
#             "last_name": user.last_name,
#             "email": user.email,
#         },
#         "onboarding_step": 2,
#     }

# # ── POST /onboarding/resend-otp ───────────────────────────────────────────────

# async def service_resend_otp(
#     db: AsyncSession,
#     *,
#     user_id: uuid.UUID,
# ) -> None:
#     """
#     Resends the email verification OTP.
#     Rate-limited: only 1 resend allowed per 60 seconds.
#     """
#     # ── 1. Get user ────────────────────────────────────────────────────────
#     user = await db_get_by_id(db, User, user_id)
#     if not user:
#         raise NotFoundException("User not found.")

#     # ── 2. Already verified? ───────────────────────────────────────────────
#     if user.is_verified:
#         raise BadRequestException("This email is already verified.")

#     # ── 3. Rate limit — block if an OTP was sent in the last 60 seconds ───
#     recent_otp = await db.scalar(
#         select(UserOTP)
#         .where(UserOTP.user_id  == user_id)
#         .where(UserOTP.otp_type == "email_verification")
#         .where(UserOTP.created_at > utc_now() - timedelta(seconds=60))
#         .order_by(UserOTP.created_at.desc())
#     )
#     if recent_otp:
#         raise BadRequestException(
#             "Please wait 60 seconds before requesting a new code."
#         )

#     # ── 4. Send fresh OTP ──────────────────────────────────────────────────
#     await send_email_verification_otp(db, user)


# # ── POST /onboarding/role ─────────────────────────────────────────────────────

# async def service_set_role(
#     db: AsyncSession,
#     user_id: uuid.UUID,
#     *,
#     role: str,
# ) -> dict:
#     """
#     Screen 04 — saves the user's chosen role.
#     Advances onboarding_step to 'profile'.
#     """
#     profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
#     if not profile:
#         raise NotFoundException("Profile not found.")

#     await db_update(db, UserProfile, profile.id, {
#         "user_role":       role,
#         "onboarding_step": 3,
#     })

#     roles = await get_user_role(db, user_id)
#     return await service_get_onboarding_status(db, user_id, roles)


# # ── POST /onboarding/profile ──────────────────────────────────────────────────
# async def service_save_profile(
#     db: AsyncSession,
#     user_id: uuid.UUID,
#     *,
#     full_legal_name: str,
#     nationality: str,
#     visa_targets: list[str],
#     date_of_birth: str | None = None,
#     gender: str | None = None,
#     country_of_residence: str | None = None,
#     primary_visa: str | None = None,
#     timezone: str | None = None,
#     preferred_language: str | None = None,
# ) -> dict:
#     """
#     Screen 05 — saves all profile fields from onboarding Step 2.
#     Replaces existing visa targets (delete + re-insert).
#     Advances onboarding_step to 3.
#     """
#     profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
#     if not profile:
#         raise NotFoundException("Profile not found.")

#     # ── Parse date_of_birth string → Python date ───────────────────────
#     parsed_dob = None
#     if date_of_birth:
#         try:
#             parsed_dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
#         except ValueError:
#             raise BadRequestException("date_of_birth must be in YYYY-MM-DD format.")

#     # ── Update all profile fields ──────────────────────────────────────
#     update_data = {
#         "full_legal_name":      full_legal_name,
#         "nationality":          nationality,
#         "onboarding_step":      3,
#     }

#     if parsed_dob is not None:
#         update_data["date_of_birth"] = parsed_dob
#     if gender is not None:
#         update_data["gender"] = gender
#     if country_of_residence is not None:
#         update_data["country_of_residence"] = country_of_residence
#     if timezone is not None:
#         update_data["timezone"] = timezone
#     if preferred_language is not None:
#         update_data["preferred_language"] = preferred_language

#     await db_update(db, UserProfile, profile.id, update_data)

#     # ── Replace visa targets ───────────────────────────────────────────
#     existing = await db_list(
#         db, UserVisaTarget,
#         filters=[UserVisaTarget.user_id == user_id],
#     )
#     for t in existing:
#         await db_delete(db, UserVisaTarget, t.id)

#     for i, vt in enumerate(visa_targets):
#         await db_create(db, UserVisaTarget(
#             user_id        = user_id,
#             visa_type_code = vt,
#             is_primary     = (vt == primary_visa) if primary_visa else (i == 0),
#             created_by     = user_id,
#         ))

#     roles = await get_user_role(db, user_id)
#     return await service_get_onboarding_status(db, user_id, roles)


# # ── POST /onboarding/complete ─────────────────────────────────────────────────

# async def service_complete_onboarding(
#     db: AsyncSession,
#     user_id: uuid.UUID,
# ) -> dict:
#     """
#     Screen 06 — user clicks 'Start My First Application'.
#     Marks onboarding as fully completed.
#     """
#     profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
#     if not profile:
#         raise NotFoundException("Profile not found.")

#     await db_update(db, UserProfile, profile.id, {
#         "onboarding_step": 4,
#         "onboarding_completed": True,
#     })

#     roles = await get_user_role(db, user_id)
#     return await service_get_onboarding_status(db, user_id, roles)


"""
Onboarding service functions.

All business logic for the onboarding flow lives here.
Routes in onboarding.py call these functions only.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import create_access_token, create_refresh_token
from app.models.visamodels import (
    User,
    UserOTP,
    UserProfile,
    UserVisaTarget,
    VisaType,
    AttorneyProfile,
    EmployerProfile,
)
from app.services.otp_service import send_email_verification_otp
from app.services.services import (
    db_create,
    db_delete,
    db_get_by_field,
    db_get_by_id,
    db_list,
    db_update,
    get_user_role,
    utc_now,
)


# ── GET /onboarding/status ────────────────────────────────────────────────────

async def service_get_onboarding_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    roles: list[str],
) -> dict:
    """
    Returns the current onboarding state for the given user.
    Frontend uses this to decide which screen to show.
    """
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    targets = await db_list(
        db,
        UserVisaTarget,
        filters=[UserVisaTarget.user_id == user_id],
    )
    return {
        "current_step":         profile.onboarding_step,
        "onboarding_completed": profile.onboarding_completed,
        "roles":                roles,
        "full_legal_name":      profile.full_legal_name,
        "nationality":          profile.nationality,
        "visa_targets":         [t.visa_type_code for t in targets],
    }


# ── POST /onboarding/verify-email ─────────────────────────────────────────────

async def service_verify_email(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    otp: str,
) -> dict:
    """
    Verifies the 6-digit OTP the user received by email.
    - Marks the OTP row as used.
    - Sets User.is_verified = True.
    - Advances onboarding_step to 2 so frontend goes to Step 2.
    - Returns fresh tokens.
    """
    otp_record = await db.scalar(
        select(UserOTP)
        .where(UserOTP.user_id   == user_id)
        .where(UserOTP.otp_code  == otp)
        .where(UserOTP.otp_type  == "email_verification")
        .where(UserOTP.is_used   == False)                      # noqa: E712
        .where(UserOTP.expires_at > utc_now())
        .order_by(UserOTP.created_at.desc())
    )
    if not otp_record:
        raise BadRequestException("Invalid or expired code. Please request a new one.")

    await db_update(db, UserOTP, otp_record.id, {"is_used": True})

    user = await db_get_by_id(db, User, user_id)
    if not user:
        raise NotFoundException("User not found.")

    if user.is_verified:
        raise BadRequestException("This email is already verified.")

    await db_update(db, User, user.id, {"is_verified": True})

    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    await db_update(db, UserProfile, profile.id, {"onboarding_step": 2})

    roles = await get_user_role(db, user_id)
    if isinstance(roles, str):
        roles = [roles]

    return {
        "access_token":  create_access_token(str(user_id), roles),
        "refresh_token": create_refresh_token(str(user_id)),
        "roles":         roles,
        "user": {
            "id":         str(user.id),
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "email":      user.email,
        },
        "onboarding_step": 2,
    }


# ── POST /onboarding/resend-otp ───────────────────────────────────────────────

async def service_resend_otp(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    user = await db_get_by_id(db, User, user_id)
    if not user:
        raise NotFoundException("User not found.")
    if user.is_verified:
        raise BadRequestException("This email is already verified.")

    recent_otp = await db.scalar(
        select(UserOTP)
        .where(UserOTP.user_id  == user_id)
        .where(UserOTP.otp_type == "email_verification")
        .where(UserOTP.created_at > utc_now() - timedelta(seconds=60))
        .order_by(UserOTP.created_at.desc())
    )
    if recent_otp:
        raise BadRequestException(
            "Please wait 60 seconds before requesting a new code."
        )

    await send_email_verification_otp(db, user)


# ── POST /onboarding/role ─────────────────────────────────────────────────────

async def service_set_role(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    role: str,
) -> dict:
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    await db_update(db, UserProfile, profile.id, {
        "user_role":       role,
        "onboarding_step": 3,
    })

    roles = await get_user_role(db, user_id)
    return await service_get_onboarding_status(db, user_id, roles)


# ── POST /onboarding/profile ──────────────────────────────────────────────────
# Employee / Student — unchanged behaviour, unchanged endpoint

async def service_save_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    full_legal_name: str,
    nationality: str,
    visa_targets: list[str],
    date_of_birth: str | None = None,
    gender: str | None = None,
    country_of_residence: str | None = None,
    primary_visa: str | None = None,
    timezone: str | None = None,
    preferred_language: str | None = None,
) -> dict:
    """
    Screen 05 — saves all profile fields from onboarding Step 2.
    Used only for Employee/Student role.
    Replaces existing visa targets (delete + re-insert).
    Advances onboarding_step to 3.
    """
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise BadRequestException("date_of_birth must be in YYYY-MM-DD format.")

    update_data: dict = {
        "full_legal_name": full_legal_name,
        "nationality":     nationality,
        "onboarding_step": 3,
    }
    if parsed_dob is not None:
        update_data["date_of_birth"] = parsed_dob
    if gender is not None:
        update_data["gender"] = gender
    if country_of_residence is not None:
        update_data["country_of_residence"] = country_of_residence
    if timezone is not None:
        update_data["timezone"] = timezone
    if preferred_language is not None:
        update_data["preferred_language"] = preferred_language

    await db_update(db, UserProfile, profile.id, update_data)

    # Replace visa targets
    existing = await db_list(
        db, UserVisaTarget,
        filters=[UserVisaTarget.user_id == user_id],
    )
    for t in existing:
        await db_delete(db, UserVisaTarget, t.id)

    for i, vt in enumerate(visa_targets):
        await db_create(db, UserVisaTarget(
            user_id        = user_id,
            visa_type_code = vt,
            is_primary     = (vt == primary_visa) if primary_visa else (i == 0),
            created_by     = user_id,
        ))

    roles = await get_user_role(db, user_id)
    return await service_get_onboarding_status(db, user_id, roles)


# =============================================================================
# NEW — Attorney profile (Step 2 for Lawyer role)
# POST /onboarding/attorney-profile
# =============================================================================

async def service_save_attorney_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    # Personal fields (go to user_profiles)
    full_legal_name:      str | None = None,
    date_of_birth:        str | None = None,
    gender:               str | None = None,
    nationality:          str | None = None,
    country_of_residence: str | None = None,
    timezone:             str | None = None,
    preferred_language:   str | None = None,
    # Professional fields (go to attorney_profiles)
    bar_number:        str | None  = None,
    bar_state:         str | None  = None,
    law_firm_name:     str | None  = None,
    years_experience:  int | None  = None,
    specialisations:   list[str]   = [],
    languages:         list[str]   = [],
    bio:               str | None  = None,
    availability_note: str | None  = None,
) -> dict:
    """
    Step 2 for Attorney/Lawyer role.
    1. Updates user_profiles with personal fields (onboarding_step → 3).
    2. Creates or updates attorney_profiles with professional credentials.
    """
    # ── 1. user_profiles ──────────────────────────────────────────────────
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise BadRequestException("date_of_birth must be in YYYY-MM-DD format.")

    personal_update: dict = {"onboarding_step": 3}
    if full_legal_name:
        personal_update["full_legal_name"] = full_legal_name
    if parsed_dob:
        personal_update["date_of_birth"] = parsed_dob
    if gender:
        personal_update["gender"] = gender
    if nationality:
        personal_update["nationality"] = nationality
    if country_of_residence:
        personal_update["country_of_residence"] = country_of_residence
    if timezone:
        personal_update["timezone"] = timezone
    if preferred_language:
        personal_update["preferred_language"] = preferred_language

    await db_update(db, UserProfile, profile.id, personal_update)

    # ── 2. attorney_profiles ──────────────────────────────────────────────
    existing = await db.scalar(
        select(AttorneyProfile).where(AttorneyProfile.user_id == user_id)
    )

    specialisations_json = json.dumps(specialisations) if specialisations else None
    languages_json       = json.dumps(languages)       if languages       else None

    if existing:
        professional_update: dict = {}
        if bar_number        is not None: professional_update["bar_number"]        = bar_number
        if bar_state         is not None: professional_update["bar_state"]         = bar_state
        if law_firm_name     is not None: professional_update["law_firm_name"]     = law_firm_name
        if years_experience  is not None: professional_update["years_experience"]  = years_experience
        if specialisations_json:          professional_update["specialisations"]   = specialisations_json
        if languages_json:                professional_update["languages"]          = languages_json
        if bio               is not None: professional_update["bio"]               = bio
        if availability_note is not None: professional_update["availability_note"] = availability_note
        if professional_update:
            await db_update(db, AttorneyProfile, existing.id, professional_update)
        attorney_id = existing.id
    else:
        new_attorney = AttorneyProfile(
            id                = uuid.uuid4(),
            user_id           = user_id,
            bar_number        = bar_number,
            bar_state         = bar_state,
            law_firm_name     = law_firm_name,
            years_experience  = years_experience,
            specialisations   = specialisations_json,
            languages         = languages_json,
            bio               = bio,
            availability_note = availability_note,
            is_accepting_cases= True,
            is_verified       = False,
            is_active         = True,
            created_by        = user_id,
            modified_by       = user_id,
        )
        saved = await db_create(db, new_attorney)
        attorney_id = saved.id

    roles = await get_user_role(db, user_id)
    if isinstance(roles, str):
        roles = [roles]

    return {
        "message":         "Attorney profile saved.",
        "onboarding_step": 3,
        "attorney_id":     str(attorney_id),
        "roles":           roles,
    }


# =============================================================================
# NEW — HR / Employer profile (Step 2 for HR role)
# POST /onboarding/hr-profile
# =============================================================================

async def service_save_hr_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    # Personal fields (go to user_profiles)
    full_legal_name:      str | None = None,
    date_of_birth:        str | None = None,
    gender:               str | None = None,
    nationality:          str | None = None,
    country_of_residence: str | None = None,
    timezone:             str | None = None,
    preferred_language:   str | None = None,
    # Company fields (go to employer_profiles — exact column names)
    company_name:   str,
    company_size:   str | None = None,   # "1_10"|"11_50"|"51_200"|"201_500"|"501_1000"|"1000_plus"
    industry:       str | None = None,
    website:        str | None = None,
    ein:            str | None = None,
    address_line1:  str | None = None,
    address_line2:  str | None = None,
    city:           str | None = None,
    state:          str | None = None,
    zip_code:       str | None = None,
    country:        str | None = None,
    contact_name:   str | None = None,
    contact_email:  str | None = None,
    contact_phone:  str | None = None,
) -> dict:
    """
    Step 2 for Employer/HR role.
    1. Updates user_profiles with personal fields.
    2. Creates or updates employer_profiles with company details.
    """
    # ── 1. user_profiles ──────────────────────────────────────────────────
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise BadRequestException("date_of_birth must be in YYYY-MM-DD format.")

    personal_update: dict = {"onboarding_step": 3}
    if full_legal_name:       personal_update["full_legal_name"]      = full_legal_name
    if parsed_dob:            personal_update["date_of_birth"]        = parsed_dob
    if gender:                personal_update["gender"]               = gender
    if nationality:           personal_update["nationality"]           = nationality
    if country_of_residence:  personal_update["country_of_residence"] = country_of_residence
    if timezone:              personal_update["timezone"]              = timezone
    if preferred_language:    personal_update["preferred_language"]   = preferred_language

    await db_update(db, UserProfile, profile.id, personal_update)

    # ── 2. employer_profiles ──────────────────────────────────────────────
    existing = await db.scalar(
        select(EmployerProfile).where(EmployerProfile.user_id == user_id)
    )

    employer_payload: dict = {
        k: v for k, v in {
            "company_name":  company_name,
            "company_size":  company_size,
            "industry":      industry,
            "website":       website,
            "ein":           ein,
            "address_line1": address_line1,
            "address_line2": address_line2,
            "city":          city,
            "state":         state,
            "zip_code":      zip_code,
            "country":       country,
            "contact_name":  contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
        }.items() if v is not None
    }

    if existing:
        employer_payload["modified_by"] = user_id
        await db_update(db, EmployerProfile, existing.id, employer_payload)
    else:
        new_employer = EmployerProfile(
            id         = uuid.uuid4(),
            user_id    = user_id,
            created_by = user_id,
            **employer_payload,
        )
        await db_create(db, new_employer)

    roles = await get_user_role(db, user_id)
    if isinstance(roles, str):
        roles = [roles]

    return {
        "message":         "Employer profile saved.",
        "onboarding_step": 3,
        "roles":           roles,
    }


# =============================================================================
# NEW — Admin profile (Step 2 for App Admin role)
# POST /onboarding/admin-profile
# Minimal — just personal preferences, no extra table
# =============================================================================

async def service_save_admin_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    full_legal_name:      str | None = None,
    date_of_birth:        str | None = None,
    gender:               str | None = None,
    nationality:          str | None = None,
    country_of_residence: str | None = None,
    timezone:             str | None = None,
    preferred_language:   str | None = None,
) -> dict:
    """
    Step 2 for App Admin role.
    Only personal preferences — no extra table needed.
    """
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise BadRequestException("date_of_birth must be in YYYY-MM-DD format.")

    update_data: dict = {"onboarding_step": 3}
    if full_legal_name:       update_data["full_legal_name"]      = full_legal_name
    if parsed_dob:            update_data["date_of_birth"]        = parsed_dob
    if gender:                update_data["gender"]               = gender
    if nationality:           update_data["nationality"]           = nationality
    if country_of_residence:  update_data["country_of_residence"] = country_of_residence
    if timezone:              update_data["timezone"]              = timezone
    if preferred_language:    update_data["preferred_language"]   = preferred_language

    await db_update(db, UserProfile, profile.id, update_data)

    roles = await get_user_role(db, user_id)
    if isinstance(roles, str):
        roles = [roles]

    return {
        "message":         "Admin profile saved.",
        "onboarding_step": 3,
        "roles":           roles,
    }


# ── POST /onboarding/complete ─────────────────────────────────────────────────

DASHBOARD_ROUTES: dict[str, str] = {
    "employee":  "/dashboard",
    "hr":        "/employer/dashboard",
    "attorney":  "/lawyer/dashboard",
    "app_admin": "/admin/dashboard",
}

async def service_complete_onboarding(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """
    Marks onboarding_completed = True.
    Returns dashboard_route so frontend can navigate correctly.
    """
    profile = await db_get_by_field(db, UserProfile, "user_id", user_id)
    if not profile:
        raise NotFoundException("Profile not found.")

    await db_update(db, UserProfile, profile.id, {
        "onboarding_step":      4,
        "onboarding_completed": True,
    })

    roles = await get_user_role(db, user_id)
    if isinstance(roles, str):
        roles = [roles]

    primary_role  = roles[0] if roles else "employee"
    dashboard_url = DASHBOARD_ROUTES.get(primary_role, "/dashboard")

    status = await service_get_onboarding_status(db, user_id, roles)
    status["dashboard_route"] = dashboard_url
    return status