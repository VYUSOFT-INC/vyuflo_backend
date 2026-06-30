# src/schemas/message.py
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
    participant_name: str             # from User.first_name + last_name
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
    """
    Shape returned to frontend as a 'Conversation' row in the left panel.
    Maps MessageThread + the OTHER participant's info (for direct threads).
    """
    id:               uuid.UUID

    # Thread meta
    thread_type:      ThreadType
    title:            Optional[str]        # group name; null for direct
    application_id:   Optional[uuid.UUID]
    is_archived:      bool

    # Derived from the OTHER participant (direct) or group title
    participant_id:   Optional[uuid.UUID]  # other user's id (direct only)
    participant_name: str                  # other user's name OR group title
    participant_role: Optional[str]        # "Immigration Specialist" etc.
    avatar_url:       Optional[str]

    # Online status of the OTHER participant (direct only)
    is_online:        bool
    last_seen_at:     Optional[datetime] = None

    # Last message preview — powers left-panel snippet
    last_message:     Optional[str]        # = last_message_preview
    last_message_at:  Optional[datetime]

    # Current user's unread count for this thread
    unread_count:     int

    created_at:       datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadCreate(BaseModel):
    """POST /messages/conversations — start a new thread"""
    thread_type:    ThreadType         = "direct"
    participant_ids: List[uuid.UUID]   # 1 for direct, multiple for group
    title:          Optional[str]      = None   # required for group
    application_id: Optional[uuid.UUID] = None
    initial_message: Optional[str]    = None    # optional first message

    model_config = ConfigDict(from_attributes=True)


class ThreadListResponse(BaseModel):
    items: List[ThreadResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MESSAGE
# =============================================================================

class MessageResponse(BaseModel):
    id:            uuid.UUID
    thread_id:     uuid.UUID           # = conversation_id for frontend
    sender_id:     uuid.UUID
    content:       Optional[str]       # = body
    message_type:  MessageType

    # Attachment fields — populated when message_type = file_attachment
    attachment_name: Optional[str]     # Document.file_name
    attachment_url:  Optional[str]     # served via /documents/:id/view
    attachment_size: Optional[str]     # "1.2 MB"
    document_id:     Optional[uuid.UUID]

    # Call fields — populated when message_type = call_event
    call_duration_seconds: Optional[int]
    call_status:           Optional[CallStatus]
    attachment_type: Optional[str] = None
    is_image: bool = False
    # State
    is_read:    bool
    is_edited:  bool
    is_deleted: bool

    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """POST /messages/conversations/:id/messages — text only"""
    content: Optional[str] = None
    # File attachments are sent as multipart — handled separately in router

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# MARK READ
# =============================================================================

class MarkReadResponse(BaseModel):
    thread_id:    uuid.UUID
    unread_count: int   # should be 0 after marking read

    model_config = ConfigDict(from_attributes=True)