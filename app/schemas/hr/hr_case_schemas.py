# app/schemas/hr/hr_case_schemas.py
"""
Pydantic v2 schemas for HR-initiated case creation.

Key differences from employee ApplicationCreate:
  - HR selects an employee from their roster (employee_link_id → resolves user_id)
  - HR selects visa by code ("H-1B"), backend resolves to visa_type_id UUID
  - HR sets case_name (stored in application.notes), priority, target_date
  - HR optionally assigns an attorney at creation time
  - assigned_hr_id is always the current HR user (set by service, not the client)
  - Duplicate check is per employee+visa, not per logged-in user+visa
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ────────────────────────────────────────────────────────────────────

HRCasePriority = Literal["standard", "urgent", "premium"]

HRCaseStatus = Literal[
    "draft",
    "in_progress",
    "action_needed",
    "rfe_response",
    "submitted",
    "approved",
    "rejected",
    "withdrawn",
]

HRCaseStage = Literal[
    "profile_eligibility",
    "documentation",
    "lca_filing",
    "uscis_submission",
]

HRApprovalStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "changes_requested",
]


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class HRCaseCreate(BaseModel):
    """
    POST /hr/cases
    HR creates an immigration case on behalf of an employee.

    Frontend sends:
      - employee_link_id  → employer_employees.id  (from HREmployees roster)
      - visa_type_code    → "H-1B", "L-1A", etc.   (backend resolves to UUID)
      - case_name         → stored in application.notes
      - Everything else is optional
    """

    # ── Required ──────────────────────────────────────────────────────────────
    employee_link_id: uuid.UUID = Field(
        ...,
        description="employer_employees.id — identifies which linked employee to sponsor"
    )
    visa_type_code: str = Field(
        ...,
        max_length=20,
        description="Visa code e.g. 'H-1B', 'L-1A', 'O-1', 'TN', 'E-3'"
    )
    case_name: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Human-readable label e.g. 'David Chen - H-1B 2025'"
    )

    # ── Case meta ─────────────────────────────────────────────────────────────
    case_description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Internal context — visible to HR and attorney, NOT the employee"
    )
    target_date: Optional[date] = Field(
        None,
        description="Desired USCIS submission date — stored as due_date on Application"
    )
    priority: HRCasePriority = Field(
        "standard",
        description="standard | urgent | premium"
    )
    internal_notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="HR-only internal notes — stored in application.notes"
    )

    # ── Assignment ────────────────────────────────────────────────────────────
    attorney_user_id: Optional[uuid.UUID] = Field(
        None,
        description="users.id of the immigration attorney to assign. Optional at creation."
    )
    sponsor_employer: Optional[str] = Field(
        None,
        max_length=200,
        description="Override company name shown on the petition. Defaults to EmployerProfile.company_name."
    )

    model_config = ConfigDict(from_attributes=True)


class HRCaseUpdate(BaseModel):
    """
    PATCH /hr/cases/{application_id}
    HR updates fields on an existing case.
    All fields optional — partial update.
    """
    case_name:           Optional[str]          = Field(None, max_length=300)
    case_description:    Optional[str]           = Field(None, max_length=2000)
    target_date:         Optional[date]          = None
    priority:            Optional[HRCasePriority] = None
    internal_notes:      Optional[str]           = Field(None, max_length=2000)
    attorney_user_id:    Optional[uuid.UUID]     = None
    sponsor_employer:    Optional[str]           = Field(None, max_length=200)
    has_action_required: Optional[bool]          = None
    action_required_note: Optional[str]          = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class HRCaseStatusUpdate(BaseModel):
    """
    PATCH /hr/cases/{application_id}/status
    HR manually changes the application status.
    Always appends an immutable history row.
    """
    status:        HRCaseStatus
    current_stage: Optional[HRCaseStage] = None
    note:          Optional[str]         = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class HRApprovalUpdate(BaseModel):
    """
    PATCH /hr/cases/{application_id}/hr-approval
    HR formally approves or rejects the application before attorney filing.
    """
    hr_approval_status: HRApprovalStatus
    hr_notes:           Optional[str] = Field(None, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class HRCaseListQuery(BaseModel):
    """
    Query params for GET /hr/cases
    Used internally by the service layer.
    """
    status:           Optional[HRCaseStatus]  = None
    visa_type_code:   Optional[str]           = None
    employee_user_id: Optional[uuid.UUID]     = None
    attorney_user_id: Optional[uuid.UUID]     = None
    limit:            int                     = Field(50, ge=1, le=200)
    offset:           int                     = Field(0, ge=0)

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class VisaTypeBasic(BaseModel):
    id:   uuid.UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class EmployeeBasic(BaseModel):
    """Minimal employee info nested inside case responses."""
    user_id:             uuid.UUID
    full_name:           str
    email:               str
    job_title:           Optional[str]
    department:          Optional[str]
    profile_picture_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AttorneyBasic(BaseModel):
    """Minimal attorney info nested inside case responses."""
    user_id:        uuid.UUID
    full_name:      str
    email:          str
    law_firm_name:  Optional[str]

    model_config = ConfigDict(from_attributes=True)


class HRCaseResponse(BaseModel):
    """
    Full case representation returned to HR.
    Includes nested employee and visa_type objects for display
    without additional lookups on the frontend.
    """
    # ── Core application fields ───────────────────────────────────────────────
    id:                   uuid.UUID
    application_number:   str
    status:               HRCaseStatus
    current_stage:        Optional[HRCaseStage]
    progress_percent:     int
    is_draft:             bool
    has_action_required:  bool
    action_required_note: Optional[str]

    # ── Dates ─────────────────────────────────────────────────────────────────
    start_date:      Optional[date]
    due_date:        Optional[date]        # = target_date from HRCaseCreate
    submission_date: Optional[datetime]

    # ── HR-specific fields ────────────────────────────────────────────────────
    case_name:           str               # from application.notes first line
    case_description:    Optional[str]     # from application.hr_notes
    priority:            str               # from application.notes metadata
    internal_notes:      Optional[str]
    sponsor_employer:    Optional[str]
    hr_approval_status:  Optional[HRApprovalStatus]
    hr_notes:            Optional[str]
    hr_approved_at:      Optional[datetime]

    # ── Assignments ───────────────────────────────────────────────────────────
    assigned_hr_id:       uuid.UUID
    assigned_attorney_id: Optional[uuid.UUID]

    # ── Nested objects (populated by joinedload) ──────────────────────────────
    visa_type:  Optional[VisaTypeBasic]  = None
    employee:   Optional[EmployeeBasic]  = None
    attorney:   Optional[AttorneyBasic]  = None

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HRCaseListResponse(BaseModel):
    """
    GET /hr/cases — KPI summary + paginated case cards.
    """
    items:          List[HRCaseResponse]
    total:          int

    # KPI counts across all HR's cases (unfiltered)
    total_active:      int    # in_progress + action_needed + rfe_response + submitted
    action_needed:     int
    approved_ytd:      int
    expiring_soon:     int    # due_date within 30 days

    model_config = ConfigDict(from_attributes=True)


class HRCaseStatusHistoryResponse(BaseModel):
    """Single row from application_status_history."""
    id:             uuid.UUID
    application_id: uuid.UUID
    stage:          HRCaseStage
    status:         HRCaseStatus
    note:           Optional[str]
    completed_at:   Optional[datetime]
    changed_by:     uuid.UUID
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class HRCaseCreateResponse(BaseModel):
    """
    Slimmer response for the creation endpoint specifically.
    Frontend uses this to navigate to the new case detail page.
    """
    id:                 uuid.UUID
    application_number: str
    message:            str
    employee_name:      str
    visa_type_code:     str

    model_config = ConfigDict(from_attributes=True)