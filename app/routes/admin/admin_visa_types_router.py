"""
app/api/v1/admin_visa_types.py  ← NEW FILE

Admin Visa Types Manager — all endpoints for the UI screen.

Mount in main.py:
    from app.api.v1.admin_visa_types import admin_visa_types_router
    app.include_router(admin_visa_types_router, prefix="/api/v1", tags=["Admin — Visa Types"])

──────────────────────────────────────────────────────────────────────────────
ENDPOINT MAP  →  UI Component
──────────────────────────────────────────────────────────────────────────────
GET  /admin/visa-types/stats          → 4 KPI cards (total, active, pending, cases)
GET  /admin/visa-types                → card grid + embedded stats
GET  /admin/visa-types/export         → "Export All" button  ← BEFORE /{id}
GET  /admin/visa-types/{id}           → "View Details" panel
POST /admin/visa-types                → "Add New Visa Type" button
PATCH /admin/visa-types/{id}/toggle   → Active/Inactive badge switch  ← BEFORE /{id}
PATCH /admin/visa-types/{id}          → "Edit" action
DELETE /admin/visa-types/{id}         → Delete (soft)

NOTE: Route ORDER matters in FastAPI.
  /export and /{id}/toggle are declared BEFORE /{id} to avoid path collisions.
──────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.admin.visa_type import (
    VisaTypeCreate,
    VisaTypeListResponse,
    VisaTypeResponse,
    VisaTypeStats,
    VisaTypeToggle,
    VisaTypeUpdate,
)
from app.services.admin.visa_type_service import (
    service_create_visa_type,
    service_delete_visa_type,
    service_export_visa_types,
    service_get_visa_type,
    service_get_visa_type_stats,
    service_list_visa_types,
    service_toggle_visa_type,
    service_update_visa_type,
)
from app.schemas.admin.visa_type import VisaTypeStats

admin_visa_types_router = APIRouter()

# Permission guard — only app_admin can manage visa types
_require_manage = PermissionChecker("visa_types.manage")
# Read-only access — admins + hr can view
_require_view   = PermissionChecker(["visa_types.manage", "applications.view_all"])


# =============================================================================
# GET /admin/visa-types/stats
# ─────────────────────────────────────────────────────────────────────────────
# Powers the 4 KPI cards at the top of the screen:
#   Card 1 → Total Visa Types   (52)  ↑12%
#   Card 2 → Active Visa Types  (48)  ↑8%
#   Card 3 → Pending Review     (4)   —0%
#   Card 4 → Active Cases       (3,247) ↑24%
#
# Declared BEFORE /admin/visa-types/{id} — "stats" must not be treated as UUID
# =============================================================================
@admin_visa_types_router.get(
    "/admin/visa-types/stats",
    response_model=VisaTypeStats,
    status_code=status.HTTP_200_OK,
    summary="Visa Types KPI stats",
    description=(
        "Returns the 4 KPI card values shown at the top of the Visa Types Manager. "
        "Runs 4 aggregation queries — cache this response for ~60 seconds in prod."
    ),
)
async def get_visa_type_stats(
    db: DBSession,
    _:  Current_User = _require_view,
) -> VisaTypeStats:
    """
    Roles:      app_admin, hr (anyone with applications.view_all)
    Permission: visa_types.manage | applications.view_all
    DB:         4 COUNT queries on visa_types + applications
    Cache:      Recommend 60-second TTL — counts change infrequently
    """
    data = await service_get_visa_type_stats(db)
    return VisaTypeStats(**data)


# =============================================================================
# GET /admin/visa-types/export
# ─────────────────────────────────────────────────────────────────────────────
# Powers the "Export All" button — returns CSV download
# Declared BEFORE /{id} — "export" must not be treated as UUID
# =============================================================================
@admin_visa_types_router.get(
    "/admin/visa-types/export",
    status_code=status.HTTP_200_OK,
    summary="Export visa types as CSV",
    description=(
        "Streams a CSV file containing all visa types. "
        "Respects the same category and status filters as the list endpoint. "
        "Returns Content-Disposition: attachment so browser auto-downloads."
    ),
)
async def export_visa_types(
    db:       DBSession,
    _:        Current_User = _require_manage,
    category: Optional[str] = Query(
        None,
        description="Filter exported rows: employment | student | visitor | "
                    "permanent_resident | exchange",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="active | inactive | pending_review",
    ),
) -> StreamingResponse:
    """
    Roles:      app_admin
    Permission: visa_types.manage
    Returns:    StreamingResponse (text/csv) — browser triggers download
    Filename:   visa_types_export.csv
    """
    csv_content = await service_export_visa_types(
        db,
        category=category,
        status=status_filter,
    )

    def _iter():
        yield csv_content

    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=visa_types_export.csv"
        },
    )


# =============================================================================
# GET /admin/visa-types
# ─────────────────────────────────────────────────────────────────────────────
# Main screen — card grid + embedded KPI stats in ONE request
#
# UI components powered:
#   - Search bar    → ?search=H-1B
#   - Category dropdown → ?category=employment
#   - Status dropdown   → ?status=active
#   - Sort dropdown     → ?sort_by=name&sort_order=asc
#   - Pagination        → ?page=1&page_size=20
#   - KPI cards         → response.stats
#   - Visa cards grid   → response.items
# =============================================================================
@admin_visa_types_router.get(
    "/admin/visa-types",
    response_model=VisaTypeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List visa types — admin grid with stats",
    description=(
        "Returns the KPI stats + paginated visa type cards in one response. "
        "Supports search (name/code), category filter, status filter, "
        "sort by name/display_order/created_at, and page-based pagination."
    ),
)
async def list_visa_types(
    db:            DBSession,
    _:             Current_User = _require_view,
    search:        Optional[str] = Query(
        None,
        min_length=1,
        description="Search by visa name or code",
    ),
    category:      Optional[str] = Query(
        None,
        description="employment | student | visitor | permanent_resident | exchange",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="active | inactive | pending_review",
    ),
    sort_by:       str = Query(
        "display_order",
        description="name | code | display_order | created_at | updated_at",
    ),
    sort_order:    str = Query(
        "asc",
        description="asc | desc",
        pattern="^(asc|desc)$",
    ),
    page:          int = Query(1,  ge=1),
    page_size:     int = Query(20, ge=1, le=100),
) -> VisaTypeListResponse:
    """
    Roles:      app_admin, hr
    Permission: visa_types.manage | applications.view_all
    DB:         SELECT visa_types + active_cases subquery + modified_by join
    Note:       Stats are bundled — no second /stats call needed from frontend
    """
    items, total, stats = await service_list_visa_types(
        db,
        search     = search,
        category   = category,
        status     = status_filter,
        sort_by    = sort_by,
        sort_order = sort_order,
        page       = page,
        page_size  = page_size,
    )

    import math
    total_pages = max(1, math.ceil(total / page_size))

    # Build response items — map ORM enriched objects to schema
    response_items = []
    for vt in items:
        item = VisaTypeResponse.model_validate(vt)
        # Inject computed fields that were set as temp attributes
        if hasattr(vt, "_active_cases_count"):
            object.__setattr__(item, "active_cases_count", vt._active_cases_count)
        if hasattr(vt, "_modified_by_name"):
            object.__setattr__(item, "modified_by_name", vt._modified_by_name)
        if hasattr(vt, "_processing_time_label"):
            object.__setattr__(item, "processing_time_label", vt._processing_time_label)
        response_items.append(item)

    return VisaTypeListResponse(
        stats      = VisaTypeStats(**stats),
        items      = response_items,
        total      = total,
        page       = page,
        page_size  = page_size,
        total_pages = total_pages,
    )


# =============================================================================
# POST /admin/visa-types
# ─────────────────────────────────────────────────────────────────────────────
# Triggered by "Add New Visa Type" button → modal form submit
# =============================================================================
@admin_visa_types_router.post(
    "/admin/visa-types",
    response_model=VisaTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new visa type",
    description=(
        "Creates a new visa type. "
        "`code` must be unique (e.g. 'H-2A'). "
        "`required_documents` must be a JSON array string: "
        '[\"Passport Copy\", \"Offer Letter\"]'
    ),
)
async def create_visa_type(
    payload:      VisaTypeCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require_manage,
) -> VisaTypeResponse:
    """
    Roles:      app_admin
    Permission: visa_types.manage
    DB:         INSERT INTO visa_types
    Raises:     409 if code already exists
    """
    vt = await service_create_visa_type(db, payload, current_user.user_id)
    item = VisaTypeResponse.model_validate(vt)
    if hasattr(vt, "_active_cases_count"):
        object.__setattr__(item, "active_cases_count", vt._active_cases_count)
    if hasattr(vt, "_processing_time_label"):
        object.__setattr__(item, "processing_time_label", vt._processing_time_label)
    return item


# =============================================================================
# GET /admin/visa-types/{id}
# ─────────────────────────────────────────────────────────────────────────────
# Powers the "View Details" panel / slide-over modal
# =============================================================================
@admin_visa_types_router.get(
    "/admin/visa-types/{visa_type_id}",
    response_model=VisaTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get visa type detail",
    description=(
        "Full visa type detail including required documents list, "
        "active cases count, processing time label, and modifier info. "
        "Powers the View Details panel."
    ),
)
async def get_visa_type(
    visa_type_id: uuid.UUID,
    db:           DBSession,
    _:            Current_User = _require_view,
) -> VisaTypeResponse:
    """
    Roles:      app_admin, hr
    Permission: visa_types.manage | applications.view_all
    DB:         SELECT + active_cases subquery + modified_by join
    Raises:     404 if not found
    """
    vt   = await service_get_visa_type(db, visa_type_id)
    item = VisaTypeResponse.model_validate(vt)
    if hasattr(vt, "_active_cases_count"):
        object.__setattr__(item, "active_cases_count", vt._active_cases_count)
    if hasattr(vt, "_modified_by_name"):
        object.__setattr__(item, "modified_by_name", vt._modified_by_name)
    if hasattr(vt, "_processing_time_label"):
        object.__setattr__(item, "processing_time_label", vt._processing_time_label)
    return item


# =============================================================================
# PATCH /admin/visa-types/{id}/toggle
# ─────────────────────────────────────────────────────────────────────────────
# The Active/Inactive badge toggle on each visa card
# Declared BEFORE the general PATCH /{id} to avoid path collision
# =============================================================================
@admin_visa_types_router.patch(
    "/admin/visa-types/{visa_type_id}/toggle",
    response_model=VisaTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle visa type active/inactive",
    description=(
        "Flips the is_active flag. "
        "Syncs the status field (active ↔ inactive) automatically. "
        "This is the dedicated endpoint for the badge toggle on each card — "
        "keeps the general PATCH endpoint clean."
    ),
)
async def toggle_visa_type(
    visa_type_id: uuid.UUID,
    payload:      VisaTypeToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require_manage,
) -> VisaTypeResponse:
    """
    Roles:      app_admin
    Permission: visa_types.manage
    DB:         UPDATE visa_types SET is_active=?, status=?, modified_by=?
    Raises:     404 if not found
    """
    vt   = await service_toggle_visa_type(
        db, visa_type_id, payload.is_active, current_user.user_id
    )
    item = VisaTypeResponse.model_validate(vt)
    if hasattr(vt, "_active_cases_count"):
        object.__setattr__(item, "active_cases_count", vt._active_cases_count)
    if hasattr(vt, "_processing_time_label"):
        object.__setattr__(item, "processing_time_label", vt._processing_time_label)
    return item


# =============================================================================
# PATCH /admin/visa-types/{id}
# ─────────────────────────────────────────────────────────────────────────────
# Triggered by the "Edit" action on each visa card
# =============================================================================
@admin_visa_types_router.patch(
    "/admin/visa-types/{visa_type_id}",
    response_model=VisaTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a visa type",
    description=(
        "Partial update — only fields included in the request body are written. "
        "`code` is immutable after creation (it's used as FK in user_visa_targets). "
        "Setting `is_active` also updates `status` automatically and vice versa."
    ),
)
async def update_visa_type(
    visa_type_id: uuid.UUID,
    payload:      VisaTypeUpdate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require_manage,
) -> VisaTypeResponse:
    """
    Roles:      app_admin
    Permission: visa_types.manage
    DB:         UPDATE visa_types SET ...
    Raises:     404 if not found
    Note:       code is NOT patchable — it's a FK used in user_visa_targets
    """
    vt   = await service_update_visa_type(db, visa_type_id, payload, current_user.user_id)
    item = VisaTypeResponse.model_validate(vt)
    if hasattr(vt, "_active_cases_count"):
        object.__setattr__(item, "active_cases_count", vt._active_cases_count)
    if hasattr(vt, "_modified_by_name"):
        object.__setattr__(item, "modified_by_name", vt._modified_by_name)
    if hasattr(vt, "_processing_time_label"):
        object.__setattr__(item, "processing_time_label", vt._processing_time_label)
    return item


# =============================================================================
# DELETE /admin/visa-types/{id}
# ─────────────────────────────────────────────────────────────────────────────
# Soft delete — sets is_active=False
# Hard delete blocked if active cases reference this visa type
# =============================================================================
@admin_visa_types_router.delete(
    "/admin/visa-types/{visa_type_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate (soft-delete) a visa type",
    description=(
        "Soft-deletes the visa type by setting is_active=False. "
        "**Blocked** if active cases (not approved/rejected/withdrawn) "
        "are using this visa type. Resolve those cases first."
    ),
)
async def delete_visa_type(
    visa_type_id: uuid.UUID,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require_manage,
) -> dict:
    """
    Roles:      app_admin
    Permission: visa_types.manage
    DB:         UPDATE visa_types SET is_active=False (NOT hard delete)
    Raises:
      404 — not found
      400 — active cases still reference this visa type
    """
    return await service_delete_visa_type(db, visa_type_id, current_user.user_id)
