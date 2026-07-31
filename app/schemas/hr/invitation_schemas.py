# app/schemas/invitation_schemas.py
import uuid
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class InviteByEmailRequest(BaseModel):
    """HR invites a specific employee by email."""
    email:            EmailStr
    personal_message: Optional[str] = Field(None, max_length=500)
    expires_days:     int            = Field(7, ge=1, le=30)
    # How many days until the invite expires (default 7)


class InviteByCodeRequest(BaseModel):
    """HR generates a reusable company code to share offline."""
    max_uses:         Optional[int]  = Field(None, ge=1, le=500)
    # NULL = unlimited — good for large companies
    personal_message: Optional[str]  = Field(None, max_length=500)


class InviteByLinkRequest(BaseModel):
    """HR generates a shareable link."""
    max_uses:         Optional[int]  = Field(None, ge=1, le=500)
    personal_message: Optional[str]  = Field(None, max_length=500)
    expires_days:     Optional[int]  = Field(30, ge=1, le=365)


class AcceptInviteRequest(BaseModel):
    """
    Employee accepts an invite.
    Works for all 3 methods — frontend sends whichever token/code they have.
    """
    invite_token: Optional[str] = None   # link method
    invite_code:  Optional[str] = None   # code method
    # email method uses invite_token from the email link


class ValidateTokenRequest(BaseModel):
    """Public endpoint — check if a token/code is valid before showing accept page."""
    invite_token: Optional[str] = None
    invite_code:  Optional[str] = None


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
    message:      str
    company_name: str
    employer_id:  uuid.UUID
    # employer_profiles.id — now stored in user_profiles.employer_id


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

    # Application stats
    active_applications: int = 0
    pending_documents:   int = 0

    linked_at:   datetime

    class Config:
        from_attributes = True


class ValidateTokenResponse(BaseModel):
    valid:        bool
    company_name: Optional[str] = None
    hr_name:      Optional[str] = None
    invite_method: Optional[str] = None
    message:      str
    # "Valid invite from TechCorp" or "This invite has expired"


class InvitationListResponse(BaseModel):
    items: list[InvitationResponse]
    total: int


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int