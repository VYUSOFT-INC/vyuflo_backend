# =============================================================================
# app/schemas/attorney_schemas.py
# Pydantic v2 schemas for the Select Attorney screen (Screen 20)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, computed_field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# User nested inside attorney (name + contact only)
# =============================================================================

class AttorneyUserOut(ORMBase):
    id:         uuid.UUID
    first_name: str
    last_name:  str
    email:      str
    phone:      Optional[str] = None


# =============================================================================
# AttorneyProfile — flat DB columns only
# =============================================================================

class AttorneyProfileBase(ORMBase):
    id:                 uuid.UUID
    user_id:            uuid.UUID
    bar_number:         Optional[str] = None
    bar_state:          Optional[str] = None
    years_experience:   Optional[int] = None
    law_firm_name:      Optional[str] = None
    specialisations:    Optional[str] = None   # JSON-encoded string
    languages:          Optional[str] = None   # JSON-encoded string
    availability_note:  Optional[str] = None
    max_active_cases:   Optional[int] = None
    bio:                Optional[str] = None
    profile_photo_url:  Optional[str] = None
    is_accepting_cases: bool
    is_verified:        bool
    is_active:          bool
    created_at:         datetime
    updated_at:         datetime

    # Nested
    user: Optional[AttorneyUserOut] = None


# =============================================================================
# AttorneyListItem — what the SELECT ATTORNEY screen card shows.
# Includes computed/aggregated fields injected by the service layer.
# =============================================================================

class AttorneyListItem(AttorneyProfileBase):
    """
    Returned by GET /api/v1/attorneys
    Computed fields are populated by attorney_service.enrich_attorney().
    """
    # Aggregated — set by service, not stored on the table
    rating:                   float = 0.0        # average from consultation_bookings ratings
    review_count:             int   = 0
    success_rate:             int   = 0          # 0–100 %
    total_cases:              int   = 0          # completed bookings
    consultation_fee_cents:   int   = 0          # cheapest active appointment_type price
    is_available:             bool  = True       # True if has unbooked slots in next 7 days
    distance_miles:           Optional[float] = None  # None when no ZIP given
    badges:                   List[str] = []     # ["Top Rated","Verified","Fast Response"]
    location_display:         str  = ""          # "Los Angeles, CA · 2.3 miles away"

    # Parsed lists (split client-side from JSON text)
    languages_list:           List[str] = []
    visa_types_list:          List[str] = []


# =============================================================================
# AttorneyListResponse — paginated wrapper
# =============================================================================

class AttorneyListResponse(BaseModel):
    attorneys:  List[AttorneyListItem]
    total:      int
    page:       int
    page_size:  int


# =============================================================================
# Query params schema (used inside the route, documented via FastAPI)
# =============================================================================

class AttorneySearchParams(BaseModel):
    zip_code:      Optional[str]   = None
    radius_miles:  Optional[int]   = 25
    visa_types:    Optional[List[str]] = None
    languages:     Optional[List[str]] = None
    min_rating:    Optional[float] = None
    max_fee_cents: Optional[int]   = None
    availability:  Optional[str]   = None   # "Available Now" | "Within 24h" | etc.
    sort_by:       Optional[str]   = "rating"  # "rating"|"fee_asc"|"fee_desc"|"experience"
    page:          int = 1
    page_size:     int = 50

# =============================================================================
# HR "Assign Attorney" step (case creation Step 4) — deliberately lightweight.
# No rating/fee/badges (that's Screen 20 marketplace stuff). Keyed by user_id
# because Application.assigned_attorney_id is a FK to users.id, not
# attorney_profiles.id.
# =============================================================================

class AttorneyAssignOption(BaseModel):
    user_id:              uuid.UUID
    full_name:            str
    email:                str
    profile_picture_url:  Optional[str] = None
    law_firm_name:        Optional[str] = None
    specialisations:      List[str] = []
    active_cases:         int = 0
    is_accepting:         bool = True


class AttorneyAssignListResponse(BaseModel):
    attorneys: List[AttorneyAssignOption]