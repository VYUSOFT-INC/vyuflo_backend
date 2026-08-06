# app/schemas/hr/hr_document_request_schemas.py
#
# "Request from Employee" — HR asks the employee to upload a specific
# document. Backed by the existing `document_requests` table
# (visamodels.DocumentRequest) — no new table needed.

import uuid
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

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


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────────────────────────────────────

class DocumentRequestCreate(BaseModel):
    """
    POST /hr/cases/{application_id}/documents/requests

    HR asks the case's employee to upload a document that isn't on file yet
    (or needs to be replaced). Fires a Notification to the employee.
    """
    document_name: str = Field(
        ..., min_length=2, max_length=200,
        description="e.g. 'Updated Resume', 'Form W-2 (2024)', 'Degree Certificate'"
    )
    details: str = Field(
        ..., min_length=1, max_length=2000,
        description="Why it's needed, or what's wrong with the current one"
    )
    priority: DocumentRequestPriority = DocumentRequestPriority.normal
    due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class DocumentRequestResponse(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    requested_by:   uuid.UUID
    requested_from: uuid.UUID
    document_name:  str
    details:        str
    priority:       DocumentRequestPriority
    due_date:       Optional[date]
    status:         DocumentRequestStatus
    document_id:    Optional[uuid.UUID]     # filled in once the employee uploads it
    fulfilled_at:   Optional[datetime]
    created_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRequestListResponse(BaseModel):
    items: List[DocumentRequestResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
