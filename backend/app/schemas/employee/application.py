
"""
schemas.py — Pydantic v2 schemas for:
  • Application
  • ApplicationStatusHistory
  • ApplicationTask
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Shared enums (mirrored from SQLAlchemy Enum columns)
# ---------------------------------------------------------------------------

ApplicationStatus = Literal[
    "draft",
    "in_progress",
    "action_needed",
    "rfe_response",
    "submitted",
    "approved",
    "rejected",
    "withdrawn",
]

ApplicationStage = Literal[
    "profile_eligibility",
    "documentation",
    "lca_filing",
    "uscis_submission",
]


# ===========================================================================
# APPLICATION SCHEMAS
# ===========================================================================


class ApplicationCreate(BaseModel):
    """
    Payload for POST /applications
    Mirrors the "New Application" button from the My-Applications screen.
    """

    visa_type_id: uuid.UUID = Field(..., description="FK → visa_types.id")
    sponsor_employer: Optional[str] = Field(None, max_length=200)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    assigned_attorney_id: Optional[uuid.UUID] = None
    assigned_hr_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    is_draft: bool = True

    model_config = ConfigDict(from_attributes=True)


class ApplicationUpdate(BaseModel):
    """
    Payload for PATCH /applications/{application_id}
    All fields optional — partial update.
    """

    sponsor_employer: Optional[str] = Field(None, max_length=200)
    status: Optional[ApplicationStatus] = None
    current_stage: Optional[ApplicationStage] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    submission_date: Optional[datetime] = None
    is_draft: Optional[bool] = None
    has_action_required: Optional[bool] = None
    action_required_note: Optional[str] = Field(None, max_length=500)
    assigned_attorney_id: Optional[uuid.UUID] = None
    assigned_hr_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationStatusUpdate(BaseModel):
    """
    Payload for PATCH /applications/{application_id}/status
    Dedicated endpoint so status changes always create a history record.
    """

    status: ApplicationStatus
    current_stage: Optional[ApplicationStage] = None
    note: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


# ADD this new schema at the top of the file (before ApplicationResponse)
class VisaTypeBasic(BaseModel):
    id:   uuid.UUID
    name: str    # "H-1B Specialty Occupation"
    code: str    # "H-1B"

    model_config = ConfigDict(from_attributes=True)


# UPDATE ApplicationResponse — add one field at the bottom
class ApplicationResponse(BaseModel):
    id: uuid.UUID
    application_number: str
    user_id: uuid.UUID
    visa_type_id: uuid.UUID
    sponsor_employer: Optional[str]
    status: ApplicationStatus
    current_stage: Optional[ApplicationStage]
    progress_percent: int
    start_date: Optional[date]
    due_date: Optional[date]
    submission_date: Optional[datetime]
    is_draft: bool
    has_action_required: bool
    action_required_note: Optional[str]
    assigned_attorney_id: Optional[uuid.UUID]
    assigned_hr_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_by: uuid.UUID
    modified_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    visa_type: Optional[VisaTypeBasic] = None   # ← ADD THIS ONE LINE

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    items:         List[ApplicationResponse]
    total:         int
    in_progress:   int    # ← flat, not nested
    action_needed: int
    approved:      int

    model_config = ConfigDict(from_attributes=True)
    
# class ApplicationResponse(BaseModel):
#     """Full representation returned to the client."""

#     id: uuid.UUID
#     application_number: str
#     user_id: uuid.UUID
#     visa_type_id: uuid.UUID
#     sponsor_employer: Optional[str]
#     status: ApplicationStatus
#     current_stage: Optional[ApplicationStage]
#     progress_percent: int
#     start_date: Optional[date]
#     due_date: Optional[date]
#     submission_date: Optional[datetime]
#     is_draft: bool
#     has_action_required: bool
#     action_required_note: Optional[str]
#     assigned_attorney_id: Optional[uuid.UUID]
#     assigned_hr_id: Optional[uuid.UUID]
#     notes: Optional[str]
#     created_by: uuid.UUID
#     modified_by: Optional[uuid.UUID]
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)


# class ApplicationListResponse(BaseModel):
#     """
#     Used by GET /applications — KPI summary row + paginated cards
#     (matches the My-Applications screen: Total / In Progress / Action Needed / Approved).
#     """
#     items: List[ApplicationResponse]
#     total: int
#     in_progress: int
#     action_needed: int
#     approved: int
    

#     model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# APPLICATION STATUS HISTORY SCHEMAS
# ===========================================================================


class StatusHistoryCreate(BaseModel):
    """
    Internal schema — created automatically whenever status changes.
    Exposed via POST /applications/{application_id}/status-history
    for manual entries (e.g. attorney notes).
    """

    stage: ApplicationStage
    status: ApplicationStatus
    note: Optional[str] = Field(None, max_length=500)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StatusHistoryResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    stage: ApplicationStage
    status: ApplicationStatus
    note: Optional[str]
    completed_at: Optional[datetime]
    changed_by: uuid.UUID
    created_by: uuid.UUID
    modified_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# APPLICATION TASK SCHEMAS
# ===========================================================================


class TaskCreate(BaseModel):
    """POST /applications/{application_id}/tasks"""

    task_name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_required: bool = True
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """PATCH /applications/{application_id}/tasks/{task_id}"""

    task_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_required: Optional[bool] = None
    sort_order: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# UPDATE TaskResponse — add document fields
class TaskResponse(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    task_name:      str
    description:    Optional[str]
    is_required:    bool
    is_completed:   bool
    sort_order:     int
    completed_at:   Optional[datetime]
    completed_by:   Optional[uuid.UUID]
    created_at:     datetime
    updated_at:     datetime
    document_id:          Optional[uuid.UUID] = None
    document_name:        Optional[str]       = None   # file_name from Document
    document_size_bytes:  Optional[int]       = None   # file_size_kb * 1024
    document_uploaded_at: Optional[datetime]  = None   # document.created_at

    model_config = ConfigDict(from_attributes=True)


# UPDATE TaskCompleteRequest — add document_id
class TaskCompleteRequest(BaseModel):
    is_completed: bool
    document_id:  Optional[uuid.UUID] = None   # ← ADD