# app/schemas/hr/hr_task_schemas.py
"""
Pydantic schemas for HR task management.

HR can:
  - List tasks on any case assigned to them
  - Mark tasks complete / incomplete (on behalf of employee)
  - Add custom tasks to a case
  - Update task metadata
  - Delete custom (non-required) tasks

Uses the same ApplicationTask model as the employee flow.
Separate schemas so HR responses can include extra fields
(e.g. who_should_complete, visibility to employee).

FIXED (earlier pass): HRTaskUpdate was missing due_date even though
hr_update_task() already read payload.due_date — added below.
HRTaskResponse was missing document_status / document_rejection_reason /
document_version even though _build_response() already set all three —
added below (Pydantic v2 silently drops unknown constructor kwargs by
default, so these were being discarded on every response with no error).

NEW — relay_status / origin / target: surfaces the HR-relay state machine
(see app/services/employee/task_relay.py) to the frontend. `target`
("hr" | "employee") is the attorney's choice at task-creation time —
whether an intake request is meant for HR to handle directly, or for HR
to relay on to the employee.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──────────────────────────────────────────────────────────────────

HRTaskPriority = Literal["critical", "high", "medium", "low"]
HRTaskAssignedTo = Literal["employee", "attorney", "hr"]

# ── Request bodies ─────────────────────────────────────────────────────────

class HRTaskCreate(BaseModel):
    """POST /hr/cases/:id/tasks — HR adds a custom task to a case."""
    task_name:   str            = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_required: bool           = True
    sort_order:  int            = 0
    priority:    HRTaskPriority = "medium"
    due_date:    Optional[str]  = None    # ISO date string, stored in description metadata
    assigned_to: HRTaskAssignedTo = "employee"

    model_config = ConfigDict(from_attributes=True)


class HRTaskUpdate(BaseModel):
    """PATCH /hr/cases/:id/tasks/:task_id — update metadata."""
    task_name:   Optional[str]          = Field(None, max_length=200)
    description: Optional[str]          = Field(None, max_length=500)
    is_required: Optional[bool]         = None
    sort_order:  Optional[int]          = None
    priority:    Optional[HRTaskPriority] = None
    due_date:    Optional[str]          = None
    assigned_to: Optional[HRTaskAssignedTo] = None

    model_config = ConfigDict(from_attributes=True)


class HRTaskCompleteRequest(BaseModel):
    """PATCH /hr/cases/:id/tasks/:task_id/complete"""
    is_completed: bool
    document_id:  Optional[uuid.UUID] = None   # link to uploaded document

    model_config = ConfigDict(from_attributes=True)


# ── Response ───────────────────────────────────────────────────────────────

class HRTaskResponse(BaseModel):
    """Full task object returned to HR."""
    id:             uuid.UUID
    application_id: uuid.UUID
    task_name:      str
    description:    Optional[str]
    is_required:    bool
    is_completed:   bool
    sort_order:     int
    priority:       str                = "medium"   # decoded from description metadata
    due_date:       Optional[str]       = None
    assigned_to:    str                 = "employee"
    relay_status:   str                 = "sent_to_lawyer"
    origin:         str                 = "hr"
    target:         str                 = "employee"   # NEW — attorney's chosen target ("hr" | "employee")
    completed_at:   Optional[datetime]
    completed_by:   Optional[uuid.UUID]
    created_at:     datetime
    updated_at:     datetime

    # Linked document (when task is completed by uploading a file)
    document_id:               Optional[uuid.UUID] = None
    document_name:              Optional[str]       = None
    document_size_bytes:        Optional[int]       = None
    document_uploaded_at:       Optional[datetime]  = None
    document_status:            Optional[str]       = None
    document_rejection_reason:  Optional[str]       = None
    document_version:           Optional[int]       = None

    model_config = ConfigDict(from_attributes=True)