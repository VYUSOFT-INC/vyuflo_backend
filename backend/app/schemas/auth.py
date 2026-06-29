"""
Pydantic schemas for authentication endpoints.
Covers: Login, Signup, SSO, Password Reset, Token responses.
"""
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from enum import Enum

class UserBasic(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ✅ allows ORM object → pydantic

    # id:         str
    email:      str
    first_name: str
    last_name:  str
    phone:      str | None = None

# ── Token ─────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: Optional[str] = None
    token_type:    str = "bearer"
    roles:list[str]| None = None
    profile:Optional[str] = None
    user:UserBasic| None = None
    onboarding_step: int | None = None
    


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    
class UserRoleName(str, Enum):
    APP_ADMIN = "app_admin"
    HR        = "hr"
    EMPLOYEE  = "employee"
    ATTORNEY  = "attorney"

# ── Login ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    """Screen 01 – Login with email/password."""
    email:       EmailStr
    password:    str = Field(..., min_length=1)
    remember_me: bool = False


# ── Signup ────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    """Screen 02 – Create account with email/password."""
    first_name:       str       = Field(..., min_length=1, max_length=100)
    last_name:        str       = Field(..., min_length=1, max_length=100)
    email:            EmailStr
    password:         str       = Field(..., min_length=8, max_length=128)
    phone:            Optional[str] = Field(None, max_length=20, description="Phone for SMS/2FA")
    country_code:Optional[str] = Field(None, max_length=10, description="Phone for SMS/2FA")
    terms_accepted:   bool      = Field(..., description="Must be True to register")
    marketing_opt_in: bool      = False
    newsletter_opt_in: bool     = False
    referral_source:  Optional[str] = Field(None, max_length=100)
    role:UserRoleName

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the Terms of Service to register")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


# ── SSO ───────────────────────────────────────────────────────────────────────
class SSORequest(BaseModel):
    """OAuth callback – exchange provider token for VisaFlow JWT."""
    provider:       str   = Field(..., pattern="^(google|microsoft|apple)$")
    provider_token: str   # ID token from provider
    terms_accepted: bool  = False  # required only on first login


# ── Password reset (Screens 07–10) ────────────────────────────────────────────
class PasswordResetRequestSchema(BaseModel):
    """Step 1 – user submits their email."""
    email: EmailStr


class PasswordResetVerifyOTP(BaseModel):
    """Step 2 – user submits the 6-digit OTP."""
    reset_token_id: str
    otp_code:       str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasswordResetComplete(BaseModel):
    """Step 3 – user submits new password."""
    reset_token_id:  str
    new_password:    str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# ── Generic success message ───────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str

# ADD this new one specifically for password reset request
class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token_id: uuid.UUID


import enum

class ResetTokenStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    COMPLETED = "completed"
    EXPIRED = "expired"
    LOCKED = "locked"
    CANCELLED = "cancelled"