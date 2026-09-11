# app/schemas/attorney/new_case_schemas.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional, List, Literal
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


# =============================================================================
# NEW — government filing records (LCA/DOL, petition/USCIS, RFE response,
# appeal). Separate from FileCaseRequest/FileCaseResponse above, which
# only support a single receipt_number per case — these support recording
# multiple distinct filings on the same case without overwriting each other.
# =============================================================================

class RecordFilingRequest(BaseModel):
    filing_type:    str              # "lca" | "petition" | "rfe_response" | "appeal"
    receipt_number: str
    filed_date:     date
    fee_amount:     Optional[float] = None
    notes:          Optional[str]   = None
    document_id:    Optional[uuid.UUID] = None  # id of the already-uploaded receipt file

    @field_validator("receipt_number")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("receipt_number is required")
        return v

    @field_validator("filing_type")
    @classmethod
    def valid_filing_type(cls, v: str) -> str:
        allowed = {"lca", "petition", "rfe_response", "appeal"}
        if v not in allowed:
            raise ValueError(f"filing_type must be one of {sorted(allowed)}")
        return v


class FilingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              uuid.UUID
    application_id:  uuid.UUID
    filing_type:     str
    receipt_number:  str
    filed_date:      date
    fee_amount:      Optional[float] = None
    notes:           Optional[str]   = None
    document_id:     Optional[uuid.UUID] = None
    filed_by:        uuid.UUID
    created_at:      datetime


class FilingListResponse(BaseModel):
    items: List[FilingResponse]
    total: int


class AttorneyTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    application_id: uuid.UUID
    task_name:      str
    description:    Optional[str] = None
    is_required:    bool
    is_completed:   bool
    document_id:    Optional[uuid.UUID] = None
    created_at:     datetime
    # NEW — surfaces which target the attorney originally chose, so the
    # frontend can label "Requested directly from HR" vs the ordinary
    # employee-intake flow. Not meaningful for origin="hr" tasks (always
    # "employee" there, but unused).
    target:         str = "employee"


class AttorneyTaskListResponse(BaseModel):
    items: List[AttorneyTaskResponse]
    total: int


class CompleteAttorneyTaskRequest(BaseModel):
    document_id: uuid.UUID   # the document just uploaded to fulfill this request


class AttorneyTaskCreateRequest(BaseModel):
    task_name:    str
    description:  Optional[str] = None
    is_required:  bool = False
    sort_order:   int = 0
    priority:     str = "medium"
    due_date:     Optional[date] = None
    # NEW — the attorney's choice at creation time:
    #   "employee" (default) — routed through the full HR relay: HR must
    #     assign it to the employee, the employee completes it, HR relays
    #     the completion back to the attorney.
    #   "hr" — assigned directly to HR, no employee involvement at all.
    #     HR completes it themselves; the attorney sees it in their own
    #     checklist immediately (no relay gating), tracking "Awaiting HR"
    #     -> "Completed".
    target: Literal["hr", "employee"] = "employee"