# app/schemas/hr/hr_approval_schemas.py
#
# Pydantic schemas for HR Approval Queue endpoints.
# These match the TypeScript types in src/types/hr/hrApproval.types.ts

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalItemStatus(str, Enum):
    pending          = "pending"
    approved         = "approved"
    edits_requested  = "edits_requested"


class ApprovalItemPriority(str, Enum):
    critical = "critical"
    high     = "high"
    medium   = "medium"
    low      = "low"


class ApprovalItemDocType(str, Enum):
    letter      = "letter"
    form        = "form"
    document    = "document"
    certificate = "certificate"


# ─────────────────────────────────────────────────────────────────────────────
# NESTED SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalCommentResponse(BaseModel):
    author: str
    role:   str
    time:   str    # relative time string e.g. "3 hours ago"
    text:   str


class ApprovalRevisionResponse(BaseModel):
    version: str   # "v1", "v2", "v3"
    label:   str   # "Original Version", "Current Version"
    author:  str
    time:    str


class ApprovalExtractedFieldResponse(BaseModel):
    label: str
    value: str


class ApprovalActionNoteResponse(BaseModel):
    type:  str    # "warning" | "edit"
    title: str
    body:  str


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalItemResponse(BaseModel):
    id:            uuid.UUID
    title:         str
    priority:      ApprovalItemPriority
    doc_type:      ApprovalItemDocType
    visa_type:     str
    employee_name: str
    case_number:   str
    submitted_ago: str      # relative time string from backend
    description:   str
    status:        ApprovalItemStatus

    ai_confidence:    int
    ai_note:          str
    extracted_label:  str
    extracted_fields: list[ApprovalExtractedFieldResponse]

    action_note:   Optional[ApprovalActionNoteResponse]
    comments:      Optional[list[ApprovalCommentResponse]]
    revisions:     Optional[list[ApprovalRevisionResponse]]
    comment_count: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class ApprovalStatsResponse(BaseModel):
    pending:             int
    approved_today:      int
    edits_requested:     int
    avg_response_hours:  float


class ApprovalListResponse(BaseModel):
    items: list[ApprovalItemResponse]
    stats: ApprovalStatsResponse
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ApproveDocumentRequest(BaseModel):
    note: Optional[str] = None


class RequestEditsRequest(BaseModel):
    note: str    # required — what needs to change


class BulkApproveRequest(BaseModel):
    document_ids: list[uuid.UUID]
    note:         Optional[str] = None