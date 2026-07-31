"""

Key behaviours:
  1. get_calendar_view()  → merges real calendar_events rows + deadline rows
     into a single unified list sorted by time. Deadlines appear as
     event_type='deadline', is_deadline=True, id=None.

  2. get_agenda()         → same merge logic but for a single day.

  3. get_critical_deadlines() → reads from deadlines table only,
     returns items not yet completed / dismissed, ordered by due_date.

  4. CRUD for calendar_events (create/get/update/cancel).

  5. linked_case_search() → searches applications by number or client name
     for the Screen 18 dropdown.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.employee.services import db_create, db_get_by_id, db_update
from app.models.visamodels import CalendarEvent
from app.models.visamodels import (
    Application,
    Deadline,
    User,
    UserProfile,
    VisaType,
)
from app.schemas.attorney.calendar import (
    AgendaItem,
    AgendaResponse,
    CalendarEventCreate,
    CalendarEventListItem,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarViewResponse,
    CriticalDeadlinesResponse,
    DeadlineSnippet,
    LinkedCaseOption,
    LinkedCaseSearchResponse,
    LinkedCaseSnapshot,
)


# ===========================================================================
# COLOUR / TYPE HELPERS
# ===========================================================================

# Map event_type → UI colour name (for frontend reference, not stored in DB)
EVENT_TYPE_COLOR = {
    "consultation":  "blue",
    "court_hearing": "red",
    "doc_review":    "yellow",
    "internal_sync": "green",
    "deadline":      "pink",
}


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

async def _get_event_or_404(
    db: AsyncSession, event_id: uuid.UUID, attorney_id: uuid.UUID
) -> CalendarEvent:
    event = await db_get_by_id(db, CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Event {event_id} not found.")
    if event.attorney_id != attorney_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not own this event.")
    return event


async def _get_user_name(db: AsyncSession, user_id: uuid.UUID) -> str:
    user = await db_get_by_id(db, User, user_id)
    if not user:
        return "Unknown"
    return f"{user.first_name} {user.last_name}".strip()


async def _build_linked_case_snapshot(
    db: AsyncSession, application_id: uuid.UUID
) -> Optional[LinkedCaseSnapshot]:
    result = await db.execute(
        select(Application, User, VisaType)
        .join(User,     User.id     == Application.user_id)
        .join(VisaType, VisaType.id == Application.visa_type_id)
        .where(Application.id == application_id)
    )
    row = result.first()
    if not row:
        return None
    app, client, vt = row
    return LinkedCaseSnapshot(
        application_id     = app.id,
        application_number = app.application_number,
        client_name        = f"{client.first_name} {client.last_name}".strip(),
        visa_type          = vt.code if vt else None,
    )


def _event_to_list_item(event: CalendarEvent) -> CalendarEventListItem:
    return CalendarEventListItem(
        id          = event.id,
        event_type  = event.event_type,
        title       = event.title,
        event_date  = event.event_date,
        start_time  = event.start_time,
        end_time    = event.end_time,
        is_all_day  = event.is_all_day,
        status      = event.status,
        is_deadline = False,
    )


def _deadline_to_list_item(dl: Deadline) -> CalendarEventListItem:
    """Convert a Deadline row into a virtual CalendarEventListItem."""
    dl_date = dl.due_date.date() if isinstance(dl.due_date, datetime) else dl.due_date
    dl_time = dl.due_date.time() if isinstance(dl.due_date, datetime) else None
    return CalendarEventListItem(
        id               = None,          # virtual — no calendar_events row
        event_type       = "deadline",
        title            = dl.title,
        event_date       = dl_date,
        start_time       = dl_time,
        end_time         = None,
        is_all_day       = False,
        status           = "confirmed",
        is_deadline      = True,
        deadline_urgency = dl.urgency,
    )


def _deadline_to_agenda_item(dl: Deadline) -> AgendaItem:
    dl_time = dl.due_date.time() if isinstance(dl.due_date, datetime) else None
    return AgendaItem(
        id               = None,
        event_type       = "deadline",
        title            = dl.title,
        start_time       = dl_time,
        end_time         = None,
        is_all_day       = False,
        location         = None,
        status           = "confirmed",
        is_deadline      = True,
        is_active        = False,
        deadline_urgency = dl.urgency,
    )


def _sort_key(item: CalendarEventListItem):
    """Sort: all-day first, then by start_time (nulls last)."""
    if item.is_all_day:
        return (0, time.min)
    return (1, item.start_time or time.max)


# ===========================================================================
# CALENDAR VIEW — Month / Week / Day
# GET /calendar/events?start=&end=&view=
# ===========================================================================

async def get_calendar_view(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    start_date: date,
    end_date: date,
    view: str = "month",
) -> CalendarViewResponse:
    """
    Merges real calendar_events + deadline entries for a date range.
    Used by Screens 14 (month), 15 (week), 16 (day) — same endpoint,
    different date range.
    """
    # ── Real events ──────────────────────────────────────────────────────────
    events_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.attorney_id == attorney_id,
            CalendarEvent.event_date  >= start_date,
            CalendarEvent.event_date  <= end_date,
            CalendarEvent.status      != "cancelled",
        ).order_by(CalendarEvent.event_date, CalendarEvent.start_time)
    )
    real_events = events_result.scalars().all()
    items: List[CalendarEventListItem] = [_event_to_list_item(e) for e in real_events]

    # ── Merge deadlines ───────────────────────────────────────────────────────
    deadlines_result = await db.execute(
        select(Deadline).where(
            Deadline.user_id      == attorney_id,
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
            func.date(Deadline.due_date) >= start_date,
            func.date(Deadline.due_date) <= end_date,
        ).order_by(Deadline.due_date)
    )
    deadlines = deadlines_result.scalars().all()
    items += [_deadline_to_list_item(dl) for dl in deadlines]

    # Sort unified list
    items.sort(key=lambda i: (i.event_date, _sort_key(i)))

    return CalendarViewResponse(
        view       = view,
        start_date = start_date,
        end_date   = end_date,
        events     = items,
        total      = len(items),
    )


# ===========================================================================
# TODAY'S AGENDA — right panel (Screens 14, 15)
# GET /calendar/agenda?date=YYYY-MM-DD
# ===========================================================================

async def get_agenda(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    agenda_date: date,
) -> AgendaResponse:
    """
    Fetches all events + deadlines for a single day.
    Marks currently active events (is_active=True).
    """
    now = datetime.now(timezone.utc)

    events_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.attorney_id == attorney_id,
            CalendarEvent.event_date  == agenda_date,
            CalendarEvent.status      != "cancelled",
        ).order_by(CalendarEvent.start_time)
    )
    real_events = events_result.scalars().all()

    agenda_items: List[AgendaItem] = []
    for e in real_events:
        # is_active: today's events where we're currently within the time window
        is_active = False
        if agenda_date == now.date() and e.start_time and e.end_time:
            is_active = e.start_time <= now.time() <= e.end_time

        agenda_items.append(AgendaItem(
            id          = e.id,
            event_type  = e.event_type,
            title       = e.title,
            start_time  = e.start_time,
            end_time    = e.end_time,
            is_all_day  = e.is_all_day,
            location    = e.location,
            status      = e.status,
            is_deadline = False,
            is_active   = is_active,
        ))

    # Merge deadline entries for the day
    dl_result = await db.execute(
        select(Deadline).where(
            Deadline.user_id      == attorney_id,
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
            func.date(Deadline.due_date) == agenda_date,
        ).order_by(Deadline.due_date)
    )
    for dl in dl_result.scalars().all():
        agenda_items.append(_deadline_to_agenda_item(dl))

    # Sort: all-day first, then by start_time
    agenda_items.sort(key=lambda i: (0 if i.is_all_day else 1,
                                     i.start_time or time.max))

    return AgendaResponse(date=agenda_date, items=agenda_items)


# ===========================================================================
# CRITICAL DEADLINES SIDEBAR (Screens 14, 15, 16)
# GET /calendar/deadlines
# ===========================================================================

async def get_critical_deadlines(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    limit: int = 5,
) -> CriticalDeadlinesResponse:
    """
    Returns upcoming non-completed deadlines for the Critical Deadlines
    sidebar panel. Ordered by urgency then due_date.
    """
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    today = datetime.now(timezone.utc)

    result = await db.execute(
        select(Deadline, Application)
        .outerjoin(Application, Application.id == Deadline.application_id)
        .where(
            Deadline.user_id      == attorney_id,
            Deadline.is_completed == False,
            Deadline.is_dismissed == False,
            Deadline.due_date     >= today,
        )
        .order_by(Deadline.due_date)
        .limit(limit * 3)   # over-fetch to allow urgency re-sort in Python
    )
    rows = result.all()

    snippets: List[DeadlineSnippet] = []
    for dl, app in rows:
        delta = (dl.due_date.date() - today.date()).days
        snippets.append(DeadlineSnippet(
            deadline_id    = dl.id,
            title          = dl.title,
            due_date       = dl.due_date,
            days_remaining = max(delta, 0),
            urgency        = dl.urgency,
            case_number    = app.application_number if app else None,
        ))

    # Re-sort by urgency first, then due_date
    snippets.sort(key=lambda s: (urgency_order.get(s.urgency, 9), s.due_date))

    return CriticalDeadlinesResponse(items=snippets[:limit])


# ===========================================================================
# LINKED CASE SEARCH — Screen 18 dropdown
# GET /calendar/cases/search?q=
# ===========================================================================

async def search_linked_cases(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    q: str,
    limit: int = 10,
) -> LinkedCaseSearchResponse:
    """
    Searches applications assigned to this attorney by case number or client name.
    Used by the "Search client name or case ID" dropdown in Screen 18.
    """
    if not q or len(q.strip()) < 2:
        return LinkedCaseSearchResponse(items=[])

    pattern = f"%{q.strip()}%"

    result = await db.execute(
        select(Application, User, VisaType)
        .join(User,     User.id     == Application.user_id)
        .join(VisaType, VisaType.id == Application.visa_type_id)
        .where(
            Application.assigned_attorney_id == attorney_id,
            or_(
                Application.application_number.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                func.concat(User.first_name, " ", User.last_name).ilike(pattern),
            ),
        )
        .limit(limit)
    )
    rows = result.all()

    items = [
        LinkedCaseOption(
            application_id     = app.id,
            application_number = app.application_number,
            client_name        = f"{client.first_name} {client.last_name}".strip(),
            visa_type          = vt.code if vt else None,
        )
        for app, client, vt in rows
    ]
    return LinkedCaseSearchResponse(items=items)


# ===========================================================================
# GET SINGLE EVENT — Screen 17 Event Details Drawer
# ===========================================================================

async def get_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    attorney_id: uuid.UUID,
) -> CalendarEventResponse:
    event         = await _get_event_or_404(db, event_id, attorney_id)
    attorney_name = await _get_user_name(db, event.attorney_id)
    linked_case   = None
    if event.application_id:
        linked_case = await _build_linked_case_snapshot(db, event.application_id)

    return CalendarEventResponse(
        id               = event.id,
        event_type       = event.event_type,
        title            = event.title,
        event_date       = event.event_date,
        start_time       = event.start_time,
        end_time         = event.end_time,
        is_all_day       = event.is_all_day,
        location         = event.location,
        notes            = event.notes,
        status           = event.status,
        reminder_enabled = event.reminder_enabled,
        reminder_minutes = event.reminder_minutes,
        attorney_id      = event.attorney_id,
        attorney_name    = attorney_name,
        linked_case      = linked_case,
        is_deadline      = False,
        created_at       = event.created_at,
        updated_at       = event.updated_at,
    )


# ===========================================================================
# CREATE EVENT — Screen 18 Save Event button
# ===========================================================================

async def create_event(
    db: AsyncSession,
    payload: CalendarEventCreate,
    attorney_id: uuid.UUID,
) -> CalendarEventResponse:
    # 'deadline' type cannot be created directly — it's virtual/read-only
    if payload.event_type == "deadline":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'deadline' events are read-only. Create a deadline via the deadlines API.",
        )

    # Validate time logic
    if payload.start_time and payload.end_time:
        if payload.end_time <= payload.start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_time must be after start_time.",
            )

    new_event = CalendarEvent(
        attorney_id      = attorney_id,
        application_id   = payload.application_id,
        event_type       = payload.event_type,
        title            = payload.title,
        event_date       = payload.event_date,
        start_time       = payload.start_time,
        end_time         = payload.end_time,
        is_all_day       = payload.is_all_day,
        location         = payload.location,
        notes            = payload.notes,
        status           = payload.status,
        reminder_enabled = payload.reminder_enabled,
        reminder_minutes = payload.reminder_minutes,
        created_by       = attorney_id,
    )
    new_event = await db_create(db, new_event)
    return await get_event(db, new_event.id, attorney_id)


# ===========================================================================
# UPDATE EVENT — Screen 17 Edit Details button
# ===========================================================================

async def update_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    payload: CalendarEventUpdate,
    attorney_id: uuid.UUID,
) -> CalendarEventResponse:
    await _get_event_or_404(db, event_id, attorney_id)

    data = payload.model_dump(exclude_unset=True)

    # Guard: can't change type to 'deadline'
    if data.get("event_type") == "deadline":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot set event_type to 'deadline'.",
        )

    # Validate time logic if both provided
    start = data.get("start_time")
    end   = data.get("end_time")
    if start and end and end <= start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be after start_time.",
        )

    data["modified_by"] = attorney_id
    await db_update(db, CalendarEvent, event_id, data)
    return await get_event(db, event_id, attorney_id)


# ===========================================================================
# CANCEL EVENT — Screen 17 Cancel Event button
# ===========================================================================

async def cancel_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    attorney_id: uuid.UUID,
) -> dict:
    event = await _get_event_or_404(db, event_id, attorney_id)

    if event.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event is already cancelled.",
        )

    await db_update(db, CalendarEvent, event_id, {
        "status":      "cancelled",
        "modified_by": attorney_id,
    })
    return {"detail": "Event cancelled successfully."}
