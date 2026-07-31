"""
intake.py  (schema)
Path: app/schemas/attorney/intake.py

V1 Pydantic schemas — Client Intake Form + Client Profile (Screen 26).
Style matches role.py (Pydantic v2, ConfigDict, from_attributes).

Changes vs previous version:
  • passport_expiry_date added to IntakeDataSave + IntakeDataResponse
  • ClientProfileResponse added for Screen 26
    - billing_summary now uses real Fee table data (amount_usd in cents → dollars)
    - recent_activity uses real AuditLog data
    - next_deadline_days uses real Deadline table
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ===========================================================================
# PREVIOUS VISA — item inside the JSON column
# ===========================================================================

class PreviousVisaItem(BaseModel):
    visa_type:       Optional[str]  = Field(None, max_length=50, examples=["F1", "B1/B2"])
    visa_number:     Optional[str]  = Field(None, max_length=50)
    issue_date:      Optional[date] = None
    expiry_date:     Optional[date] = None
    issuing_country: Optional[str]  = Field(None, max_length=100)


# ===========================================================================
# INTAKE DATA — Step 1 (Personal Info) + Step 3 (Immigration History)
# ===========================================================================

class IntakeDataSave(BaseModel):
    """
    PUT /intake/sessions/{session_id}/data
    All fields Optional — partial saves and drafts work at any time.
    """
    # Step 1 — Personal Info (Screen 04)
    first_name:           Optional[str]      = Field(None, max_length=100)
    last_name:            Optional[str]      = Field(None, max_length=100)
    date_of_birth:        Optional[date]     = None
    gender:               Optional[str]      = Field(None, max_length=20)
    nationality:          Optional[str]      = Field(None, max_length=100)
    passport_number:      Optional[str]      = Field(None, max_length=50)
    passport_expiry_date: Optional[date]     = None
    email:                Optional[EmailStr] = None

    # Step 3 — Immigration History (Screen 03)
    current_visa_status:  Optional[str]  = Field(None, max_length=50)
    visa_expiration_date: Optional[date] = None
    has_visa_denial:      Optional[bool] = None
    visa_denial_details:  Optional[str]  = None
    has_overstay:         Optional[bool] = None
    previous_visas:       Optional[List[PreviousVisaItem]] = None


class IntakeDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   uuid.UUID
    intake_session_id:    uuid.UUID

    # Step 1
    first_name:           Optional[str]
    last_name:            Optional[str]
    date_of_birth:        Optional[date]
    gender:               Optional[str]
    nationality:          Optional[str]
    passport_number:      Optional[str]
    passport_expiry_date: Optional[date]
    email:                Optional[str]

    # Step 3
    current_visa_status:  Optional[str]
    visa_expiration_date: Optional[date]
    has_visa_denial:      Optional[bool]
    visa_denial_details:  Optional[str]
    has_overstay:         Optional[bool]
    previous_visas:       List[PreviousVisaItem] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime


# ===========================================================================
# SESSION
# ===========================================================================

class IntakeSessionCreate(BaseModel):
    application_id: uuid.UUID
    generate_link:  bool = Field(
        default=False,
        description="Set true to also generate the client link token immediately",
    )


class IntakeSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    application_id:   uuid.UUID
    token:            Optional[str]
    token_expires_at: Optional[datetime]
    current_step:     int
    step_1_completed: bool
    step_2_completed: bool
    step_3_completed: bool
    step_4_completed: bool
    step_5_completed: bool
    is_draft:         bool
    last_saved_at:    Optional[datetime]
    is_submitted:     bool
    submitted_at:     Optional[datetime]
    created_at:       datetime
    updated_at:       datetime
    intake_data:      Optional[IntakeDataResponse] = None


# ===========================================================================
# GENERATE LINK
# ===========================================================================

class GenerateLinkResponse(BaseModel):
    token:            str
    client_url:       str
    token_expires_at: datetime


# ===========================================================================
# SAVE DRAFT
# ===========================================================================

class SaveDraftResponse(BaseModel):
    detail:        str
    last_saved_at: datetime
    current_step:  int


# ===========================================================================
# SUBMIT
# ===========================================================================

class SubmitIntakeResponse(BaseModel):
    detail:       str
    submitted_at: datetime
    session_id:   uuid.UUID


# ===========================================================================
# VISA STATUS OPTIONS — dropdown
# ===========================================================================

class VisaStatusOption(BaseModel):
    value: str
    label: str


class VisaStatusOptionsResponse(BaseModel):
    items: List[VisaStatusOption]


# ===========================================================================
# CLIENT PROFILE — Screen 26
# ===========================================================================

class ActiveCaseSnapshot(BaseModel):
    """Active case card — left column of Screen 26 Overview tab."""
    case_id:          uuid.UUID
    case_number:      str                   # application_number from applications table
    visa_type_name:   Optional[str]         # from visa_types.name via application.visa_type
    status:           str
    progress_percent: int                   # application.progress_percent
    current_stage:    Optional[str]         # application.current_stage
    due_date:         Optional[date]        # application.due_date


class BillingSummarySnapshot(BaseModel):
    """Billing summary — right column of Screen 26. Sourced from fees table."""
    total_billed:  float = 0.0   # sum of all fees for this client (cents → dollars)
    total_paid:    float = 0.0   # sum of fees where status='paid'
    outstanding:   float = 0.0   # total_billed - total_paid


class ActivityItem(BaseModel):
    """One row in Recent Activity. Sourced from audit_logs table."""
    action:      str            # audit_logs.action  e.g. "document.uploaded"
    description: Optional[str] # audit_logs.description
    occurred_at: datetime       # audit_logs.created_at


class ClientProfileResponse(BaseModel):
    """
    GET /clients/{client_id}/profile — Screen 26 aggregated read-only view.

    Sources:
      users                       → name, email, phone, client_since
      intake_immigration_history  → visa status, nationality, passport info
      applications                → total_cases, active_cases, active_case card
      deadlines                   → next_deadline_days
      fees                        → billing_summary (real data, not zeros)
      audit_logs                  → recent_activity (last 3 entries for this user)
    """
    # Hero section
    client_id:   uuid.UUID
    full_name:   str
    initials:    str
    email:       str
    phone:       Optional[str]

    # Visa badge + sub-header
    current_visa_status: Optional[str]  # e.g. "H1B" → UI renders "H-1B Active"
    location:            Optional[str]  # V1: always null
    employer:            Optional[str]  # V1: always null
    job_title:           Optional[str]  # V1: always null
    client_since:        datetime

    # Contact & Details card
    nationality:          Optional[str]
    passport_number:      Optional[str]
    passport_expiry_date: Optional[date]

    # Stats ribbon
    total_cases:        int   = 0
    active_cases:       int   = 0
    unbilled_amount:    float = 0.0   # fees outstanding
    next_deadline_days: Optional[int] = None

    # Overview tab cards
    active_case:     Optional[ActiveCaseSnapshot]
    billing_summary: BillingSummarySnapshot = Field(default_factory=BillingSummarySnapshot)
    recent_activity: List[ActivityItem]     = Field(default_factory=list)

class AssignedApplicationResponse(BaseModel):
    """
    Row in the lawyer's worklist (Client Intake landing page).

    Returned by GET /lawyer/applications. One per Application assigned
    to the logged-in attorney. Includes intake session status so the
    UI can render 'Start Intake' vs 'Continue Intake' vs 'View Submission'.
    """

    application_id:    uuid.UUID                         = Field(..., description="Application UUID")
    client_name:       str                               = Field(..., description="Full name of the applicant")
    client_email:      str                               = Field(default="",  description="Applicant email")
    user_id:           Optional[uuid.UUID] = Field(default=None, description="Client's user UUID")  # ← ADD THIS


    visa_type:         Optional[str]                     = Field(default=None, description="Visa code, e.g. 'H1B'")
    visa_type_label:   Optional[str]                     = Field(default=None, description="Human-readable visa name")

    status: Literal["pending_intake", "intake_in_progress", "intake_completed"] = Field(
        ..., description="Intake session state"
    )

    intake_session_id: Optional[uuid.UUID]               = Field(default=None, description="None if no session yet")
    intake_step:       Optional[int]                     = Field(default=None, ge=1, le=5)
    assigned_at:       datetime                          = Field(..., description="When the application was created/assigned")
    hr_reviewed_by:    Optional[str]                     = Field(default=None, description="HR reviewer name (V1: nullable)")

    model_config = ConfigDict(from_attributes=True)