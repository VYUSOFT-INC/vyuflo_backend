
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# ENUMS (as string literals — OpenAPI renders them as dropdowns)
# ===========================================================================

EventType   = Literal["consultation", "court_hearing", "doc_review",
                       "internal_sync", "deadline"]
EventStatus = Literal["confirmed", "cancelled", "tentative"]


# ===========================================================================
# LINKED CASE SEARCH — Screen 18 "Search client name or case ID" dropdown
# ===========================================================================

class LinkedCaseOption(BaseModel):
    application_id:     uuid.UUID
    application_number: str
    client_name:        str
    visa_type:          Optional[str] = None


class LinkedCaseSearchResponse(BaseModel):
    items: List[LinkedCaseOption]


# ===========================================================================
# CREATE — Screen 18 Save Event button
# ===========================================================================

class CalendarEventCreate(BaseModel):
    event_type:       EventType
    title:            str              = Field(..., min_length=1, max_length=300)
    event_date:       date
    start_time:       Optional[time]   = None
    end_time:         Optional[time]   = None
    is_all_day:       bool             = False
    location:         Optional[str]    = Field(None, max_length=300)
    notes:            Optional[str]    = None
    application_id:   Optional[uuid.UUID] = None   # Linked Case (Optional)
    status:           EventStatus      = "confirmed"
    reminder_enabled: bool             = True
    reminder_minutes: int              = Field(default=1440, ge=0)
    # 1440 = "1 day before" shown in Screen 18


# ===========================================================================
# UPDATE — Screen 17 Edit Details button (all fields optional)
# ===========================================================================

class CalendarEventUpdate(BaseModel):
    event_type:       Optional[EventType]      = None
    title:            Optional[str]            = Field(None, min_length=1, max_length=300)
    event_date:       Optional[date]           = None
    start_time:       Optional[time]           = None
    end_time:         Optional[time]           = None
    is_all_day:       Optional[bool]           = None
    location:         Optional[str]            = Field(None, max_length=300)
    notes:            Optional[str]            = None
    application_id:   Optional[uuid.UUID]      = None
    status:           Optional[EventStatus]    = None
    reminder_enabled: Optional[bool]           = None
    reminder_minutes: Optional[int]            = Field(None, ge=0)


# ===========================================================================
# LINKED CASE SNAPSHOT — embedded in event detail response
# ===========================================================================

class LinkedCaseSnapshot(BaseModel):
    application_id:     uuid.UUID
    application_number: str
    client_name:        str
    visa_type:          Optional[str] = None


# ===========================================================================
# FULL EVENT RESPONSE — Screen 17 Event Details Drawer
# ===========================================================================

class CalendarEventResponse(BaseModel):
    """Full event detail — used by Screen 17 drawer and GET /events/{id}."""
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    event_type:       str
    title:            str
    event_date:       date
    start_time:       Optional[time]
    end_time:         Optional[time]
    is_all_day:       bool
    location:         Optional[str]
    notes:            Optional[str]
    status:           str
    reminder_enabled: bool
    reminder_minutes: int

    # Organizer (attorney)
    attorney_id:      uuid.UUID
    attorney_name:    str          # computed by service: first_name + last_name

    # Linked case — null if no case linked
    linked_case:      Optional[LinkedCaseSnapshot] = None

    # Source flag — True = came from deadlines table (read-only virtual entry)
    is_deadline:      bool = False

    created_at:       datetime
    updated_at:       datetime


# ===========================================================================
# LIST ITEM — compact form rendered inside calendar grid cells
# Screens 14 (month cells), 15 (week columns), 16 (day timeline slots)
# ===========================================================================

class CalendarEventListItem(BaseModel):
    """
    Minimal shape for grid rendering.
    The UI shows: time + title + color dot.
    Deadline entries merged here have is_deadline=True and no event_id.
    """
    # None for virtual deadline entries (they don't have a calendar_events row)
    id:           Optional[uuid.UUID] = None
    event_type:   str
    title:        str
    event_date:   date
    start_time:   Optional[time]
    end_time:     Optional[time]
    is_all_day:   bool
    status:       str
    is_deadline:  bool = False

    # deadline-only fields
    deadline_urgency: Optional[str] = None   # "critical", "high", "medium", "low"


# ===========================================================================
# CALENDAR VIEW RESPONSE — Month / Week / Day
# GET /calendar/events?start=&end=&view=month|week|day
# ===========================================================================

class CalendarViewResponse(BaseModel):
    """
    Returned for all 3 view modes (Month/Week/Day).
    Events list includes both real calendar_events rows AND
    merged deadline entries (is_deadline=True items).
    """
    view:       str             # "month" | "week" | "day"
    start_date: date
    end_date:   date
    events:     List[CalendarEventListItem]
    total:      int


# ===========================================================================
# AGENDA ITEM — right panel "Today's Agenda" (Screens 14, 15)
# Richer than list item: includes location, status badge, organizer
# ===========================================================================

class AgendaItem(BaseModel):
    id:           Optional[uuid.UUID] = None
    event_type:   str
    title:        str
    start_time:   Optional[time]
    end_time:     Optional[time]
    is_all_day:   bool
    location:     Optional[str]
    status:       str
    is_deadline:  bool  = False
    is_active:    bool  = False   # True when event is currently happening
    deadline_urgency: Optional[str] = None


class AgendaResponse(BaseModel):
    """GET /calendar/agenda?date=YYYY-MM-DD — Today's Agenda panel."""
    date:  date
    items: List[AgendaItem]


# ===========================================================================
# DEADLINE SNIPPET — "Critical Deadlines" sidebar (Screens 14, 15, 16)
# Sourced from deadlines table, not calendar_events
# ===========================================================================

class DeadlineSnippet(BaseModel):
    deadline_id:    uuid.UUID
    title:          str
    due_date:       datetime
    days_remaining: int       # computed: (due_date.date() - today).days
    urgency:        str       # "critical" | "high" | "medium" | "low"
    case_number:    Optional[str] = None   # application_number if linked


class CriticalDeadlinesResponse(BaseModel):
    """GET /calendar/deadlines — Critical Deadlines sidebar panel."""
    items: List[DeadlineSnippet]
