"""
employee_forms.py — Pydantic v2 schemas for EmployeeForm (I-9, I-983, ...)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FormType   = Literal["i9", "i983"]
FormStatus = Literal["draft", "submitted", "hr_approved", "needs_corrections", "approved", "completed", "archived"]


class EmployeeFormSave(BaseModel):
    """Payload for POST /employee/forms/{form_type} and PUT .../{form_id}"""
    application_id: Optional[uuid.UUID] = Field(
        None, description="Required on first save (POST). Ignored on PUT."
    )
    form_response: dict = Field(default_factory=dict, description="Whatever fields are filled so far.")


class EmployeeFormVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    form_response: dict
    status_at_snapshot: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeFormVersionListResponse(BaseModel):
    items: list[EmployeeFormVersionResponse]


class CorrectionCreate(BaseModel):
    target: Literal["employee", "hr"]
    fields: list[str] = Field(default_factory=list, description="Specific field names, e.g. ['ssn']")
    note: str = Field(..., min_length=1)


class CorrectionResponse(BaseModel):
    id: uuid.UUID
    form_type: str
    form_id: uuid.UUID
    target: str
    fields: list[str]
    note: str
    requested_by: uuid.UUID
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CorrectionListResponse(BaseModel):
    items: list[CorrectionResponse]


class EmployeeFormResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    employee_id: uuid.UUID
    form_type: FormType
    status: FormStatus
    form_response: dict
    current_version: int
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    last_action_by: Optional[uuid.UUID] = None
    last_action_by_role: Optional[str] = None
    last_action_at: Optional[datetime] = None

    # NOTE: open_corrections intentionally NOT embedded here — call
    # GET /forms/{form_type}/{form_id}/corrections separately (Option B)

    model_config = ConfigDict(from_attributes=True)


class EmployeeFormListResponse(BaseModel):
    items: list[EmployeeFormResponse]


class HRSection2Save(BaseModel):
    """HR's Section 2 (employer verification) — stored under form_response['section_2']"""
    section_2: dict = Field(default_factory=dict)