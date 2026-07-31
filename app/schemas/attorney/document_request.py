import uuid
from datetime import date, datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class DocumentRequestPriority(str, Enum):
    low    = "low"
    normal = "normal"
    high   = "high"
    urgent = "urgent"


class DocumentRequestStatus(str, Enum):
    pending             = "pending"              # visible to the employee, awaiting their upload
    pending_hr_approval = "pending_hr_approval"  # attorney created it — sitting with HR, employee doesn't know yet
    fulfilled           = "fulfilled"
    cancelled           = "cancelled"             # withdrawn by whoever created it
    declined            = "declined"              # HR declined an attorney's request


class DocumentRequestCreate(BaseModel):
    application_id: uuid.UUID
    document_name:  str = Field(..., max_length=200, description="e.g. Form W-2 (2024)")
    details:        str = Field(..., description="Details / Reason shown to the client")
    priority:       DocumentRequestPriority = DocumentRequestPriority.normal
    due_date:       Optional[date] = None


class HRReviewDecision(str, Enum):
    approve = "approve"
    decline = "decline"


class HRReviewDocumentRequest(BaseModel):
    """
    PATCH /documents/requests/{request_id}/hr-review

    HR's decision on an attorney-created request that's sitting in
    'pending_hr_approval'. `reason` is required when declining.
    """
    decision: HRReviewDecision
    reason:   Optional[str] = Field(None, max_length=1000)


class DocumentRequestResponse(BaseModel):
    id:              uuid.UUID
    application_id:  uuid.UUID
    requested_by:    uuid.UUID
    requested_from:  uuid.UUID
    document_name:   str
    details:         str
    priority:        DocumentRequestPriority
    due_date:        Optional[date]
    status:          DocumentRequestStatus
    document_id:     Optional[uuid.UUID]
    fulfilled_at:    Optional[datetime]

    # ── HR-relay tracking — populated only for attorney-created requests
    #    that went through pending_hr_approval ─────────────────────────────────
    hr_reviewed_by:     Optional[uuid.UUID] = None
    hr_reviewed_at:     Optional[datetime]  = None
    hr_decision_reason: Optional[str]       = None

    created_at:      datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRequestListResponse(BaseModel):
    items: list[DocumentRequestResponse]
    total: int
