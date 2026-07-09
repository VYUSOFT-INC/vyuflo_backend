"""

Route map (9 endpoints):

  GET  /calendar/events              → Screens 14/15/16 — calendar grid data
  GET  /calendar/agenda              → Screens 14/15    — Today's Agenda panel
  GET  /calendar/deadlines           → Screens 14/15/16 — Critical Deadlines sidebar
  GET  /calendar/cases/search        → Screen 18        — Linked Case dropdown search

  POST   /calendar/events            → Screen 18        — Save Event button
  GET    /calendar/events/{id}       → Screen 17        — Event Details Drawer load
  PATCH  /calendar/events/{id}       → Screen 17        — Edit Details button
  DELETE /calendar/events/{id}       → Screen 17        — Cancel Event button

"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_permissions import get_current_user, get_db
from app.models.visamodels import User
from app.services.attorney import calendar_service
from app.schemas.attorney.calendar import (
    AgendaResponse,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarViewResponse,
    CriticalDeadlinesResponse,
    LinkedCaseSearchResponse,
)

calendar_router = APIRouter(tags=["Calendar"])


# ===========================================================================
# CALENDAR GRID — Month / Week / Day views (Screens 14, 15, 16)
# ===========================================================================

@calendar_router.get(
    "/calendar/events",
    response_model=CalendarViewResponse,
    summary="Get calendar events for a date range (Month / Week / Day view)",
)
async def get_calendar_events(
    view: str = Query(
        default="month",
        regex="^(month|week|day)$",
        description="month | week | day",
    ),
    start: date = Query(..., description="Range start date YYYY-MM-DD"),
    end:   date = Query(..., description="Range end date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screens 14 / 15 / 16 — called on load and on prev/next navigation.

    Frontend sends:
      Screen 14 (Month):  start=2026-08-01  end=2026-08-31  view=month
      Screen 15 (Week):   start=2026-08-09  end=2026-08-15  view=week
      Screen 16 (Day):    start=2026-08-10  end=2026-08-10  view=day

    Returns real calendar_events rows MERGED with deadline entries.
    Deadlines appear with is_deadline=True and id=None.
    """
    if start > end:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="start must be before end.")

    return await calendar_service.get_calendar_view(
        db, current_user.user_id, start, end, view
    )


# ===========================================================================
# TODAY'S AGENDA — right panel (Screens 14, 15)
# ===========================================================================

@calendar_router.get(
    "/calendar/agenda",
    response_model=AgendaResponse,
    summary="Today's Agenda panel — right sidebar on Month and Week views",
)
async def get_agenda(
    agenda_date: date = Query(
        default=None,
        description="Date to fetch agenda for. Defaults to today.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screens 14 & 15 — populates the right-side 'Today's Agenda' panel.
    Returns events with is_active=True for currently running appointments.
    Also merges deadline entries for the day.
    """
    target = agenda_date or datetime.now(timezone.utc).date()
    return await calendar_service.get_agenda(db, current_user.user_id, target)


# ===========================================================================
# CRITICAL DEADLINES SIDEBAR (Screens 14, 15, 16)
# ===========================================================================

@calendar_router.get(
    "/calendar/deadlines",
    response_model=CriticalDeadlinesResponse,
    summary="Critical Deadlines sidebar — upcoming deadlines ordered by urgency",
)
async def get_critical_deadlines(
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screens 14 / 15 / 16 — populates the Critical Deadlines sidebar.
    Sourced from the deadlines table (not calendar_events).
    Ordered: critical → high → medium → low, then by due_date.
    """
    return await calendar_service.get_critical_deadlines(
        db, current_user.user_id, limit
    )


# ===========================================================================
# LINKED CASE SEARCH — Screen 18 dropdown
# ===========================================================================

@calendar_router.get(
    "/calendar/cases/search",
    response_model=LinkedCaseSearchResponse,
    summary="Search linked cases for Add Event modal (Screen 18)",
)
async def search_linked_cases(
    q: str = Query(..., min_length=2, description="Client name or case ID"),
    limit: int = Query(default=10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 18 — 'Search client name or case ID' dropdown.
    Returns matching applications assigned to the current attorney.
    """
    return await calendar_service.search_linked_cases(
        db, current_user.user_id, q, limit
    )


# ===========================================================================
# CREATE EVENT — Screen 18 Save Event button
# ===========================================================================

@calendar_router.post(
    "/calendar/events",
    response_model=CalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new calendar event (Screen 18 — Save Event)",
)
async def create_event(
    payload: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 18 — 'Save Event' button in the Add New Event modal.

    Event types: consultation | court_hearing | doc_review | internal_sync
    ('deadline' type is read-only — cannot be created here.)

    Validation:
      • end_time must be after start_time
      • event_type cannot be 'deadline'
    """
    return await calendar_service.create_event(
        db, payload, current_user.user_id
    )


# ===========================================================================
# GET SINGLE EVENT — Screen 17 Event Details Drawer
# ===========================================================================

@calendar_router.get(
    "/calendar/events/{event_id}",
    response_model=CalendarEventResponse,
    summary="Get event details — Screen 17 Event Details Drawer",
)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 17 — triggered when user clicks an event on the calendar grid.
    Returns full event details including linked case snapshot.
    """
    return await calendar_service.get_event(
        db, event_id, current_user.user_id
    )


# ===========================================================================
# UPDATE EVENT — Screen 17 Edit Details button
# ===========================================================================

@calendar_router.patch(
    "/calendar/events/{event_id}",
    response_model=CalendarEventResponse,
    summary="Edit event details — Screen 17 Edit Details button",
)
async def update_event(
    event_id: uuid.UUID,
    payload: CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 17 — 'Edit Details' button opens the edit form.
    Only send the fields that changed (PATCH semantics).
    """
    return await calendar_service.update_event(
        db, event_id, payload, current_user.user_id
    )


# ===========================================================================
# CANCEL EVENT — Screen 17 Cancel Event button
# ===========================================================================

@calendar_router.delete(
    "/calendar/events/{event_id}",
    summary="Cancel (soft-delete) an event — Screen 17 Cancel Event button",
)
async def cancel_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Screen 17 — red 'Cancel Event' button.
    Sets status='cancelled' (soft delete — event stays in DB for audit).
    Returns 409 if already cancelled.
    """
    return await calendar_service.cancel_event(
        db, event_id, current_user.user_id
    )
