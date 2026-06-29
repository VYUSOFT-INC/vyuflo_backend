# src/app/schemas/user_profile.py
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id:                   uuid.UUID
    user_id:              uuid.UUID
    full_legal_name:      Optional[str]
    nationality:          Optional[str]
    country_of_residence: Optional[str]
    date_of_birth:        Optional[date]
    gender:               Optional[str]
    profile_picture_url:  Optional[str]
    timezone:             Optional[str]
    preferred_language:   Optional[str]
    onboarding_step:      int
    onboarding_completed: bool
    created_at:           datetime
    updated_at:           datetime
    phone_number:Optional[str] = None
    country_code :Optional[str] = None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_legal_name:      Optional[str] = None
    nationality:          Optional[str] = None
    country_of_residence: Optional[str] = None
    date_of_birth:        Optional[date] = None
    gender:               Optional[str] = None
    profile_picture_url:  Optional[str] = None
    timezone:             Optional[str] = None
    preferred_language:   Optional[str] = None
    onboarding_step:      Optional[int] = None
    onboarding_completed: Optional[bool] = None
    phone_number:Optional[str] = None
    country_code :Optional[str] = None

class ProfilePictureResponse(BaseModel):
    profile_picture_url: Optional[str]

    class Config:
        from_attributes = True