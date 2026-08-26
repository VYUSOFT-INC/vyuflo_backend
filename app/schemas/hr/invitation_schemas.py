# app/schemas/invitation_schemas.py
import re
import uuid
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, field_validator


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class InviteByEmailRequest(BaseModel):
    """HR invites a specific employee by email."""
    email:             EmailStr
    # MANDATORY — identity verification. The employee must correctly
    # re-enter this exact number before their acceptance is allowed.
    # Only a hash is ever stored server-side (see invited_passport_hash).
    passport_number:   str = Field(..., min_length=6, max_length=20)
    personal_message:  Optional[str] = Field(None, max_length=500)
    expires_days:      int            = Field(7, ge=1, le=30)
    # How many days until the invite expires (default 7)

    @field_validator("passport_number")
    @classmethod
    def validate_passport_number(cls, v: str) -> str:
        cleaned = v.strip().upper().replace(" ", "").replace("-", "")
        if not cleaned:
            raise ValueError("Passport number is required.")
        if not re.match(r"^[A-Z0-9]{6,20}$", cleaned):
            raise ValueError("Passport number must be 6–20 alphanumeric characters.")
        return cleaned


class InviteByCodeRequest(BaseModel):
    """HR generates a reusable company code to share offline."""
    max_uses:         Optional[int]  = Field(None, ge=1, le=500)
    # NULL = unlimited — good for large companies
    personal_message: Optional[str]  = Field(None, max_length=500)


class AcceptInviteRequest(BaseModel):
    """
    Employee accepts an invite.
    Works for all 3 methods — frontend sends whichever token/code they have.

    passport_number is optional AT THE SCHEMA LEVEL because code/link
    invites never collect one. For email invites it is effectively
    mandatory — the service layer enforces this by checking whether the
    resolved invitation has an invited_passport_hash set, and rejects
    acceptance if it's missing or doesn't match.
    """
    invite_token:     Optional[str] = None   # link method
    invite_code:      Optional[str] = None   # code method
    passport_number:  Optional[str] = None   # required only for email-method invites
    # email method uses invite_token from the email link


class ValidateTokenRequest(BaseModel):
    """Public endpoint — check if a token/code is valid before showing accept page."""
    invite_token: Optional[str] = None
    invite_code:  Optional[str] = None


class AcceptInviteNewUserRequest(BaseModel):
    """
    Public — used when NO existing account matches the resolved primary
    email. `email` is whichever email the classification step determined
    should be primary — mandatory. `other_email` is optional (invited email
    or the extra one they typed), stored as a linked email.
    """
    invite_token:     Optional[str] = None
    invite_code:      Optional[str] = None
    first_name:       str
    last_name:        str
    email:            EmailStr
    other_email:      Optional[EmailStr] = None
    password:         str = Field(..., min_length=8)
    passport_number:  Optional[str] = None
    terms_accepted:   bool


class RequestMergeOtpRequest(BaseModel):
    """
    Public — step 1 of the merge flow. Sends a one-time login code to the
    matched account's personal email, to confirm it's really them before
    merging the invite in.
    """
    invite_token: Optional[str] = None
    invite_code:  Optional[str] = None
    login_email:  EmailStr


class AcceptInviteExistingUserRequest(BaseModel):
    """
    Public — step 2 of the merge flow. `other_email`, if given, gets added
    to the matched account's linked emails once identity is confirmed.
    """
    invite_token: Optional[str] = None
    invite_code:  Optional[str] = None
    login_email:  EmailStr
    otp_code:     str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    other_email:  Optional[EmailStr] = None
    passport_number: Optional[str] = None


class UpdateEmployeeRequest(BaseModel):
    """HR updates job info for a linked employee."""
    job_title:   Optional[str] = Field(None, max_length=200)
    department:  Optional[str] = Field(None, max_length=200)
    work_email:  Optional[str] = Field(None, max_length=255)
    start_date:  Optional[str] = None   # YYYY-MM-DD
    is_active:   Optional[bool] = None


class RevokeInviteRequest(BaseModel):
    """HR revokes a pending invite."""
    reason: Optional[str] = Field(None, max_length=300)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class EmployerProfileShort(BaseModel):
    id:           uuid.UUID
    company_name: str
    industry:     Optional[str]
    is_verified:  bool

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    id:               uuid.UUID
    invite_method:    str
    status:           str
    invited_email:    Optional[str]
    invite_code:      Optional[str]
    invite_token:     Optional[str]
    max_uses:         Optional[int]
    used_count:       int
    expires_at:       Optional[datetime]
    personal_message: Optional[str]
    created_at:       datetime

    class Config:
        from_attributes = True


class InvitationWithCompany(InvitationResponse):
    """Returned when employee validates a token — includes company info."""
    company_name:    str
    company_industry: Optional[str]
    hr_name:         str
    # So employee can see "TechCorp (Sarah) is inviting you"


class AcceptInviteResponse(BaseModel):
    message:               str
    company_name:          str
    employer_id:           uuid.UUID
    # employer_profiles.id — now stored in user_profiles.employer_id
    needs_personal_email:  bool = False


class EmployeeResponse(BaseModel):
    """HR sees this when listing their employees."""
    id:          uuid.UUID
    employee_id: uuid.UUID

    # Employee personal info
    full_name:   str
    email:       str
    profile_picture_url: Optional[str]

    # Job info
    job_title:   Optional[str]
    department:  Optional[str]
    work_email:  Optional[str]
    start_date:  Optional[str]
    is_active:   bool
    access_revoked_at: Optional[str] = None

    # Application stats
    active_applications: int = 0
    pending_documents:   int = 0

    linked_at:   datetime

    class Config:
        from_attributes = True


class ValidateTokenResponse(BaseModel):
    valid:         bool
    company_name:  Optional[str] = None
    hr_name:       Optional[str] = None
    invite_method: Optional[str] = None
    message:       str

    # The email the invite was actually sent to — exposed so the frontend
    # can prefill the signup/merge forms. Safe to expose publicly since
    # the person already received it in their inbox.
    invited_email: Optional[str] = None

    # True → the accept screen must show a blank passport number field and
    # block acceptance until it's correctly filled in. Always true for
    # email-method invites now that passport_number is mandatory on creation.
    requires_passport_verification: bool = False

    # Tells the frontend which screen to show next —
    # True  → merge-via-OTP flow (existing account)
    # False → new-account creation flow
    account_exists: bool = False

    # Only present once the frontend has answered the "another email?" /
    # "is it primary?" questions and re-called this endpoint with them.
    resolved_primary_email: Optional[str] = None
    resolved_other_email:   Optional[str] = None


class AcceptInviteAuthResponse(BaseModel):
    """
    Returned by both the new-user and existing-user accept endpoints.
    Mirrors the token shape used by signup/login so the frontend can log
    the person straight in after accepting.
    """
    access_token:  str
    refresh_token: str
    roles:         list[str]
    company_name:  str
    employer_id:   uuid.UUID
    # True → the account's primary email matches the employer's registered
    # domain AND no second verified email is on file yet. Frontend should
    # show the "add a personal email" prompt even if `other_email` wasn't
    # filled in during signup/merge — this is the same domain-match check
    # used by the authenticated accept path, ported here so someone who
    # skips the optional field still gets asked once, right after joining.
    needs_personal_email: bool = False
    linked_email:  Optional[str] = None
    message:       str


class RequestMergeOtpResponse(BaseModel):
    message: str


class InvitationListResponse(BaseModel):
    items: list[InvitationResponse]
    total: int


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int

class EmployerDomainResponse(BaseModel):
    domain: Optional[str] = None