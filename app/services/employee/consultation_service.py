# =============================================================================
# app/services/consultation_service.py
# All business logic for consultations.
# Routes stay thin — call these functions directly.
# =============================================================================

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, time, datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    User,
    UserProfile,
    Application,
    AttorneyProfile,
    AppointmentType,
    AttorneyAvailability,
    ConsultationSlot,
    ConsultationBooking,
)
from app.schemas.employee.consultation_schemas import (
    CreateConsultationBookingRequest,
    AttorneyAvailabilityCreateRequest,
    SaveAvailabilityRequest,
    AppointmentTypeCreateRequest,
    SlotGenerateRequest,
    BookConsultationPageData,
    AttorneyProfileOut,
    AppointmentTypeOut,
    ConsultationSlotOut,
)
from app.services.employee.services import db_create, db_get_by_id, db_update
from app.core.email import send_email
from app.models.visamodels import Notification


def _now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Attorney helpers
# =============================================================================

async def list_attorneys(
    db: AsyncSession,
    accepting_only: bool = True,
) -> Sequence[AttorneyProfile]:
    """Return all active attorneys, optionally filtered to accepting-cases only."""
    stmt = (
        select(AttorneyProfile)
        .options(selectinload(AttorneyProfile.user))
        .where(AttorneyProfile.is_active == True)
    )
    if accepting_only:
        stmt = stmt.where(AttorneyProfile.is_accepting_cases == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_attorney_by_id(
    db: AsyncSession,
    attorney_id: uuid.UUID,
) -> Optional[AttorneyProfile]:
    result = await db.execute(
        select(AttorneyProfile)
        .options(selectinload(AttorneyProfile.user))
        .where(
            and_(
                AttorneyProfile.id == attorney_id,
                AttorneyProfile.is_active == True,
            )
        )
    )
    return result.scalar_one_or_none()


# =============================================================================
# AppointmentType
# =============================================================================

async def list_appointment_types(
    db: AsyncSession,
) -> Sequence[AppointmentType]:
    result = await db.execute(
        select(AppointmentType)
        .where(AppointmentType.is_active == True)
        .order_by(AppointmentType.sort_order, AppointmentType.duration_minutes)
    )
    return result.scalars().all()


async def create_appointment_type(
    db: AsyncSession,
    data: AppointmentTypeCreateRequest,
    created_by: uuid.UUID,
) -> AppointmentType:
    obj = AppointmentType(
        id=uuid.uuid4(),
        title=data.title,
        description=data.description,
        duration_minutes=data.duration_minutes,
        price_usd=data.price_usd,
        sort_order=data.sort_order,
        created_by=created_by,
    )
    return await db_create(db, obj)


# =============================================================================
# Attorney Availability
# =============================================================================

async def list_attorney_availability(
    db: AsyncSession,
    attorney_id: uuid.UUID,
) -> Sequence[AttorneyAvailability]:
    result = await db.execute(
        select(AttorneyAvailability)
        .where(
            and_(
                AttorneyAvailability.attorney_id == attorney_id,
                AttorneyAvailability.is_active == True,
            )
        )
        .order_by(AttorneyAvailability.day_of_week, AttorneyAvailability.start_time)
    )
    return result.scalars().all()


async def set_attorney_availability(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    data: AttorneyAvailabilityCreateRequest,
) -> AttorneyAvailability:
    obj = AttorneyAvailability(
        id=uuid.uuid4(),
        attorney_id=attorney_id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        slot_duration_minutes=data.slot_duration_minutes,
        timezone=data.timezone,
    )
    return await db_create(db, obj)


async def get_user_timezone(
    db: AsyncSession,
    user_id: uuid.UUID,
    fallback: str,
) -> str:
    """
    Looks up a user's own personal timezone from their profile (set on
    the settings page). Falls back to `fallback` (usually the attorney's
    slot timezone) if the user never filled that field in.
    """
    result = await db.execute(
        select(UserProfile.timezone).where(UserProfile.user_id == user_id)
    )
    tz = result.scalar_one_or_none()
    return tz or fallback


async def _get_attorney_profile_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[AttorneyProfile]:
    """Resolves the logged-in user's own AttorneyProfile.id — used by the
    /attorneys/me/* endpoints so the frontend never has to know the UUID."""
    result = await db.execute(
        select(AttorneyProfile).where(AttorneyProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _verify_no_overlap_within_day(rows) -> None:
    """
    Belt-and-suspenders check: frontend already prevents overlapping
    windows on the same day, but a malformed API call could still send
    e.g. Mon 9-12 AND Mon 11-13 (overlapping by an hour). Catch that here
    before it ever reaches the database.
    """
    rows_by_day: dict[int, list] = defaultdict(list)
    for r in rows:
        rows_by_day[r.day_of_week].append(r)

    for day, day_rows in rows_by_day.items():
        sorted_rows = sorted(day_rows, key=lambda r: r.start_time)
        for i, r in enumerate(sorted_rows):
            if i > 0 and r.start_time < sorted_rows[i - 1].end_time:
                raise ValueError(
                    f"day_of_week={day}: overlapping windows "
                    f"{sorted_rows[i-1].start_time}-{sorted_rows[i-1].end_time} "
                    f"and {r.start_time}-{r.end_time}"
                )


async def bulk_replace_availability(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    data: SaveAvailabilityRequest,
) -> Sequence[AttorneyAvailability]:
    """
    Replaces the attorney's ENTIRE weekly availability in one call.
    Any day not included in `data.rows` is treated as "turned off".
    A day can have MULTIPLE windows (e.g. 9-12 AND 14-17) — every row
    in `data.rows` gets inserted, no deduping by day_of_week.

    Safety rule: turning a day off (or narrowing its hours) must NEVER
    cancel a consultation that was already booked. So this function only
    wipes UNBOOKED future ConsultationSlot rows — booked slots (and the
    real bookings tied to them) are always left completely alone.

    We wipe ALL unbooked future slots on every save, not just the ones
    for days that got turned off — an earlier version only cleaned up
    removed days, which missed a real case: a day that stays ACTIVE but
    has its time window narrowed (e.g. 9-5 -> 10-4) still left the old
    9-10 and 4-5 slots bookable forever. Wiping everything and letting
    generate_slots rebuild from scratch is simpler and can't miss a case.
    """
    _verify_no_overlap_within_day(data.rows)   # raises ValueError on overlap

    # ── Bulk replace the availability rules ───────────────────────────────
    await db.execute(
        delete(AttorneyAvailability).where(AttorneyAvailability.attorney_id == attorney_id)
    )
    for row in data.rows:
        db.add(AttorneyAvailability(
            id=uuid.uuid4(),
            attorney_id=attorney_id,
            day_of_week=row.day_of_week,
            start_time=row.start_time,
            end_time=row.end_time,
            slot_duration_minutes=row.slot_duration_minutes,
            timezone=row.timezone,
            is_active=True,
        ))

    # ── Wipe every UNBOOKED future slot — generate_slots (called by the
    #    frontend right after this) rebuilds a clean, correct set from the
    #    rules just saved above. Booked slots are never touched.
    await db.execute(
        delete(ConsultationSlot).where(
            and_(
                ConsultationSlot.attorney_id == attorney_id,
                ConsultationSlot.is_booked == False,
                ConsultationSlot.slot_date >= date.today(),
            )
        )
    )

    await db.commit()
    return await list_attorney_availability(db, attorney_id)


# =============================================================================
# Slot generation — called by attorney or cron job
# Generates ConsultationSlot rows from AttorneyAvailability for a date range
# =============================================================================

async def generate_slots(
    db: AsyncSession,
    data: SlotGenerateRequest,
) -> List[ConsultationSlot]:
    """
    Walk every day in [from_date, to_date] using the ATTORNEY'S OWN local
    calendar (their weekly rule is still expressed in their own timezone —
    see AttorneyAvailability, which is intentionally NOT converted to UTC).

    A day can have MULTIPLE windows (e.g. 9-12 AND 14-17) — avail_by_day
    groups by day_of_week into a LIST of rules, not a single rule. A plain
    dict would silently keep only the LAST window inserted for that day
    and drop the rest.

    Every generated slot is converted to its true UTC instant BEFORE being
    stored — ConsultationSlot rows are always UTC from here on, regardless
    of which timezone the attorney's rule uses.

    A slot near midnight can convert into the UTC day BEFORE or AFTER the
    local day being walked (e.g. 11:30 PM in Los Angeles becomes the next
    day in UTC) — so the "does this slot already exist" check is done
    against a UTC-based lookup table, not the local day being walked.
    """
    from app.core.timeutils import to_utc

    availability_rows = await list_attorney_availability(db, data.attorney_id)
    if not availability_rows:
        return []

    # Group by day_of_week — a day can have MULTIPLE windows.
    avail_by_day: dict[int, list[AttorneyAvailability]] = defaultdict(list)
    for row in availability_rows:
        avail_by_day[row.day_of_week].append(row)

    # Pad the existing-slot lookup by 1 day on each side — a local slot
    # near midnight can land on the UTC day just before/after the range.
    existing_result = await db.execute(
        select(ConsultationSlot.slot_date, ConsultationSlot.slot_time).where(
            and_(
                ConsultationSlot.attorney_id == data.attorney_id,
                ConsultationSlot.slot_date >= data.from_date - timedelta(days=1),
                ConsultationSlot.slot_date <= data.to_date + timedelta(days=1),
            )
        )
    )
    existing_utc_pairs = {(r.slot_date, r.slot_time) for r in existing_result.all()}

    created: List[ConsultationSlot] = []
    current = data.from_date

    while current <= data.to_date:
        dow = current.weekday()  # 0=Monday … 6=Sunday, attorney's LOCAL day
        if dow in avail_by_day:
            for rule in avail_by_day[dow]:   # walk EACH window on this day

                # Walk start→end in the attorney's own local time
                slot_dt = datetime.combine(current, rule.start_time)
                end_dt  = datetime.combine(current, rule.end_time)

                while slot_dt < end_dt:
                    local_time = slot_dt.time()
                    utc_instant = to_utc(current, local_time, rule.timezone)
                    utc_date = utc_instant.date()
                    utc_time = utc_instant.time()

                    pair = (utc_date, utc_time)
                    if pair not in existing_utc_pairs:
                        slot = ConsultationSlot(
                            id=uuid.uuid4(),
                            attorney_id=data.attorney_id,
                            slot_date=utc_date,
                            slot_time=utc_time,
                            timezone="UTC",
                        )
                        db.add(slot)
                        created.append(slot)
                        existing_utc_pairs.add(pair)   # avoid dupes within this same run
                    slot_dt += timedelta(minutes=rule.slot_duration_minutes)

        current += timedelta(days=1)

    await db.flush()
    for s in created:
        await db.refresh(s)
    return created


# =============================================================================
# Slot queries
# =============================================================================

async def list_slots_for_attorney(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    include_booked: bool = False,
) -> List[ConsultationSlot]:
    """
    Return available (not booked, not blocked) slots for an attorney.
    Defaults to today → today + 30 days.
    """
    today = date.today()
    from_date = from_date or today
    to_date   = to_date   or (today + timedelta(days=30))

    filters = [
        ConsultationSlot.attorney_id == attorney_id,
        ConsultationSlot.slot_date >= from_date,
        ConsultationSlot.slot_date <= to_date,
        ConsultationSlot.is_blocked == False,
    ]
    if not include_booked:
        filters.append(ConsultationSlot.is_booked == False)

    result = await db.execute(
        select(ConsultationSlot)
        .where(and_(*filters))
        .order_by(ConsultationSlot.slot_date, ConsultationSlot.slot_time)
    )
    slots = list(result.scalars().all())

    return slots


def _slot_availability(slot: ConsultationSlot, booked_counts: dict) -> str:
    """
    'none'    → already booked
    'limited' → it's the last slot of the day (naive heuristic)
    'high'    → otherwise
    """
    if slot.is_booked:
        return "none"
    day_count = booked_counts.get(slot.slot_date, 0)
    if day_count >= 3:
        return "limited"
    return "high"


# =============================================================================
# Book-page aggregate
# =============================================================================

async def get_book_page_data(
    db: AsyncSession,
    attorney_id: Optional[uuid.UUID] = None,
    viewer_id: Optional[uuid.UUID] = None,
) -> BookConsultationPageData:
    """
    Single query that assembles everything the BookConsultation screen needs:
    - attorney profile (with nested user)
    - appointment types
    - available slots for the next 30 days

    `viewer_id` is the logged-in employee browsing this page. ConsultationSlot
    rows are stored as UTC — display_date/display_time are computed here,
    converted into the VIEWER's own timezone (from their profile, falling
    back to UTC if they never set one), so the frontend needs no timezone
    logic of its own — it just shows these two strings as-is.
    """
    from app.core.timeutils import to_viewer_local

    attorney = None
    slots: List[ConsultationSlot] = []

    if attorney_id:
        attorney = await get_attorney_by_id(db, attorney_id)
        if attorney:
            slots = await list_slots_for_attorney(db, attorney_id)

    appt_types = await list_appointment_types(db)

    # Compute availability label per slot
    # Count already-booked slots per day to determine "limited"
    booked_counts: dict[date, int] = {}
    if attorney_id:
        booked_result = await db.execute(
            select(ConsultationSlot.slot_date)
            .where(
                and_(
                    ConsultationSlot.attorney_id == attorney_id,
                    ConsultationSlot.is_booked == True,
                    ConsultationSlot.slot_date >= date.today(),
                )
            )
        )
        for d in booked_result.scalars().all():
            booked_counts[d] = booked_counts.get(d, 0) + 1

    viewer_tz = await get_user_timezone(db, viewer_id, fallback="UTC") if viewer_id else "UTC"

    slot_outs = []
    for s in slots:
        avail = _slot_availability(s, booked_counts)

        # s.slot_date/s.slot_time are stored as UTC — convert to the
        # viewer's own timezone before formatting for display.
        utc_dt   = datetime.combine(s.slot_date, s.slot_time, tzinfo=timezone.utc)
        local_dt = to_viewer_local(utc_dt, viewer_tz)
        tz_abbrev = local_dt.tzname() or viewer_tz

        out = ConsultationSlotOut(
            id=s.id,
            attorney_id=s.attorney_id,
            slot_date=s.slot_date,
            slot_time=s.slot_time,
            timezone=s.timezone,
            is_booked=s.is_booked,
            is_blocked=s.is_blocked,
            availability=avail,
            display_date=local_dt.date().isoformat(),
            display_time=f"{local_dt.strftime('%I:%M %p').lstrip('0')} {tz_abbrev}",
        )
        slot_outs.append(out)

    return BookConsultationPageData(
        attorney=AttorneyProfileOut.model_validate(attorney) if attorney else None,
        appointment_types=[AppointmentTypeOut.model_validate(a) for a in appt_types],
        slots=slot_outs,
    )


# =============================================================================
# Booking
# =============================================================================

async def create_booking(
    db: AsyncSession,
    data: CreateConsultationBookingRequest,
    employee_id: uuid.UUID,
) -> ConsultationBooking:
    """
    1. Validate slot is free
    2. Validate attorney is accepting cases
    3. Validate appointment type exists
    4. Create booking
    5. Mark slot as booked
    6. Send confirmation email + in-app notification to both parties
    """
    # ── Validate slot ────────────────────────────────────────────────────────
    slot = await db_get_by_id(db, ConsultationSlot, data.slot_id)
    if not slot:
        raise ValueError("Slot not found")
    if slot.is_booked:
        raise ValueError("This slot is already booked. Please choose another time.")
    if slot.is_blocked:
        raise ValueError("This slot is not available.")
    if slot.attorney_id != data.attorney_id:
        raise ValueError("Slot does not belong to this attorney.")

    # ── Validate attorney ────────────────────────────────────────────────────
    attorney = await get_attorney_by_id(db, data.attorney_id)
    if not attorney:
        raise ValueError("Attorney not found")
    if not attorney.is_accepting_cases:
        raise ValueError("This attorney is not currently accepting new cases.")

    # ── Validate appointment type ────────────────────────────────────────────
    appt_type = await db_get_by_id(db, AppointmentType, data.appointment_type_id)
    if not appt_type or not appt_type.is_active:
        raise ValueError("Appointment type not found or inactive.")

    # ── Validate case — marketplace gating (now optional) ────────────────────
    # CHANGED: only run this block if the frontend actually sent an application_id.
    # No application_id yet = self-petition flow isn't live = skip the check.
    if data.application_id:
        application = await db_get_by_id(db, Application, data.application_id)
        if not application:
            raise ValueError("Case not found.")
        if application.user_id != employee_id:
            raise ValueError("You can only book a consultation for your own case.")
        if application.case_origin != "self_petition":
            raise ValueError(
                "The attorney marketplace is only available for self-petition cases. "
                "Employer-sponsored cases already have an assigned attorney."
            )

    # ── Create booking ───────────────────────────────────────────────────────
    booking = ConsultationBooking(
        id=uuid.uuid4(),
        employee_id=employee_id,
        attorney_id=data.attorney_id,
        slot_id=data.slot_id,
        appointment_type_id=data.appointment_type_id,
        consultation_format=data.consultation_format,
        status="confirmed",   # CHANGED from "pending" — no manual review step exists
        amount_usd=appt_type.price_usd,
        employee_notes=data.employee_notes,
        created_by=employee_id,
        modified_by=employee_id,
    )
    try:
        await db_create(db, booking)
    except IntegrityError:
        await db.rollback()
        raise ValueError(
            "This slot was just booked by someone else. Please choose another time."
        )

    # ── Mark slot as booked ──────────────────────────────────────────────────
    await db_update(db, ConsultationSlot, slot.id, {"is_booked": True})

    # ── NEW: create Zoho meeting (best-effort) ────────────────────────────────
    # Wrapped in try/except so a Zoho outage or auth/scope problem never blocks
    # the booking itself — the booking still succeeds with an empty link.
    employee = await db_get_by_id(db, User, employee_id)
    try:
        from app.core.zoho_meeting import create_meeting
        from app.core.timeutils import to_utc

        # The slot's own timezone (e.g. "Asia/Kolkata") tells us what the
        # stored 09:00 actually means. Converting through it — instead of
        # treating 09:00 as if it were already UTC — is what makes the
        # real Zoho meeting land on the correct real-world moment no
        # matter which timezone the attorney set their hours in.
        start_dt_utc = to_utc(slot.slot_date, slot.slot_time, slot.timezone)
        zoho_resp = await create_meeting(
            topic            = f"{appt_type.title} — {attorney.user.first_name} & {employee.first_name}",
            start_time_utc   = start_dt_utc,
            duration_minutes = appt_type.duration_minutes,
            presenter_email  = attorney.user.email,
            attendee_emails  = [employee.email],
            agenda           = data.employee_notes or None,
        )
        session     = zoho_resp.get("session", {}) or {}
        join_link   = session.get("joinLink") or session.get("attendeeJoinLink")
        session_key = session.get("sessionKey") or session.get("meetingKey")

        if join_link:
            await db_update(db, ConsultationBooking, booking.id, {
                "meeting_link":     join_link,
                "zoho_session_key": session_key,
            })
            # Refresh in-memory row so the email/notification block below uses it
            booking.meeting_link     = join_link
            booking.zoho_session_key = session_key
    except Exception as e:
        # Booking still succeeds. Meeting can be manually re-created later.
        print(f"[create_booking] Zoho meeting create failed: {e}")

    # ── NEW: send confirmation email + in-app notification ───────────────────
    # Wrapped in try/except so a broken email server never blocks the booking itself.
    try:
        from app.core.timeutils import to_utc, format_in_timezone

        confirmation_no = f"VYU-{str(booking.id)[:6].upper()}"
        join_url = booking.meeting_link or ""   # empty if Zoho create failed above

        # The one true moment this consultation happens at, regardless of
        # who is looking at it — everything below is just this same instant
        # displayed in each viewer's own timezone.
        start_dt_utc = to_utc(slot.slot_date, slot.slot_time, slot.timezone)

        employee_tz = await get_user_timezone(db, employee.id, fallback=slot.timezone)
        attorney_tz = await get_user_timezone(db, attorney.user_id, fallback=slot.timezone)

        when_text_employee = format_in_timezone(start_dt_utc, employee_tz)
        when_text_attorney = format_in_timezone(start_dt_utc, attorney_tz)

        # -- Email to the employee --
        await send_email(
            to=employee.email,
            subject=f"Your consultation with {attorney.user.first_name} is confirmed",
            body=(
                f"Hi {employee.first_name},\n\n"
                f"Your {appt_type.title} with {attorney.user.first_name} {attorney.user.last_name} "
                f"is confirmed for {when_text_employee}.\n"
                f"Confirmation #: {confirmation_no}\n"
                f"{'Join link: ' + join_url if join_url else 'Meeting link will be shared before the call.'}\n\n"
                f"Thanks,\nVyuflo Team"
            ),
        )

        # -- Email to the attorney --
        await send_email(
            to=attorney.user.email,
            subject=f"New consultation booked — {employee.first_name} {employee.last_name}",
            body=(
                f"Hi {attorney.user.first_name},\n\n"
                f"{employee.first_name} {employee.last_name} ({employee.email}) booked a "
                f"{appt_type.title} with you for {when_text_attorney}.\n"
                f"Confirmation #: {confirmation_no}\n"
                f"{'Join link: ' + join_url if join_url else 'Meeting link will be shared before the call.'}\n\n"
                f"Thanks,\nVyuflo Team"
            ),
        )

        # -- In-app notification for the employee --
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=employee.id,
            notification_type="calendar_event_reminder",
            category="case_update",
            priority="medium",
            title=f"Consultation booked with {attorney.user.first_name} {attorney.user.last_name}",
            body=f"{appt_type.title} on {when_text_employee}. Meeting link has been emailed to you.",
            case_reference=confirmation_no,
            actor_id=attorney.user_id,
            actor_label=f"{attorney.user.first_name} {attorney.user.last_name}",
            cta_primary_label="View booking",
            cta_primary_url=join_url or None,
            is_read=False,
            created_by=employee.id,
        ))

        # -- In-app notification for the attorney --
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=attorney.user_id,
            notification_type="calendar_event_reminder",
            category="case_update",
            priority="medium",
            title=f"New consultation with {employee.first_name} {employee.last_name}",
            body=f"Scheduled for {when_text_attorney}. Client email: {employee.email}",
            case_reference=confirmation_no,
            actor_id=employee.id,
            actor_label=f"{employee.first_name} {employee.last_name}",
            is_read=False,
            created_by=employee.id,
        ))

        # -- NEW: notify assigned HR, if any --
        # Only fires when the booking is linked to an application that has an
        # assigned HR (employer-sponsored cases). Self-petition/marketplace
        # bookings have no application_id and are silently skipped — there's
        # no HR to notify. HR is not added to the Zoho meeting itself; they
        # just get the join link here and can join if they choose to.
        if booking.application_id:
            application = await db_get_by_id(db, Application, booking.application_id)
            if application and application.assigned_hr_id:
                hr_user = await db_get_by_id(db, User, application.assigned_hr_id)
                if hr_user:
                    hr_tz = await get_user_timezone(db, hr_user.id, fallback=slot.timezone)
                    when_text_hr = format_in_timezone(start_dt_utc, hr_tz)
                    db.add(Notification(
                        id=uuid.uuid4(),
                        user_id=hr_user.id,
                        notification_type="calendar_event_reminder",
                        category="case_update",
                        priority="low",
                        title=f"Consultation scheduled: {employee.first_name} {employee.last_name}",
                        body=(
                            f"{employee.first_name} {employee.last_name} has a "
                            f"{appt_type.title} with {attorney.user.first_name} "
                            f"{attorney.user.last_name} on {when_text_hr}. "
                            + ("You can join using the link below if needed."
                               if join_url else
                               "Meeting link will be shared before the call.")
                        ),
                        case_reference=confirmation_no,
                        actor_id=employee.id,
                        actor_label=f"{employee.first_name} {employee.last_name}",
                        cta_primary_label="Join meeting" if join_url else None,
                        cta_primary_url=join_url or None,
                        is_read=False,
                        created_by=employee.id,
                    ))
    except Exception as e:
        # Booking still succeeds even if email/notification fails — just log it.
        print(f"[create_booking] email/notification failed: {e}")

    # Reload with relationships
    result = await db.execute(
        select(ConsultationBooking)
        .options(
            selectinload(ConsultationBooking.slot),
            selectinload(ConsultationBooking.appointment_type),
            selectinload(ConsultationBooking.attorney).selectinload(AttorneyProfile.user),
        )
        .where(ConsultationBooking.id == booking.id)
    )
    return result.scalar_one()

async def list_bookings_for_employee(
    db: AsyncSession,
    employee_id: uuid.UUID,
) -> List[ConsultationBooking]:
    result = await db.execute(
        select(ConsultationBooking)
        .options(
            selectinload(ConsultationBooking.slot),
            selectinload(ConsultationBooking.appointment_type),
            selectinload(ConsultationBooking.attorney).selectinload(AttorneyProfile.user),
        )
        .where(ConsultationBooking.employee_id == employee_id)
        .order_by(ConsultationBooking.created_at.desc())
    )
    return list(result.scalars().all())


async def cancel_booking(
    db: AsyncSession,
    booking_id: uuid.UUID,
    cancelled_by: uuid.UUID,
    reason: Optional[str] = None,
) -> ConsultationBooking:
    booking = await db_get_by_id(db, ConsultationBooking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    if booking.status in ("cancelled", "completed"):
        raise ValueError(f"Cannot cancel a booking with status '{booking.status}'")

    # Free the slot
    await db_update(db, ConsultationSlot, booking.slot_id, {"is_booked": False})

    # Update booking
    updated = await db_update(db, ConsultationBooking, booking_id, {
        "status":               "cancelled",
        "cancellation_reason":  reason,
        "cancelled_at":         _now(),
        "cancelled_by":         cancelled_by,
        "modified_by":          cancelled_by,
    })

    # ── NEW: delete the Zoho meeting (best-effort) ────────────────────────────
    if booking.zoho_session_key:
        try:
            from app.core.zoho_meeting import delete_meeting
            await delete_meeting(booking.zoho_session_key)
        except Exception as e:
            print(f"[cancel_booking] Zoho meeting delete failed: {e}")

    # ── NEW: notify assigned HR of the cancellation, if any ───────────────────
    # Same silent-skip rule as create_booking — only fires when the booking
    # is linked to an application with an assigned HR.
    try:
        if booking.application_id:
            application = await db_get_by_id(db, Application, booking.application_id)
            if application and application.assigned_hr_id:
                hr_user = await db_get_by_id(db, User, application.assigned_hr_id)
                employee = await db_get_by_id(db, User, booking.employee_id)
                if hr_user and employee:
                    confirmation_no = f"VYU-{str(booking.id)[:6].upper()}"
                    db.add(Notification(
                        id=uuid.uuid4(),
                        user_id=hr_user.id,
                        notification_type="calendar_event_reminder",
                        category="case_update",
                        priority="low",
                        title=f"Consultation cancelled: {employee.first_name} {employee.last_name}",
                        body=(
                            f"The consultation for {employee.first_name} "
                            f"{employee.last_name} has been cancelled."
                            + (f" Reason: {reason}" if reason else "")
                        ),
                        case_reference=confirmation_no,
                        actor_id=cancelled_by,
                        is_read=False,
                        created_by=cancelled_by,
                    ))
    except Exception as e:
        print(f"[cancel_booking] HR notification failed: {e}")

    return updated