from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


class NewCaseCreateRequest(BaseModel):
    client_user_id:  uuid.UUID
    visa_type_code:  str
    case_name:       str
    target_date:     Optional[date] = None
    priority:        str = "standard"
    source:          str = "consultation"

    @field_validator("case_name")
    @classmethod
    def name_len(cls, v: str) -> str:
        if len(v.strip()) < 3 or len(v) > 200:
            raise ValueError("case_name must be 3-200 characters")
        return v.strip()

    @field_validator("priority")
    @classmethod
    def valid_priority(cls, v: str) -> str:
        if v not in ("standard", "urgent", "premium"):
            raise ValueError("priority must be 'standard', 'urgent', or 'premium'")
        return v


class NewCaseCreateResponse(BaseModel):
    id:          uuid.UUID
    case_number: str          # your real application_number, e.g. "VF-3A9F21C0"
    case_name:   str
    status:      str
    created_at:  datetime
    message:     str


class ConsultedClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id:            uuid.UUID
    full_name:          str
    email:              str
    last_consulted_iso: datetime
    visa_hint:          Optional[str] = None

class FileCaseRequest(BaseModel):
    receipt_number: str
    priority_date:  date

    @field_validator("receipt_number")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("receipt_number is required")
        return v


class FileCaseResponse(BaseModel):
    id:                   uuid.UUID
    receipt_number:       str
    priority_date:        date
    case_pipeline_stage:  str
    message:              str