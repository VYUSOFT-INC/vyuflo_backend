# """
# Pydantic schemas for onboarding routes.
# File: app/schemas/onboarding.py
# """
# from typing import Optional
# from pydantic import BaseModel


# # ── Requests ──────────────────────────────────────────────────────────────────

# class VerifyEmailRequest(BaseModel):
#     otp: str                        # 6-digit code from email


# class OnboardingRoleRequest(BaseModel):
#     role: str                       # employee_student | employer_hr | lawyer | admin


# # class OnboardingProfileRequest(BaseModel):
# #     full_legal_name: str
# #     nationality:     str
# #     visa_targets:    list[str]      # e.g. ["H-1B", "F-1"]

# class OnboardingProfileRequest(BaseModel):
#     full_legal_name: str
#     date_of_birth: str | None = None        # "YYYY-MM-DD"
#     gender: str | None = None
#     nationality: str
#     country_of_residence: str | None = None
#     visa_targets: list[str]
#     primary_visa: str | None = None
#     timezone: str | None = None
#     preferred_language: str | None = None
#     phone_number:         Optional[str]  = None   # ← ADD
#     country_code:         Optional[str]  = None   # ← ADD e.g. "+91"

# class OnboardingCompleteRequest(BaseModel):
#     pass                            # no body needed — identity from token


# # ── Responses ─────────────────────────────────────────────────────────────────

# class OnboardingStatusResponse(BaseModel):
#     current_step:         str | int
#     onboarding_completed: bool
#     roles:                list[str]
#     full_legal_name:      Optional[str] = None
#     nationality:          Optional[str] = None
#     visa_targets:         list[str]     = []


"""
app/schemas/onboarding.py  — FULL REPLACEMENT
Add the 3 new role-specific request schemas below the existing ones.
All existing schemas are preserved unchanged.
"""
from typing import Optional
from pydantic import BaseModel, Field


# ── Existing schemas (unchanged) ──────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    otp: str                        # 6-digit code from email


class OnboardingRoleRequest(BaseModel):
    role: str                       # employee | hr | attorney | app_admin


class OnboardingProfileRequest(BaseModel):
    """Employee/Student — existing endpoint POST /onboarding/profile"""
    full_legal_name:      str
    date_of_birth:        str | None = None        # "YYYY-MM-DD"
    gender:               str | None = None
    nationality:          str
    country_of_residence: str | None = None
    visa_targets:         list[str]
    primary_visa:         str | None = None
    timezone:             str | None = None
    preferred_language:   str | None = None
    phone_number:         Optional[str] = None
    country_code:         Optional[str] = None
    theme_color:          Optional[str] = None


class OnboardingCompleteRequest(BaseModel):
    pass                            # no body needed — identity from token


class OnboardingStatusResponse(BaseModel):
    current_step:         str | int
    onboarding_completed: bool
    roles:                list[str]
    full_legal_name:      Optional[str] = None
    nationality:          Optional[str] = None
    visa_targets:         list[str]     = []


# ── NEW: Attorney/Lawyer — POST /onboarding/attorney-profile ─────────────────

class AttorneyProfileRequest(BaseModel):
    """Step 2 profile for Attorney/Lawyer role."""
    # Personal fields (→ user_profiles)
    full_legal_name:      Optional[str] = None
    date_of_birth:        Optional[str] = None      # "YYYY-MM-DD"
    gender:               Optional[str] = None
    nationality:          Optional[str] = None
    country_of_residence: Optional[str] = None
    timezone:             Optional[str] = None
    preferred_language:   Optional[str] = None

    # Professional fields (→ attorney_profiles)
    bar_number:           Optional[str]   = None
    bar_state:            Optional[str]   = None    # e.g. "CA", "NY"
    law_firm_name:        Optional[str]   = None
    years_experience:     Optional[int]   = Field(None, ge=0, le=70)
    specialisations:      list[str]       = []      # ["H-1B", "O-1", "EB-2"]
    languages:            list[str]       = []      # ["English", "Spanish"]
    bio:                  Optional[str]   = None
    availability_note:    Optional[str]   = None    # "Mon–Fri 9am–6pm EST"


# ── NEW: Employer/HR — POST /onboarding/hr-profile ───────────────────────────

COMPANY_SIZE_OPTIONS = ("1_10", "11_50", "51_200", "201_500", "501_1000", "1000_plus")

class HRProfileRequest(BaseModel):
    """Step 2 profile for Employer/HR role — maps to employer_profiles table."""
    # Personal fields (→ user_profiles)
    full_legal_name:      Optional[str] = None
    date_of_birth:        Optional[str] = None
    gender:               Optional[str] = None
    nationality:          Optional[str] = None
    country_of_residence: Optional[str] = None
    timezone:             Optional[str] = None
    preferred_language:   Optional[str] = None

    # Company fields (→ employer_profiles — exact column names)
    company_name:   str                   # required
    company_size:   Optional[str] = None  # "1_10"|"11_50"|"51_200"|"201_500"|"501_1000"|"1000_plus"
    industry:       Optional[str] = None
    website:        Optional[str] = None
    ein:            Optional[str] = None  # Employer Identification Number
    address_line1:  Optional[str] = None
    address_line2:  Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    zip_code:       Optional[str] = None
    country:        Optional[str] = None
    contact_name:   Optional[str] = None
    contact_email:  Optional[str] = None
    contact_phone:  Optional[str] = None


# ── NEW: App Admin — POST /onboarding/admin-profile ──────────────────────────

class AdminProfileRequest(BaseModel):
    """Step 2 profile for App Admin role — personal preferences only."""
    full_legal_name:      Optional[str] = None
    date_of_birth:        Optional[str] = None
    gender:               Optional[str] = None
    nationality:          Optional[str] = None
    country_of_residence: Optional[str] = None
    timezone:             Optional[str] = None
    preferred_language:   Optional[str] = None