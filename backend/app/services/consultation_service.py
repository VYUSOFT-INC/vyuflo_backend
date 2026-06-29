# =============================================================================
# app/services/consultation_service.py
# All business logic for consultations.
# Routes stay thin — call these functions directly.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import date, time, datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    User,
    AttorneyProfile,
    AppointmentType,
    AttorneyAvailability,
    ConsultationSlot,
    ConsultationBooking,
)
from app.schemas.consultation_schemas import (
    CreateConsultationBookingRequest,
    AttorneyAvailabilityCreateRequest,
    AppointmentTypeCreateRequest,
    SlotGenerateRequest,
    BookConsultationPageData,
    AttorneyProfileOut,
    AppointmentTypeOut,
    ConsultationSlotOut,
)
from app.services.services import db_create, db_get_by_id, db_update


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


# =============================================================================
# Slot generation — called by attorney or cron job
# Generates ConsultationSlot rows from AttorneyAvailability for a date range
# =============================================================================

async def generate_slots(
    db: AsyncSession,
    data: SlotGenerateRequest,
) -> List[ConsultationSlot]:
    """
    Walk every day in [from_date, to_date].
    For each day that matches an availability rule (day_of_week),
    generate time slots spaced by slot_duration_minutes.
    Skip days that already have slots.
    """
    availability_rows = await list_attorney_availability(db, data.attorney_id)
    if not availability_rows:
        return []

    # Build lookup: day_of_week → availability rule
    avail_by_day: dict[int, AttorneyAvailability] = {}
    for row in availability_rows:
        avail_by_day[row.day_of_week] = row

    created: List[ConsultationSlot] = []
    current = data.from_date

    while current <= data.to_date:
        dow = current.weekday()  # 0=Monday … 6=Sunday
        if dow in avail_by_day:
            rule = avail_by_day[dow]

            # Check which slots already exist for this date
            existing_result = await db.execute(
                select(ConsultationSlot.slot_time).where(
                    and_(
                        ConsultationSlot.attorney_id == data.attorney_id,
                        ConsultationSlot.slot_date == current,
                    )
                )
            )
            existing_times = set(existing_result.scalars().all())

            # Walk start→end in steps of slot_duration_minutes
            slot_dt = datetime.combine(current, rule.start_time)
            end_dt  = datetime.combine(current, rule.end_time)

            while slot_dt < end_dt:
                t = slot_dt.time()
                if t not in existing_times:
                    slot = ConsultationSlot(
                        id=uuid.uuid4(),
                        attorney_id=data.attorney_id,
                        slot_date=current,
                        slot_time=t,
                        timezone=rule.timezone,
                    )
                    db.add(slot)
                    created.append(slot)
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
) -> BookConsultationPageData:
    """
    Single query that assembles everything the BookConsultation screen needs:
    - attorney profile (with nested user)
    - appointment types
    - available slots for the next 30 days
    """
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

    slot_outs = []
    for s in slots:
        avail = _slot_availability(s, booked_counts)
        out = ConsultationSlotOut(
            id=s.id,
            attorney_id=s.attorney_id,
            slot_date=s.slot_date,
            slot_time=s.slot_time,
            timezone=s.timezone,
            is_booked=s.is_booked,
            is_blocked=s.is_blocked,
            availability=avail,
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

    # ── Create booking ───────────────────────────────────────────────────────
    booking = ConsultationBooking(
        id=uuid.uuid4(),
        employee_id=employee_id,
        attorney_id=data.attorney_id,
        slot_id=data.slot_id,
        appointment_type_id=data.appointment_type_id,
        consultation_format=data.consultation_format,
        status="pending",
        amount_usd=appt_type.price_usd,
        employee_notes=data.employee_notes,
        created_by=employee_id,
        modified_by=employee_id,
    )
    await db_create(db, booking)

    # ── Mark slot as booked ──────────────────────────────────────────────────
    await db_update(db, ConsultationSlot, slot.id, {"is_booked": True})

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
    return updated