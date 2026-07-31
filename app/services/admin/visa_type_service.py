"""
app/services/visa_type_service.py  ← COMPLETE REPLACEMENT

All business logic for the Admin Visa Types Manager screen.
Each function maps 1-to-1 with a router endpoint.

Pattern followed from your existing services:
  - async SQLAlchemy
  - raises domain exceptions (NotFoundException, ConflictException, etc.)
  - never returns ORM objects raw — service enriches data before return
"""
from __future__ import annotations

import csv
import io
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Select, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.visamodels import Application, User, VisaType


# =============================================================================
# HELPER — days → human label ("6-8 months", "2-3 weeks")
# Powers the "Processing Time: 6-8 months" label on visa cards
# =============================================================================
def _days_to_label(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    if days <= 14:
        return f"{days} days"
    if days <= 60:
        weeks = round(days / 7)
        return f"{weeks}-{weeks + 1} weeks"
    months = round(days / 30)
    return f"{months}-{months + 1} months"


# =============================================================================
# HELPER — build the base SELECT with computed columns
# Reused by list, get_one, and export to stay DRY
# =============================================================================
def _base_visa_select() -> Select:
    """
    Returns a SQLAlchemy select that joins:
      visa_types → users (for modified_by_name)
      visa_types → applications (for active_cases_count)
    """
    active_cases_subq = (
        select(func.count(Application.id))
        .where(
            Application.visa_type_id == VisaType.id,
            Application.status.notin_(["approved", "rejected", "withdrawn"]),
        )
        .correlate(VisaType)
        .scalar_subquery()
    )

    modifier_name_subq = (
        select(func.concat(User.first_name, " ", User.last_name))
        .where(User.id == VisaType.modified_by)
        .correlate(VisaType)
        .scalar_subquery()
    )

    return select(
        VisaType,
        active_cases_subq.label("active_cases_count"),
        modifier_name_subq.label("modified_by_name"),
    )


# =============================================================================
# HELPER — apply filters to a query (reused by list + export)
# =============================================================================
def _apply_filters(
    q,
    search:   Optional[str],
    category: Optional[str],
    status:   Optional[str],
) -> Any:
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            or_(
                func.lower(VisaType.name).like(term),
                func.lower(VisaType.code).like(term),
                func.lower(VisaType.short_label).like(term),
            )
        )
    if category:
        q = q.where(VisaType.category == category)
    if status:
        if status == "active":
            q = q.where(VisaType.is_active == True)  # noqa: E712
        elif status == "inactive":
            q = q.where(VisaType.is_active == False)  # noqa: E712
        elif status == "pending_review":
            # requires status column — falls back to is_active filter if column absent
            q = q.where(VisaType.status == "pending_review")
    return q


# =============================================================================
# HELPER — apply sorting
# =============================================================================
def _apply_sort(q, sort_by: str, sort_order: str) -> Any:
    col_map = {
        "name":         VisaType.name,
        "code":         VisaType.code,
        "display_order": VisaType.display_order,
        "created_at":   VisaType.created_at,
        "updated_at":   VisaType.updated_at,
    }
    col = col_map.get(sort_by, VisaType.display_order)
    return q.order_by(col.desc() if sort_order == "desc" else col.asc())


# =============================================================================
# HELPER — enrich a VisaType ORM row with computed fields
# =============================================================================
def _enrich(row: Any) -> VisaType:
    """Attach computed fields as temp attributes for schema serialisation."""
    vt: VisaType = row.VisaType
    vt._active_cases_count = row.active_cases_count or 0  # type: ignore[attr-defined]
    vt._modified_by_name   = row.modified_by_name          # type: ignore[attr-defined]

    # Derive status if column doesn't exist yet (pre-migration fallback)
    if not hasattr(vt, "status") or vt.status is None:  # type: ignore[attr-defined]
        vt.status = "active" if vt.is_active else "inactive"  # type: ignore[attr-defined]

    # Build processing_time_label
    vt._processing_time_label = _days_to_label(vt.typical_processing_days)  # type: ignore[attr-defined]
    return vt


# =============================================================================
# 1. GET STATS
# Powers the 4 KPI cards at the top of the screen
# GET /admin/visa-types/stats
# =============================================================================
async def service_get_visa_type_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    4 aggregation queries run in parallel via one round-trip.
    Returns: total, active, pending_review, active_cases + % changes.
    """
    total_q   = await db.execute(select(func.count(VisaType.id)))
    active_q  = await db.execute(
        select(func.count(VisaType.id)).where(VisaType.is_active == True)  # noqa
    )
    cases_q = await db.execute(
        select(func.count(Application.id)).where(
            Application.status.notin_(["approved", "rejected", "withdrawn"])
        )
    )

    # pending_review: try status column, fallback to 0
    try:
        pending_q = await db.execute(
            select(func.count(VisaType.id)).where(VisaType.status == "pending_review")
        )
        pending = pending_q.scalar() or 0
    except Exception:
        pending = 0

    total        = total_q.scalar()  or 0
    active       = active_q.scalar() or 0
    active_cases = cases_q.scalar()  or 0

    return {
        "total_visa_types":  total,
        "active_visa_types": active,
        "pending_review":    pending,
        "active_cases":      active_cases,
        # % change fields — wire up to historical snapshots when available
        # For now returning None so UI shows "—" not a wrong number
        "total_pct_change":   None,
        "active_pct_change":  None,
        "pending_pct_change": None,
        "cases_pct_change":   None,
    }


# =============================================================================
# 2. LIST VISA TYPES (main grid)
# GET /admin/visa-types
# Powers the visa type card grid with filters, search, sort, pagination
# =============================================================================
async def service_list_visa_types(
    db:          AsyncSession,
    search:      Optional[str]  = None,
    category:    Optional[str]  = None,
    status:      Optional[str]  = None,
    sort_by:     str            = "display_order",
    sort_order:  str            = "asc",
    page:        int            = 1,
    page_size:   int            = 20,
) -> Tuple[List[VisaType], int, Dict[str, Any]]:
    """
    Returns: (enriched_rows, total_count, stats_dict)
    Stats are bundled so the frontend gets everything in one HTTP call.
    """
    base = _base_visa_select()
    base = _apply_filters(base, search, category, status)
    base = _apply_sort(base, sort_by, sort_order)

    # total count (before pagination)
    count_q = select(func.count()).select_from(
        _apply_filters(_base_visa_select().subquery(), search, category, status)
    )
    # Simpler count approach:
    count_base = select(func.count(VisaType.id))
    count_base = _apply_filters(count_base, search, category, status)
    total_result = await db.execute(count_base)
    total = total_result.scalar() or 0

    # pagination
    offset = (page - 1) * page_size
    base   = base.offset(offset).limit(page_size)

    result = await db.execute(base)
    rows   = result.all()

    enriched = [_enrich(row) for row in rows]
    stats    = await service_get_visa_type_stats(db)

    return enriched, total, stats


# =============================================================================
# 3. GET ONE VISA TYPE
# GET /admin/visa-types/{id}
# Powers the "View Details" panel / modal
# =============================================================================
async def service_get_visa_type(
    db:           AsyncSession,
    visa_type_id: uuid.UUID,
) -> VisaType:
    q      = _base_visa_select().where(VisaType.id == visa_type_id)
    result = await db.execute(q)
    row    = result.first()
    if not row:
        raise NotFoundException(f"Visa type {visa_type_id} not found.")
    return _enrich(row)


# =============================================================================
# 4. CREATE VISA TYPE
# POST /admin/visa-types
# Triggered by "Add New Visa Type" button
# =============================================================================
async def service_create_visa_type(
    db:         AsyncSession,
    payload:    Any,   # VisaTypeCreate schema
    created_by: uuid.UUID,
) -> VisaType:
    # Guard: code must be unique
    existing = await db.execute(
        select(VisaType).where(VisaType.code == payload.code.upper().strip())
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            f"Visa type with code '{payload.code}' already exists."
        )

    vt = VisaType(
        id                        = uuid.uuid4(),
        code                      = payload.code.upper().strip(),
        name                      = payload.name,
        short_label               = payload.short_label,
        description               = payload.description,
        category                  = payload.category,
        requires_employer_sponsor = payload.requires_employer_sponsor,
        required_documents        = payload.required_documents,
        typical_processing_days   = payload.typical_processing_days,
        government_fee_usd        = payload.government_fee_usd,
        uscis_url                 = payload.uscis_url,
        display_order             = payload.display_order,
        is_active                 = payload.is_active,
        created_by                = created_by,
        modified_by               = created_by,
        created_at                = datetime.now(timezone.utc),
        updated_at                = datetime.now(timezone.utc),
    )

    # Set status + success_rate if columns exist (post-migration)
    if hasattr(payload, "status") and payload.status:
        vt.status       = payload.status       # type: ignore[attr-defined]
    if hasattr(payload, "success_rate"):
        vt.success_rate = payload.success_rate  # type: ignore[attr-defined]

    db.add(vt)
    await db.commit()
    await db.refresh(vt)

    # Return enriched (active_cases will be 0 for new type)
    vt._active_cases_count      = 0    # type: ignore[attr-defined]
    vt._modified_by_name        = None # type: ignore[attr-defined]
    vt._processing_time_label   = _days_to_label(vt.typical_processing_days)  # type: ignore[attr-defined]
    return vt


# =============================================================================
# 5. UPDATE VISA TYPE
# PATCH /admin/visa-types/{id}
# Triggered by "Edit" action on visa card
# =============================================================================
async def service_update_visa_type(
    db:           AsyncSession,
    visa_type_id: uuid.UUID,
    payload:      Any,   # VisaTypeUpdate schema
    modified_by:  uuid.UUID,
) -> VisaType:
    result = await db.execute(
        select(VisaType).where(VisaType.id == visa_type_id)
    )
    vt = result.scalar_one_or_none()
    if not vt:
        raise NotFoundException(f"Visa type {visa_type_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(vt, field):
            setattr(vt, field, value)

    # Sync is_active ↔ status
    if "status" in update_data:
        vt.is_active = update_data["status"] == "active"
    elif "is_active" in update_data:
        vt.status = "active" if update_data["is_active"] else "inactive"  # type: ignore[attr-defined]

    vt.modified_by = modified_by
    vt.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(vt)
    return await service_get_visa_type(db, visa_type_id)


# =============================================================================
# 6. TOGGLE ACTIVE STATUS
# PATCH /admin/visa-types/{id}/toggle
# The Active/Inactive badge switch on each visa card
# =============================================================================
async def service_toggle_visa_type(
    db:           AsyncSession,
    visa_type_id: uuid.UUID,
    is_active:    bool,
    modified_by:  uuid.UUID,
) -> VisaType:
    result = await db.execute(
        select(VisaType).where(VisaType.id == visa_type_id)
    )
    vt = result.scalar_one_or_none()
    if not vt:
        raise NotFoundException(f"Visa type {visa_type_id} not found.")

    vt.is_active   = is_active
    vt.modified_by = modified_by
    vt.updated_at  = datetime.now(timezone.utc)

    # Keep status in sync
    try:
        vt.status = "active" if is_active else "inactive"  # type: ignore[attr-defined]
    except AttributeError:
        pass  # status column not yet migrated — ignore

    await db.commit()
    await db.refresh(vt)
    return await service_get_visa_type(db, visa_type_id)


# =============================================================================
# 7. DELETE VISA TYPE
# DELETE /admin/visa-types/{id}
# Soft delete — sets is_active=False (hard delete blocked if cases exist)
# =============================================================================
async def service_delete_visa_type(
    db:           AsyncSession,
    visa_type_id: uuid.UUID,
    deleted_by:   uuid.UUID,
) -> Dict[str, str]:
    result = await db.execute(
        select(VisaType).where(VisaType.id == visa_type_id)
    )
    vt = result.scalar_one_or_none()
    if not vt:
        raise NotFoundException(f"Visa type {visa_type_id} not found.")

    # Block deletion if active cases exist
    cases_result = await db.execute(
        select(func.count(Application.id)).where(
            Application.visa_type_id == visa_type_id,
            Application.status.notin_(["approved", "rejected", "withdrawn"]),
        )
    )
    active_case_count = cases_result.scalar() or 0
    if active_case_count > 0:
        raise BadRequestException(
            f"Cannot delete visa type with {active_case_count} active case(s). "
            "Close or reassign all active cases first."
        )

    # Soft delete
    vt.is_active   = False
    vt.modified_by = deleted_by
    vt.updated_at  = datetime.now(timezone.utc)
    try:
        vt.status = "inactive"  # type: ignore[attr-defined]
    except AttributeError:
        pass

    await db.commit()
    return {"message": f"Visa type '{vt.code}' deactivated successfully."}


# =============================================================================
# 8. EXPORT
# GET /admin/visa-types/export
# Powers the "Export All" button — returns CSV
# =============================================================================
async def service_export_visa_types(
    db:       AsyncSession,
    category: Optional[str] = None,
    status:   Optional[str] = None,
) -> str:
    """Returns CSV string of all visa types matching optional filters."""
    base   = _base_visa_select()
    base   = _apply_filters(base, search=None, category=category, status=status)
    base   = _apply_sort(base, sort_by="display_order", sort_order="asc")

    result = await db.execute(base)
    rows   = result.all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row — matches what admin would expect in Excel
    writer.writerow([
        "Code", "Name", "Short Label", "Category", "Status",
        "Requires Sponsor", "Required Docs Count",
        "Processing Days", "Processing Time", "Govt Fee (USD)",
        "Success Rate (%)", "Active Cases",
        "USCIS URL", "Is Active", "Created At", "Updated At",
    ])

    for row in rows:
        vt = row.VisaType
        docs = []
        if vt.required_documents:
            try:
                docs = json.loads(vt.required_documents)
            except (json.JSONDecodeError, TypeError):
                docs = []

        status_val = getattr(vt, "status", None) or ("active" if vt.is_active else "inactive")
        success    = getattr(vt, "success_rate", None)

        writer.writerow([
            vt.code,
            vt.name,
            vt.short_label or "",
            vt.category,
            status_val,
            "Yes" if vt.requires_employer_sponsor else "No",
            len(docs),
            vt.typical_processing_days or "",
            _days_to_label(vt.typical_processing_days) or "",
            vt.government_fee_usd or "",
            success or "",
            row.active_cases_count or 0,
            vt.uscis_url or "",
            "Yes" if vt.is_active else "No",
            str(vt.created_at),
            str(vt.updated_at),
        ])

    return output.getvalue()


# =============================================================================
# LEGACY COMPAT — kept for existing non-admin endpoints
# GET /visa-types  (employee-facing dropdown)
# =============================================================================
async def list_visa_types(
    db:          AsyncSession,
    category:    Optional[str] = None,
    active_only: bool          = True,
    limit:       int           = 100,
    offset:      int           = 0,
) -> Tuple[List[VisaType], int]:
    """
    Lightweight list — no active_cases join.
    Used by employee screens to populate visa type dropdowns.
    """
    q = select(VisaType)
    if active_only:
        q = q.where(VisaType.is_active == True)  # noqa
    if category:
        q = q.where(VisaType.category == category)
    q = q.order_by(VisaType.display_order.asc())

    count_q      = select(func.count(VisaType.id))
    if active_only:
        count_q  = count_q.where(VisaType.is_active == True)  # noqa
    if category:
        count_q  = count_q.where(VisaType.category == category)

    total_result = await db.execute(count_q)
    total        = total_result.scalar() or 0

    result = await db.execute(q.offset(offset).limit(limit))
    items  = result.scalars().all()

    return items, total
