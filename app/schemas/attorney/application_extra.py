# =============================================================================
# app/schemas/application_extra.py
#
# NEW schemas only — Comments + Deadlines (Screens 9, 10, 11)
# Your existing app/schemas/application.py is NOT touched.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared enums
# ─────────────────────────────────────────────────────────────────────────────

CommentVisibility = Literal[
    "all_staff",
    "attorney_only",
    "hr_only",
    "admin_only",
]

DeadlineUrgency = Literal["critical", "high", "medium", "low"]

DeadlineType = Literal[
    "document_submission",
    "government_filing",
    "attorney_review",
    "hr_approval",
    "interview",
    "other",
]


# =============================================================================
# COMMENT SCHEMAS
# =============================================================================

class CommentCreate(BaseModel):
    """POST /applications/{id}/comments"""
    body:       str                          = Field(..., min_length=1, max_length=5000)
    visible_to: CommentVisibility            = "all_staff"

    model_config = ConfigDict(from_attributes=True)


class CommentUpdate(BaseModel):
    """PATCH /applications/{id}/comments/{comment_id}"""
    body: str = Field(..., min_length=1, max_length=5000)

    model_config = ConfigDict(from_attributes=True)


class CommentAuthor(BaseModel):
    """Nested author info — avoids extra round trips from frontend."""
    id:         uuid.UUID
    first_name: str
    last_name:  str
    email:      str

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    author_id:      uuid.UUID
    author:         Optional[CommentAuthor] = None   # nested — populated by service
    body:           str
    visible_to:     CommentVisibility
    is_pinned:      bool
    pinned_by:      Optional[uuid.UUID]
    pinned_at:      Optional[datetime]
    is_edited:      bool
    edited_at:      Optional[datetime]
    is_deleted:     bool
    created_at:     datetime
    updated_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int


# =============================================================================
# DEADLINE SCHEMAS
# =============================================================================

class DeadlineCreate(BaseModel):
    """POST /applications/{id}/deadlines"""
    title:         str           = Field(..., min_length=1, max_length=300)
    description:   Optional[str] = Field(None, max_length=2000)
    due_date:      datetime
    urgency:       DeadlineUrgency = "medium"
    deadline_type: DeadlineType    = "other"

    model_config = ConfigDict(from_attributes=True)


class DeadlineUpdate(BaseModel):
    """PATCH /applications/{id}/deadlines/{deadline_id}"""
    title:         Optional[str]           = Field(None, min_length=1, max_length=300)
    description:   Optional[str]           = Field(None, max_length=2000)
    due_date:      Optional[datetime]      = None
    urgency:       Optional[DeadlineUrgency] = None
    deadline_type: Optional[DeadlineType]  = None

    model_config = ConfigDict(from_attributes=True)


class DeadlineResponse(BaseModel):
    id:             uuid.UUID
    application_id: Optional[uuid.UUID]
    user_id:        uuid.UUID
    title:          str
    description:    Optional[str]
    due_date:       datetime
    urgency:        DeadlineUrgency
    deadline_type:  DeadlineType
    is_completed:   bool
    completed_at:   Optional[datetime]
    completed_by:   Optional[uuid.UUID]
    is_dismissed:   bool
    dismissed_at:   Optional[datetime]
    created_at:     datetime
    updated_at:     datetime

    model_config = ConfigDict(from_attributes=True)


class DeadlineListResponse(BaseModel):
    items: List[DeadlineResponse]
    total: int
