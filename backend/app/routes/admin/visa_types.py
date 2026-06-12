"""
app/routes/visa_types.py  ← CORRECTED VERSION
Matches visamodels.py exactly. All admin + employee endpoints.

ENDPOINTS
    GET    /visa-types                     Employee dropdown (no admin required)
    GET    /admin/visa-types               Admin card grid + KPI stats
    GET    /admin/visa-types/stats         KPI cards only (lightweight refresh)
    GET    /admin/visa-types/export        Export All button → CSV download
    GET    /admin/visa-types/{id}          View Details panel
    POST   /admin/visa-types               Add New Visa Type button
    PATCH  /admin/visa-types/{id}/toggle   Active/Inactive badge toggle
    PATCH  /admin/visa-types/{id}          Edit visa type
    DELETE /admin/visa-types/{id}          Soft delete
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse
import io

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.visa_type import (
    VisaTypeCreate,
    VisaTypeExportRow,
    VisaTypeListResponse,
    VisaTypeResponse,
    VisaTypeStats,
    VisaTypeToggle,
    VisaTypeUpdate,
)
from app.services.visa_type_service import (
    list_visa_types,
    service_create_visa_type,
    service_delete_visa_type,
    service_export_visa_types,
    service_get_visa_type,
    service_get_visa_type_stats,
    service_list_visa_types,
    service_toggle_visa_type,
    service_update_visa_type,
)

visa_type_router = APIRouter()
_require = PermissionChecker("visa_types.manage")


# =============================================================================
# GET /visa-types — Employee-facing dropdown (no admin required)
# Used by application forms to populate visa type selector
# =============================================================================
@visa_type_router.get(
    "/visa-types",
    status_code=status.HTTP_200_OK,
    summary="List visa types for employee dropdowns",
    description="Returns active visa types for form dropdowns. No admin required.",
)
async def list_visa_types_endpoint(
    db:           DBSession,
    current_user: Current_User,
    category:     Optional[str] = Query(None,
                                        description="employment|student|visitor|"
                                                    "permanent_resident|exchange"),
    active_only:  bool = Query(True,  description="Return only active visa types"),
    limit:        int  = Query(100,   ge=1, le=500),
    offset:       int  = Query(0,     ge=0),
) -> dict:
    items, total = await list_visa_types(
        db, category=category, active_only=active_only, limit=limit, offset=offset,
    )
    return {
        "items": [VisaTypeResponse.model_validate(r) for r in items],
        "total": total,
    }


# =============================================================================
# GET /admin/visa-types/stats — KPI cards (lightweight, poll-friendly)
# MUST be before /admin/visa-types/{id} to avoid path collision
# =============================================================================
@visa_type_router.get(
    "/admin/visa-types/stats",
    status_code=status.HTTP_200_OK,
    summary="Visa type KPI stats — 4 stat cards",
    description="Total, Active, Pending Review, Active Cases counts for KPI cards.",
)
async def get_visa_type_stats(
    db: DBSession,
    _:  Current_User = _require,
) -> VisaTypeStats:
    stats = await service_get_visa_type_stats(db)
    return VisaTypeStats(**stats)


# =============================================================================
# GET /admin/visa-types/export — Export All button → CSV download
# MUST be before /admin/visa-types/{id}
# =============================================================================
@visa_type_router.get(
    "/admin/visa-types/export",
    status_code=status.HTTP_200_OK,
    summary="Export all visa types as CSV",
    description="Powers the 'Export All' button. Returns CSV file download.",
)
async def export_visa_types(
    db:       DBSession,
    _:        Current_User = _require,
    category: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
):
    csv_content = await service_export_visa_types(db, category=category, status=status)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=visa_types.csv"},
    )


# =============================================================================
# GET /admin/visa-types — Main card grid + KPI stats in one call
# =============================================================================
@visa_type_router.get(
    "/admin/visa-types",
    status_code=status.HTTP_200_OK,
    summary="Admin visa types card grid with filters, search, sort, pagination",
    description=(
        "Returns KPI stats + paginated visa type cards in one call. "
        "No waterfall — frontend gets everything it needs."
    ),
)
async def list_admin_visa_types(
    db:         DBSession,
    _:          Current_User = _require,
    search:     Optional[str] = Query(None, min_length=1,
                                      description="Search by name or code"),
    category:   Optional[str] = Query(None,
                                      description="employment|student|visitor|"
                                                  "permanent_resident|exchange"),
    status:     Optional[str] = Query(None,
                                      description="active|inactive|pending_review"),
    sort_by:    str            = Query("display_order",
                                      description="name|code|display_order|"
                                                  "created_at|updated_at"),
    sort_order: str            = Query("asc", description="asc|desc"),
    page:       int            = Query(1,  ge=1),
    page_size:  int            = Query(20, ge=1, le=100),
) -> VisaTypeListResponse:
    items, total, stats = await service_list_visa_types(
        db=db, search=search, category=category,
        status=status, sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size))   # ceiling division
    return VisaTypeListResponse(
        stats=VisaTypeStats(**stats),
        items=[VisaTypeResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# GET /admin/visa-types/{id} — View Details panel / modal
# =============================================================================
@visa_type_router.get(
    "/admin/visa-types/{visa_type_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a single visa type by ID",
)
async def get_visa_type(
    visa_type_id: uuid.UUID,
    db:           DBSession,
    _:            Current_User = _require,
) -> VisaTypeResponse:
    vt = await service_get_visa_type(db, visa_type_id)
    return VisaTypeResponse.model_validate(vt)


# =============================================================================
# POST /admin/visa-types — "Add New Visa Type" button
# =============================================================================
@visa_type_router.post(
    "/admin/visa-types",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new visa type",
)
async def create_visa_type(
    payload:      VisaTypeCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> VisaTypeResponse:
    vt = await service_create_visa_type(
        db=db, payload=payload, created_by=current_user.user_id
    )
    return VisaTypeResponse.model_validate(vt)


# =============================================================================
# PATCH /admin/visa-types/{id}/toggle — Active/Inactive badge toggle
# MUST be declared BEFORE /{id} PATCH to avoid path collision
# =============================================================================
@visa_type_router.patch(
    "/admin/visa-types/{visa_type_id}/toggle",
    status_code=status.HTTP_200_OK,
    summary="Toggle visa type active/inactive",
    description="The Active/Inactive badge switch on each visa card.",
)
async def toggle_visa_type(
    visa_type_id: uuid.UUID,
    payload:      VisaTypeToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> VisaTypeResponse:
    vt = await service_toggle_visa_type(
        db=db, visa_type_id=visa_type_id,
        is_active=payload.is_active, modified_by=current_user.user_id,
    )
    return VisaTypeResponse.model_validate(vt)


# =============================================================================
# PATCH /admin/visa-types/{id} — Edit visa type content
# =============================================================================
@visa_type_router.patch(
    "/admin/visa-types/{visa_type_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a visa type",
    description="Edit name, description, processing time, fees, documents, etc.",
)
async def update_visa_type(
    visa_type_id: uuid.UUID,
    payload:      VisaTypeUpdate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> VisaTypeResponse:
    vt = await service_update_visa_type(
        db=db, visa_type_id=visa_type_id,
        payload=payload, modified_by=current_user.user_id,
    )
    return VisaTypeResponse.model_validate(vt)


# =============================================================================
# DELETE /admin/visa-types/{id} — Soft delete
# Blocked if active cases exist — returns 400 with count
# =============================================================================
@visa_type_router.delete(
    "/admin/visa-types/{visa_type_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate (soft-delete) a visa type",
    description=(
        "Sets is_active=False. Blocked if active cases exist. "
        "Hard delete not supported — data integrity must be preserved."
    ),
)
async def delete_visa_type(
    visa_type_id: uuid.UUID,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _require,
) -> dict:
    return await service_delete_visa_type(
        db=db, visa_type_id=visa_type_id, deleted_by=current_user.user_id,
    )
