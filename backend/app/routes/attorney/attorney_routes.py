# =============================================================================
# app/api/v1/attorney_routes.py
# Routes for the Select Attorney screen (Screen 20).
#
# Register in main.py:
#   from app.api.v1.attorney_routes import router as attorney_router
#   app.include_router(attorney_router, prefix="/api/v1", tags=["attorneys"])
# =============================================================================

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.visamodels import User
from app.schemas.attorney.attorney_schemas import (
    AttorneyListItem,
    AttorneyListResponse,
    AttorneySearchParams,
)
from app.services.attorney.attorney_service import (
    list_attorneys,
    get_attorney_by_id,
)

# from app.services.attorney import intake_service
# from app.schemas.attorney.intake import (
    # GenerateLinkResponse,
    # IntakeDataResponse,
    # IntakeDataSave,
    # IntakeSessionCreate,
    # IntakeSessionResponse,
    # SaveDraftResponse,
    # SubmitIntakeResponse,
    # VisaStatusOptionsResponse,
# )
attorney_router = APIRouter()


# =============================================================================
# GET /api/v1/attorneys
# Screen 20 — Select Attorney by ZIP Code — card grid
# =============================================================================

@attorney_router.get(
    "/attorneys",
    response_model=AttorneyListResponse,
    summary="List attorneys — Screen 20 Select Attorney",
    description="""
    Returns a paginated, filtered list of active immigration attorneys.

    **Filtering** (all optional):
    - `zip_code` + `radius_miles` — proximity filter (stub: distance_miles = null until PostGIS added)
    - `visa_types[]` — multi-value, ILIKE match against specialisations
    - `languages[]` — multi-value, ILIKE match against languages
    - `min_rating` — minimum star rating (computed, not stored)
    - `max_fee_cents` — max consultation fee in US cents
    - `availability` — `"Available Now"` requires unbooked slot within 7 days

    **Sorting** (`sort_by`):
    - `rating` (default) · `fee_asc` · `fee_desc` · `experience`

    **Enriched fields** (computed by service, not on DB table):
    - `rating`, `review_count`, `success_rate`, `total_cases`
    - `consultation_fee_cents` — cheapest active appointment type
    - `is_available` — True if unbooked slot in next 7 days
    - `badges` — ["Top Rated", "Verified", "Fast Response"]
    - `languages_list`, `visa_types_list` — parsed from JSON text columns
    """,
)
async def api_list_attorneys(
    # ── Proximity ──────────────────────────────────────────────────────────────
    zip_code:      Optional[str]        = Query(None, description="5-digit US ZIP code"),
    radius_miles:  Optional[int]        = Query(25,   description="Search radius in miles"),

    # ── Filters ────────────────────────────────────────────────────────────────
    visa_types:    Optional[List[str]]  = Query(None, description="e.g. H-1B, EB-2, O-1"),
    languages:     Optional[List[str]]  = Query(None, description="e.g. English, Spanish"),
    min_rating:    Optional[float]      = Query(None, ge=0.0, le=5.0),
    max_fee_cents: Optional[int]        = Query(None, ge=0, description="Max fee in US cents"),
    availability:  Optional[str]        = Query(None, description="Available Now | Within 24h | Within 48h"),

    # ── Sort + Pagination ───────────────────────────────────────────────────────
    sort_by:       Optional[str]        = Query("rating", description="rating | fee_asc | fee_desc | experience"),
    page:          int                  = Query(1,   ge=1),
    page_size:     int                  = Query(20,  ge=1, le=100),

    # ── Dependencies ───────────────────────────────────────────────────────────
    db:            AsyncSession         = Depends(get_db),
    current_user:  User                 = Depends(get_current_user),
):
    params = AttorneySearchParams(
        zip_code=zip_code,
        radius_miles=radius_miles,
        visa_types=visa_types,
        languages=languages,
        min_rating=min_rating,
        max_fee_cents=max_fee_cents,
        availability=availability,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return await list_attorneys(db, params)


# =============================================================================
# GET /api/v1/attorneys/{attorney_id}
# Used by BookConsultation to pre-fill the Selected Attorney card
# =============================================================================

@attorney_router.get(
    "/attorneys/{attorney_id}",
    response_model=AttorneyListItem,
    summary="Get single attorney — pre-fill for BookConsultation screen",
)
async def api_get_attorney(
    attorney_id:  uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    attorney = await get_attorney_by_id(db, attorney_id)
    if not attorney:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attorney not found or not currently accepting cases.",
        )
    return attorney