# app/schemas/hr/hr_deadline_schemas.py
#
# Pydantic schemas for HR Deadlines & Extensions endpoints.
# These match the TypeScript types in src/types/hr/hrDeadlines.types.ts

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class DeadlineUrgency(str, Enum):
    urgent   = "urgent"
    warning  = "warning"
    on_track = "on_track"
    overdue  = "overdue"


class DeadlineType(str, Enum):
    lca_response         = "lca_response"
    rfe_response         = "rfe_response"
    document_submission  = "document_submission"
    payment              = "payment"
    form_submission      = "form_submission"
    general              = "general"


class ExtensionStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    denied   = "denied"


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class DeadlineItemResponse(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    case_number:    str
    visa_type:      str
    title:          str
    description:    str
    due_date:       datetime
    days_remaining: int        # negative = overdue
    urgency:        DeadlineUrgency
    deadline_type:  DeadlineType
    employee_name:  str
    employer_name:  str
    attorney_name:  Optional[str]
    assigned_count: int
    status:         str        # application status passthrough

    model_config = ConfigDict(from_attributes=True)


class DeadlineStatsResponse(BaseModel):
    urgent:     int
    warning:    int
    on_track:   int
    extensions: int    # count of pending extension requests


class DeadlineInsightsResponse(BaseModel):
    completion_rate:    float
    completed_on_time:  int
    late_completions:   int
    with_extensions:    int
    avg_response_days:  float
    fastest_hours:      int
    slowest_days:       int
    high_risk:          int
    medium_risk:        int
    low_risk:           int


class DeadlineListResponse(BaseModel):
    items:    list[DeadlineItemResponse]
    stats:    DeadlineStatsResponse
    insights: DeadlineInsightsResponse
    total:    int


class ExtensionRequestResponse(BaseModel):
    id:                  uuid.UUID
    request_number:      str
    application_id:      uuid.UUID
    case_number:         str
    visa_type:           str
    title:               str
    description:         str
    original_deadline:   datetime
    extension_days:      int
    proposed_deadline:   datetime
    status:              ExtensionStatus
    requested_by:        str
    submitted_at:        datetime
    reviewed_by:         Optional[str]
    reviewed_at:         Optional[datetime]
    days_until_original: int

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class RequestExtensionBody(BaseModel):
    extension_days: int
    reason:         str


class ReviewExtensionBody(BaseModel):
    action: str    # "approve" | "deny"
    note:   Optional[str] = None