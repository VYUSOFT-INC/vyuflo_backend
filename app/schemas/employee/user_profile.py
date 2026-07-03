# ─────────────────────────────────────────────────────────────────────────────
# src/app/schemas/user_profile.py  (updated)
#
# WHAT CHANGED:  Added `theme_color` to UserProfileUpdate and UserProfileResponse.
# The existing PATCH /users/me/profile service already does:
#     update_data = payload.model_dump(exclude_none=True)
#     await db_update(db, UserProfile, profile.id, update_data)
# So adding the field here is all the backend needs — no router or service edits.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Shared validator ─────────────────────────────────────────────────────────

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ── Response ─────────────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    id:                   uuid.UUID
    user_id:              uuid.UUID
    full_legal_name:      Optional[str]  = None
    nationality:          Optional[str]  = None
    country_of_residence: Optional[str]  = None
    date_of_birth:        Optional[date] = None
    gender:               Optional[str]  = None
    profile_picture_url:  Optional[str]  = None
    timezone:             Optional[str]  = None
    preferred_language:   Optional[str]  = None
    phone_number:         Optional[str]  = None
    country_code:         Optional[str]  = None
    onboarding_step:      int            = 1
    onboarding_completed: bool           = False

    # ← NEW
    theme_color:          Optional[str]  = None

    employer_id:          Optional[uuid.UUID] = None
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}


# ── Update (PATCH body) ─────────────────────────────────────────────────────

class UserProfileUpdate(BaseModel):
    full_legal_name:      Optional[str]  = None
    nationality:          Optional[str]  = None
    country_of_residence: Optional[str]  = None
    date_of_birth:        Optional[date] = None
    gender:               Optional[str]  = None
    profile_picture_url:  Optional[str]  = None
    timezone:             Optional[str]  = None
    preferred_language:   Optional[str]  = None
    phone_number:         Optional[str]  = None
    country_code:         Optional[str]  = None
    onboarding_step:      Optional[int]  = None
    onboarding_completed: Optional[bool] = None

    # ← NEW — validated 7-char hex
    theme_color:          Optional[str]  = Field(None, max_length=7)

    @field_validator("theme_color")
    @classmethod
    def validate_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _HEX_RE.match(v):
            raise ValueError("theme_color must be a valid hex like #4f46e5")
        return v


# ── Profile picture ─────────────────────────────────────────────────────────

class ProfilePictureResponse(BaseModel):
    profile_picture_url: Optional[str] = None