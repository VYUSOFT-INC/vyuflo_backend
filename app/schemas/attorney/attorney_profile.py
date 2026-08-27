# src/app/schemas/attorney/attorney_profile.py
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttorneyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 uuid.UUID
    user_id:            uuid.UUID
    bar_number:         Optional[str] = None
    bar_state:          Optional[str] = None
    years_experience:   Optional[int] = None
    law_firm_name:      Optional[str] = None
    firm_id:            Optional[uuid.UUID] = None
    specialisations:    Optional[str] = None   # comma-separated on the frontend for now
    languages:          Optional[str] = None   # comma-separated on the frontend for now
    availability_note:  Optional[str] = None
    max_active_cases:   Optional[int] = None
    bio:                Optional[str] = None
    profile_photo_url:  Optional[str] = None
    is_accepting_cases: bool
    is_verified:        bool
    is_active:          bool
    hourly_rate_cents:            Optional[int] = None
    monthly_billing_target_cents: Optional[int] = None


class AttorneyProfileUpdate(BaseModel):
    """Partial update — only send fields you want to change."""
    bar_number:         Optional[str] = None
    bar_state:          Optional[str] = None
    years_experience:   Optional[int] = None
    law_firm_name:      Optional[str] = None
    specialisations:    Optional[str] = None
    languages:          Optional[str] = None
    availability_note:  Optional[str] = None
    max_active_cases:   Optional[int] = None
    bio:                Optional[str] = None
    is_accepting_cases: Optional[bool] = None
    hourly_rate_cents:            Optional[int] = None
    monthly_billing_target_cents: Optional[int] = None


class AttorneyPhotoResponse(BaseModel):
    profile_photo_url: Optional[str] = None