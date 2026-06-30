# =============================================================================
# app/api/v1/consultation_routes.py
#
# Register in main.py:
#   from app.api.v1.consultation_routes import router as consultation_router
#   app.include_router(consultation_router, prefix="/api/v1", tags=["consultations"])
# =============================================================================

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.models.visamodels import ConsultationBooking
from app.schemas.employee.consultation_schemas import (
    AttorneyProfileOut,
    AppointmentTypeOut,
    AppointmentTypeCreateRequest,
    AttorneyAvailabilityOut,
    AttorneyAvailabilityCreateRequest,
    ConsultationSlotOut,
    SlotGenerateRequest,
    ConsultationBookingOut,
    CreateConsultationBookingRequest,
    CreateConsultationBookingResponse,
    CancelBookingRequest,
    BookConsultationPageData,
)
from app.services.employee.consultation_service import (
    list_attorneys,
    get_attorney_by_id,
    list_appointment_types,
    create_appointment_type,
    list_attorney_availability,
    set_attorney_availability,
    generate_slots,
    list_slots_for_attorney,
    get_book_page_data,
    create_booking,
    list_bookings_for_employee,
    cancel_booking,
)

consultation_router = APIRouter()


# =============================================================================
# ── ATTORNEYS ─────────────────────────────────────────────────────────────────
# =============================================================================

@consultation_router.get(
    "/attorneys",
    response_model=List[AttorneyProfileOut],
    summary="List all attorneys accepting cases (Screen 19 Step 1)",
)
async def api_list_attorneys(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Used by SelectAttorney screen — lists all active, accepting attorneys
    with their nested user (first_name, last_name, email).
    """
    return await list_attorneys(db, accepting_only=True)


@consultation_router.get(
    "/attorneys/{attorney_id}",
    response_model=AttorneyProfileOut,
    summary="Get a single attorney profile",
)
async def api_get_attorney(
    attorney_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    attorney = await get_attorney_by_id(db, attorney_id)
    if not attorney:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Attorney not found")
    return attorney


# =============================================================================
# ── APPOINTMENT TYPES ────────────────────────────────────────────────────────
# =============================================================================

@consultation_router.get(
    "/consultations/appointment-types",
    response_model=List[AppointmentTypeOut],
    summary="List all active appointment types",
)
async def api_list_appointment_types(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await list_appointment_types(db)


@consultation_router.post(
    "/consultations/appointment-types",
    response_model=AppointmentTypeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an appointment type (admin)",
)
async def api_create_appointment_type(
    body:         AppointmentTypeCreateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await create_appointment_type(db, body, created_by=current_user.id)


# =============================================================================
# ── ATTORNEY AVAILABILITY ────────────────────────────────────────────────────
# =============================================================================

@consultation_router.get(
    "/attorneys/{attorney_id}/availability",
    response_model=List[AttorneyAvailabilityOut],
    summary="Get attorney's weekly availability rules",
)
async def api_get_availability(
    attorney_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await list_attorney_availability(db, attorney_id)


@consultation_router.post(
    "/attorneys/{attorney_id}/availability",
    response_model=AttorneyAvailabilityOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a weekly availability rule for an attorney",
)
async def api_set_availability(
    attorney_id:  uuid.UUID,
    body:         AttorneyAvailabilityCreateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await set_attorney_availability(db, attorney_id, body)


# =============================================================================
# ── SLOTS ────────────────────────────────────────────────────────────────────
# =============================================================================

@consultation_router.get(
    "/attorneys/{attorney_id}/slots",
    response_model=List[ConsultationSlotOut],
    summary="List available slots for an attorney",
)
async def api_list_slots(
    attorney_id:   uuid.UUID,
    from_date:     Optional[date] = Query(None),
    to_date:       Optional[date] = Query(None),
    db:            AsyncSession   = Depends(get_db),
    current_user:  User           = Depends(get_current_user),
):
    """
    Returns unbooked, unblocked slots.
    Defaults to today → today + 30 days if no dates given.
    """
    return await list_slots_for_attorney(db, attorney_id, from_date, to_date)


@consultation_router.post(
    "/attorneys/{attorney_id}/slots/generate",
    response_model=List[ConsultationSlotOut],
    status_code=status.HTTP_201_CREATED,
    summary="Generate slots from availability rules (attorney/admin)",
)
async def api_generate_slots(
    attorney_id:  uuid.UUID,
    body:         SlotGenerateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Walks the date range and creates ConsultationSlot rows based on
    AttorneyAvailability rules. Safe to call multiple times — skips
    dates that already have slots.
    """
    body.attorney_id = attorney_id   # enforce from URL
    slots = await generate_slots(db, body)
    await db.commit()
    return slots


# =============================================================================
# ── BOOK-PAGE AGGREGATE ───────────────────────────────────────────────────────
# =============================================================================

@consultation_router.get(
    "/consultations/book-page",
    response_model=BookConsultationPageData,
    summary="Aggregate endpoint — everything Screen 19 needs in one call",
)
async def api_book_page(
    attorney_id:  Optional[uuid.UUID] = Query(None),
    db:           AsyncSession         = Depends(get_db),
    current_user: User                 = Depends(get_current_user),
):
    """
    Returns:
    - attorney profile (null if no attorney_id given)
    - all active appointment types
    - available slots for the next 30 days

    Frontend calls:
        GET /api/v1/consultations/book-page?attorney_id=<uuid>
    """
    return await get_book_page_data(db, attorney_id)


# =============================================================================
# ── BOOKINGS ──────────────────────────────────────────────────────────────────
# =============================================================================

@consultation_router.post(
    "/consultations/bookings",
    response_model=CreateConsultationBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a consultation slot",
)
async def api_create_booking(
    body:         CreateConsultationBookingRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Called when user clicks 'Confirm Booking' on Screen 19.
    - Validates slot is free
    - Creates ConsultationBooking
    - Marks slot as booked (atomic within same transaction)
    """
    try:
        booking = await create_booking(db, body, employee_id=current_user.id)
        await db.commit()
        return CreateConsultationBookingResponse(
            id=booking.id,
            status=booking.status,
            message="Booking confirmed. The attorney will send a meeting link shortly.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@consultation_router.get(
    "/consultations/bookings",
    response_model=List[ConsultationBookingOut],
    summary="List current user's consultation bookings",
)
async def api_list_my_bookings(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await list_bookings_for_employee(db, current_user.id)


@consultation_router.get(
    "/consultations/bookings/{booking_id}",
    response_model=ConsultationBookingOut,
    summary="Get a single booking",
)
async def api_get_booking(
    booking_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.visamodels import AttorneyProfile

    result = await db.execute(
        select(ConsultationBooking)
        .options(
            selectinload(ConsultationBooking.slot),
            selectinload(ConsultationBooking.appointment_type),
            selectinload(ConsultationBooking.attorney).selectinload(AttorneyProfile.user),
        )
        .where(
            and_(
                ConsultationBooking.id == booking_id,
                ConsultationBooking.employee_id == current_user.id,
            )
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Booking not found")
    return booking


@consultation_router.post(
    "/consultations/bookings/{booking_id}/cancel",
    response_model=ConsultationBookingOut,
    summary="Cancel a booking",
)
async def api_cancel_booking(
    booking_id:   uuid.UUID,
    body:         CancelBookingRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Cancels the booking and frees the slot so another user can book it.
    """
    try:
        booking = await cancel_booking(
            db, booking_id,
            cancelled_by=current_user.id,
            reason=body.reason,
        )
        await db.commit()
        return booking
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))