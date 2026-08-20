# src/app/schemas/employer/company_profile.py
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompanyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    user_id:       uuid.UUID
    company_name:  str
    company_size:  Optional[str] = None
    industry:      Optional[str] = None
    website:       Optional[str] = None
    domain:        Optional[str] = None
    ein:           Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city:          Optional[str] = None
    state:         Optional[str] = None
    zip_code:      Optional[str] = None
    country:       Optional[str] = None
    contact_name:  Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url:      Optional[str] = None
    is_verified:   bool
    is_active:     bool


class CompanyProfileUpdate(BaseModel):
    """Partial update — only send fields you want to change."""
    company_name:  Optional[str] = None
    company_size:  Optional[str] = None  # "1_10" | "11_50" | "51_200" | "201_500" | "501_1000" | "1000_plus"
    industry:      Optional[str] = None
    website:       Optional[str] = None
    domain:        Optional[str] = None
    ein:           Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city:          Optional[str] = None
    state:         Optional[str] = None
    zip_code:      Optional[str] = None
    country:       Optional[str] = None
    contact_name:  Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class CompanyLogoResponse(BaseModel):
    logo_url: Optional[str] = None