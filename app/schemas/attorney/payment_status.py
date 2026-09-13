# app/schemas/attorney/payment_status.py

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

FILING_TYPES = {"lca", "petition", "rfe_response", "appeal"}


class PaymentStatusCreate(BaseModel):
    """POST /lawyer/applications/{id}/payment-status — attorney marks a
    payment as currently in progress. No receipt number yet — that comes
    later via the existing RecordFilingRequest once the filing is actually
    complete."""
    filing_type: str
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("filing_type")
    @classmethod
    def valid_filing_type(cls, v: str) -> str:
        if v not in FILING_TYPES:
            raise ValueError(f"filing_type must be one of {sorted(FILING_TYPES)}")
        return v


class PaymentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     uuid.UUID
    application_id:         uuid.UUID
    filing_type:            str
    note:                   Optional[str] = None
    created_by_user:        uuid.UUID
    created_by_name:        str = "Attorney"   # populated by the service, not from_attributes
    relayed_to_employee_at: Optional[datetime] = None
    relayed_to_employee_by: Optional[uuid.UUID] = None
    created_at:             datetime


class PaymentStatusListResponse(BaseModel):
    items: List[PaymentStatusResponse]
    total: int