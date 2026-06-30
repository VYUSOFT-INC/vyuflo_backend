# =============================================================================
# app/schemas/screen13_schemas.py
# Screen 13 — Profile & Settings
#
# Covers:
#   A. Profile Information   → ProfileResponse, ProfileUpdateRequest,
#                               AttorneyProfileUpdateRequest, AvatarUpdateResponse
#
#   B. Notification Prefs    → NO NEW SCHEMAS — reuse existing
#                               NotificationPreferencesOut + UpdatePreferencesRequest
#                               from app/schemas/notification_schemas.py
#                               Existing GET/PATCH /notifications/preferences
#                               endpoints are REUSED AS-IS (no new endpoints).
#                               Frontend maps columns using Option A:
#                                 "Pending Reviews"  in-app → notify_document_updates
#                                 "Pending Reviews"  email  → email_enabled
#                                 "Action Required"  in-app → notify_case_updates
#                                 "Action Required"  email  → email_enabled
#                                 "New Messages"     in-app → push_enabled
#                                 "New Messages"     email  → email_enabled
#
#   C. AI Extraction         → Skipped (already done by colleague)
# =============================================================================

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# A. PROFILE INFORMATION
# =============================================================================

class ProfileResponse(BaseModel):
    """
    Response for GET /users/me/profile.
    Aggregated from: users + user_profiles + attorney_profiles.
    """
    model_config = ConfigDict(from_attributes=True)

    # users table
    id:         uuid.UUID
    first_name: str
    last_name:  str
    email:      str

    # user_profiles table
    profile_picture_url: Optional[str] = None
    timezone:            Optional[str] = None
    preferred_language:  Optional[str] = None

    # attorney_profiles table (None for non-attorney users)
    bar_number:    Optional[str] = None
    bar_state:     Optional[str] = None
    law_firm_name: Optional[str] = None

     # ── ADDED: Screen 25 - Lawyer Dashboard ──────────────────────────────────
    monthly_billing_target_cents: Optional[int] = Field(
        None,
        description=(
            "Monthly billing target in US cents. e.g. 1500000 = $15,000. "
            "Powers 'Target: $15,000' on Screen 25 Monthly Billing panel."
        ),
    )
    # ─────────────────────────────────────────────────────────────────────────

    # computed from user_roles → roles
    role: Optional[str] = None   # e.g. "Senior Reviewer"


class ProfileUpdateRequest(BaseModel):
    """
    PATCH /users/me/profile — "Save Changes" button.
    All fields optional — only provided fields are written.
    Writes to: users (first_name, last_name) + user_profiles (timezone, preferred_language).
    """
    first_name:         Optional[str] = None
    last_name:          Optional[str] = None
    timezone:           Optional[str] = None
    preferred_language: Optional[str] = None


class AttorneyProfileUpdateRequest(BaseModel):
    """
    PATCH /users/me/attorney-profile — Bar Association ID field.
    All fields optional — only provided fields are written.
    Writes to: attorney_profiles table.
    """
    bar_number:    Optional[str] = None   # "Bar Association ID" field on Screen 13
    bar_state:     Optional[str] = None
    law_firm_name: Optional[str] = None
    bio:           Optional[str] = None

    # ── ADDED: Screen 25 - Lawyer Dashboard ──────────────────────────────────
    monthly_billing_target_cents: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Monthly billing target in US cents. e.g. 1500000 = $15,000. "
            "Attorney sets this from their dashboard billing panel."
        ),
    )
    # ─────────────────────────────────────────────────────────────────────────
 


class AvatarUpdateResponse(BaseModel):
    """Response for PATCH /users/me/avatar and DELETE /users/me/avatar."""
    profile_picture_url: Optional[str] = None
    message: str
