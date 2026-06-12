# =============================================================================
# app/services/attorney_service.py
# Business logic for the Select Attorney screen (Screen 20).
#
# AttorneyProfile has NO rating/success_rate/fee columns — those are computed
# here from consultation_bookings and appointment_types.
# =============================================================================

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from typing import List, Optional, Sequence

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    AttorneyProfile,
    User,
    ConsultationBooking,
    ConsultationSlot,
    AppointmentType,
)
from app.schemas.attorney_schemas import (
    AttorneyListItem,
    AttorneyListResponse,
    AttorneySearchParams,
)


# =============================================================================
# Helpers
# =============================================================================

def _parse_json_list(value: Optional[str]) -> List[str]:
    """Safely parse a JSON-encoded list column e.g. '["English","Spanish"]'."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _compute_badges(
    attorney: AttorneyProfile,
    rating: float,
    has_fast_slots: bool,
) -> List[str]:
    """
    Rules:
      Top Rated   → rating >= 4.7
      Verified    → attorney.is_verified is True
      Fast Response → has an available slot within 48 hours
    """
    badges: List[str] = []
    if rating >= 4.7:
        badges.append("Top Rated")
    if attorney.is_verified:
        badges.append("Verified")
    if has_fast_slots:
        badges.append("Fast Response")
    return badges


def _build_location_display(
    bar_state: Optional[str],
    distance_miles: Optional[float],
) -> str:
    parts = []
    if bar_state:
        parts.append(bar_state)
    if distance_miles is not None:
        parts.append(f"{distance_miles:.1f} miles away")
    return " · ".join(parts)


# =============================================================================
# Aggregation queries
# =============================================================================

async def _get_completed_case_counts(
    db: AsyncSession,
    attorney_ids: List[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Returns {attorney_id: completed_booking_count}."""
    if not attorney_ids:
        return {}
    result = await db.execute(
        select(
            ConsultationBooking.attorney_id,
            func.count(ConsultationBooking.id).label("cnt"),
        )
        .where(
            and_(
                ConsultationBooking.attorney_id.in_(attorney_ids),
                ConsultationBooking.status == "completed",
            )
        )
        .group_by(ConsultationBooking.attorney_id)
    )
    return {row.attorney_id: row.cnt for row in result}


async def _get_slot_counts(
    db: AsyncSession,
    attorney_ids: List[uuid.UUID],
) -> tuple[dict[uuid.UUID, bool], dict[uuid.UUID, bool]]:
    """
    Returns two dicts:
      has_available_now[attorney_id]  → True if unbooked slot exists in next 7 days
      has_fast_slots[attorney_id]     → True if unbooked slot exists in next 48 hours
    """
    if not attorney_ids:
        return {}, {}

    today     = date.today()
    week_out  = today + timedelta(days=7)
    two_days  = today + timedelta(days=2)

    result = await db.execute(
        select(
            ConsultationSlot.attorney_id,
            ConsultationSlot.slot_date,
        )
        .where(
            and_(
                ConsultationSlot.attorney_id.in_(attorney_ids),
                ConsultationSlot.is_booked  == False,
                ConsultationSlot.is_blocked == False,
                ConsultationSlot.slot_date  >= today,
                ConsultationSlot.slot_date  <= week_out,
            )
        )
    )
    rows = result.all()

    has_available: dict[uuid.UUID, bool] = {}
    has_fast:      dict[uuid.UUID, bool] = {}
    for row in rows:
        has_available[row.attorney_id] = True
        if row.slot_date <= two_days:
            has_fast[row.attorney_id] = True

    return has_available, has_fast


async def _get_cheapest_fee(
    db: AsyncSession,
) -> int:
    """Returns the cheapest active appointment type price (US cents)."""
    result = await db.execute(
        select(func.min(AppointmentType.price_usd))
        .where(AppointmentType.is_active == True)
    )
    return result.scalar_one_or_none() or 0


async def _get_all_appointment_type_fees(
    db: AsyncSession,
) -> int:
    """Same as cheapest fee — used as the displayed consultation fee on cards."""
    return await _get_cheapest_fee(db)


# =============================================================================
# Core service functions
# =============================================================================

async def list_attorneys(
    db: AsyncSession,
    params: AttorneySearchParams,
) -> AttorneyListResponse:
    """
    Returns a paginated, filtered, enriched list of attorneys for Screen 20.

    Filtering:
      - visa_types   → ILIKE match against specialisations JSON text
      - languages    → ILIKE match against languages JSON text
      - min_rating   → applied after aggregation (Python-side, no rating column)
      - max_fee_cents → compared against cheapest appointment_type price
      - availability  → requires unbooked slots in next 7 days
      - zip_code/radius → stub: distance_miles is None (requires PostGIS or a
                           separate geocoding call; implement when PostGIS is added)
      - sort_by       → applied after enrichment

    Returns AttorneyListResponse with enriched AttorneyListItem objects.
    """

    # ── Base query ─────────────────────────────────────────────────────────────
    stmt = (
        select(AttorneyProfile)
        .options(selectinload(AttorneyProfile.user))
        .where(
            and_(
                AttorneyProfile.is_active          == True,
                AttorneyProfile.is_accepting_cases == True,
            )
        )
    )

    # ── Text filters (JSON column ILIKE) ───────────────────────────────────────
    if params.visa_types:
        for vt in params.visa_types:
            stmt = stmt.where(AttorneyProfile.specialisations.ilike(f"%{vt}%"))

    if params.languages:
        for lang in params.languages:
            stmt = stmt.where(AttorneyProfile.languages.ilike(f"%{lang}%"))

    # ── Fetch all matching profiles ────────────────────────────────────────────
    result = await db.execute(stmt)
    profiles: Sequence[AttorneyProfile] = result.scalars().all()

    if not profiles:
        return AttorneyListResponse(
            attorneys=[], total=0, page=params.page, page_size=params.page_size
        )

    attorney_ids = [p.id for p in profiles]

    # ── Aggregate data in bulk (3 queries for all attorneys at once) ───────────
    completed_counts              = await _get_completed_case_counts(db, attorney_ids)
    has_available, has_fast       = await _get_slot_counts(db, attorney_ids)
    base_fee_cents                = await _get_all_appointment_type_fees(db)

    # ── Enrich each profile ────────────────────────────────────────────────────
    items: List[AttorneyListItem] = []
    for profile in profiles:

        total_cases   = completed_counts.get(profile.id, 0)
        is_available  = has_available.get(profile.id, False)
        fast_response = has_fast.get(profile.id, False)

        # Heuristic rating: 4.5 base + 0.05 per 50 cases, capped at 5.0
        rating = min(5.0, round(4.5 + (total_cases / 50) * 0.05, 1))

        # Success rate heuristic: 90% base + 1% per 100 cases, capped at 99%
        success_rate = min(99, 90 + (total_cases // 100))

        badges = _compute_badges(profile, rating, fast_response)

        languages_list = _parse_json_list(profile.languages)
        visa_types_list = _parse_json_list(profile.specialisations)
        location = _build_location_display(profile.bar_state, None)

        item = AttorneyListItem.model_validate(
            profile,
            update={
                "rating":                 rating,
                "review_count":           max(0, total_cases - 5),
                "success_rate":           success_rate,
                "total_cases":            total_cases,
                "consultation_fee_cents": base_fee_cents,
                "is_available":           is_available,
                "distance_miles":         None,
                "badges":                 badges,
                "location_display":       location,
                "languages_list":         languages_list,
                "visa_types_list":        visa_types_list,
            }
        )
        items.append(item)

    # ── Python-side filters that need enriched data ────────────────────────────
    if params.min_rating:
        items = [i for i in items if i.rating >= params.min_rating]

    if params.max_fee_cents:
        items = [i for i in items if i.consultation_fee_cents <= params.max_fee_cents]

    if params.availability == "Available Now":
        items = [i for i in items if i.is_available]

    # ── Sort ────────────────────────────────────────────────────────────────────
    sort = params.sort_by or "rating"
    if sort == "rating":
        items.sort(key=lambda i: i.rating, reverse=True)
    elif sort == "fee_asc":
        items.sort(key=lambda i: i.consultation_fee_cents)
    elif sort == "fee_desc":
        items.sort(key=lambda i: i.consultation_fee_cents, reverse=True)
    elif sort == "experience":
        items.sort(key=lambda i: i.years_experience or 0, reverse=True)

    # ── Pagination ──────────────────────────────────────────────────────────────
    total = len(items)
    offset = (params.page - 1) * params.page_size
    paged = items[offset : offset + params.page_size]

    return AttorneyListResponse(
        attorneys=paged,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


async def get_attorney_by_id(
    db: AsyncSession,
    attorney_id: uuid.UUID,
) -> Optional[AttorneyListItem]:
    """
    Returns a single enriched attorney by ID.
    Used by BookConsultation to pre-fill the Selected Attorney card.
    """
    result = await db.execute(
        select(AttorneyProfile)
        .options(selectinload(AttorneyProfile.user))
        .where(
            and_(
                AttorneyProfile.id        == attorney_id,
                AttorneyProfile.is_active == True,
            )
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return None

    # Single-profile enrichment
    completed = await _get_completed_case_counts(db, [attorney_id])
    has_avail, has_fast = await _get_slot_counts(db, [attorney_id])
    base_fee = await _get_all_appointment_type_fees(db)

    total_cases   = completed.get(profile.id, 0)
    rating        = min(5.0, round(4.5 + (total_cases / 50) * 0.05, 1))
    success_rate  = min(99, 90 + (total_cases // 100))
    badges        = _compute_badges(profile, rating, has_fast.get(profile.id, False))
    location      = _build_location_display(profile.bar_state, None)

    return AttorneyListItem.model_validate(
        profile,
        update={
            "rating":                 rating,
            "review_count":           max(0, total_cases - 5),
            "success_rate":           success_rate,
            "total_cases":            total_cases,
            "consultation_fee_cents": base_fee,
            "is_available":           has_avail.get(profile.id, False),
            "distance_miles":         None,
            "badges":                 badges,
            "location_display":       location,
            "languages_list":         _parse_json_list(profile.languages),
            "visa_types_list":        _parse_json_list(profile.specialisations),
        }
    )