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
    pending   = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class DocumentRequestCreate(BaseModel):
    application_id: uuid.UUID
    document_name:  str = Field(..., max_length=200, description="e.g. Form W-2 (2024)")
    details:        str = Field(..., description="Details / Reason shown to the client")
    priority:       DocumentRequestPriority = DocumentRequestPriority.normal
    due_date:       Optional[date] = None


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
    created_at:      datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRequestListResponse(BaseModel):
    items: list[DocumentRequestResponse]
    total: int
