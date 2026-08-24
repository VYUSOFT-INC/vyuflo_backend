"""
employee_forms.py — Pydantic v2 schemas for EmployeeForm (I-9, I-983, ...)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FormType   = Literal["i9", "i983"]
FormStatus = Literal["draft", "submitted", "archived"]


class EmployeeFormSave(BaseModel):
    """Payload for POST /employee/forms/{form_type} and PUT .../{form_id}"""
    application_id: Optional[uuid.UUID] = Field(
        None, description="Required on first save (POST). Ignored on PUT."
    )
    form_response: dict = Field(default_factory=dict, description="Whatever fields are filled so far.")


class EmployeeFormResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    employee_id: uuid.UUID
    form_type: FormType
    status: FormStatus
    form_response: dict
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeFormListResponse(BaseModel):
    items: list[EmployeeFormResponse]