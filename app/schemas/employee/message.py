# src/schemas/employee/message.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict


# ── Enums ─────────────────────────────────────────────────────────────────────
ThreadType      = Literal["direct", "group"]
MessageType     = Literal["text", "file_attachment", "call_event", "system_notification"]
ParticipantRole = Literal["employee", "attorney", "hr", "support", "admin"]
CallStatus      = Literal["incoming", "outgoing", "missed", "declined"]


# =============================================================================
# PARTICIPANT
# =============================================================================

class ParticipantResponse(BaseModel):
    id:               uuid.UUID
    user_id:          uuid.UUID
    participant_name: str
    participant_role: ParticipantRole
    avatar_url:       Optional[str]
    is_online:        bool
    unread_count:     int
    is_muted:         bool
    is_archived:      bool
    joined_at:        datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# THREAD  (= Conversation in frontend)
# =============================================================================

class ThreadResponse(BaseModel):
    id:               uuid.UUID
    thread_type:      ThreadType
    title:            Optional[str]         = None
    application_id:   Optional[uuid.UUID]   = None
    is_archived:      bool

    # The other participant (direct) or group info
    participant_id:    Optional[uuid.UUID]  = None
    participant_name:  str
    participant_role:  Optional[str]        = None
    avatar_url:        Optional[str]        = None
    participant_count: Optional[int]        = None  # ← group: total member count

    # Online status
    is_online:     bool
    last_seen_at:  Optional[datetime]       = None

    # Left-panel preview
    last_message:    Optional[str]          = None
    last_message_at: Optional[datetime]     = None
    unread_count:    int

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadCreate(BaseModel):
    thread_type:     ThreadType              = "direct"
    participant_ids: List[uuid.UUID]
    title:           Optional[str]           = None
    application_id:  Optional[uuid.UUID]     = None
    initial_message: Optional[str]           = None

    model_config = ConfigDict(from_attributes=True)


class ThreadListResponse(BaseModel):
    items: List[ThreadResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MESSAGE
# =============================================================================

class MessageResponse(BaseModel):
    id:           uuid.UUID
    thread_id:    uuid.UUID
    sender_id:    uuid.UUID
    sender_name:   Optional[str]        = None   # ← full name from User relation
    sender_avatar: Optional[str]        = None   # ← profile picture URL

    content:      Optional[str]         = None
    message_type: MessageType

    # Attachment fields
    attachment_name: Optional[str]      = None
    attachment_url:  Optional[str]      = None
    attachment_size: Optional[str]      = None
    document_id:     Optional[uuid.UUID] = None
    attachment_type: Optional[str]      = None
    is_image:        bool               = False

    # Call fields
    call_duration_seconds: Optional[int]      = None
    call_status:           Optional[CallStatus] = None

    is_read:    bool
    is_edited:  bool
    is_deleted: bool

    created_at:  datetime
    updated_at:  Optional[datetime]     = None

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MARK READ
# =============================================================================

class MarkReadResponse(BaseModel):
    thread_id:    uuid.UUID
    unread_count: int

    model_config = ConfigDict(from_attributes=True)