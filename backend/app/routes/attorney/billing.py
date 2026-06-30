"""
app/routers/billing.py

Router for Screen 19 — Billing & Time Tracking Dashboard.
One router file for one screen. Mirrors subscription router style exactly.

All endpoints grouped by section:
  ── DASHBOARD         GET  /billing/dashboard/stats
  ── BILLING CLIENTS   GET/POST /billing/clients
  ── TIME ENTRIES      GET/POST/PATCH/DELETE /billing/time-entries
  ── INVOICES          GET/POST/PATCH /billing/invoices

Registration in main.py:
    from app.routers.billing import router as billing_router
    app.include_router(billing_router)
"""
from __future__ import annotations

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.visamodels import User
from app.schemas.attorney.billing import (
    AttorneyInvoiceListResponse,
    AttorneyInvoiceResponse,
    BillingClientCreate,
    BillingClientListResponse,
    BillingClientResponse,
    BillingDashboardStats,
    BulkActionRequest,
    BulkActionResponse,
    InvoiceCreate,
    InvoiceDraftFromEntries,
    InvoiceStatusUpdateRequest,
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
    TopClientsToBillResponse,
)
from app.services.attorney.billing_service import (
    service_bulk_action,
    service_create_billing_client,
    service_create_invoice,
    service_create_time_entry,
    service_delete_time_entry,
    service_draft_from_entries,
    service_get_billing_client,
    service_get_dashboard_stats,
    service_get_invoice,
    service_get_time_entry,
    service_get_top_unbilled_clients,
    service_list_billing_clients,
    service_list_invoices,
    service_list_time_entries,
    service_update_invoice_status,
    service_update_time_entry,
)

billing_router = APIRouter(tags=["Billing & Time Tracking"])


# =============================================================================
# ── DASHBOARD ─────────────────────────────────────────────────────────────────
# =============================================================================

@billing_router.get(
    "/dashboard/stats",
    response_model=BillingDashboardStats,
    summary="Billing KPI Dashboard",
    description=(
        "Returns all 4 KPI cards: This Month Revenue, Billable Hours, "
        "Outstanding Invoices, Active Clients. "
        "Use ?period=this_month|last_month|ytd to switch the period toggle."
    ),
)
async def get_dashboard_stats(
    period:       str          = Query("this_month",
                                       pattern="^(this_month|last_month|ytd)$"),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("billing:dashboard")),
):
    try:
        return await service_get_dashboard_stats(db, current_user.user_id, period)
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# =============================================================================
# ── BILLING CLIENTS ───────────────────────────────────────────────────────────
# =============================================================================

@billing_router.get(
    "/clients/top-unbilled",
    response_model=TopClientsToBillResponse,
    summary="Top Clients to Bill",
    description="Right sidebar panel — clients ranked by highest unbilled amount.",
)
async def get_top_unbilled_clients(
    limit:        int          = Query(10, ge=1, le=50),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("billing:dashboard")),
):
    return await service_get_top_unbilled_clients(db, current_user.user_id, limit)


@billing_router.get(
    "/clients",
    response_model=BillingClientListResponse,
    summary="List Billing Clients",
)
async def list_billing_clients(
    search:      Optional[str]  = Query(None),
    client_type: Optional[str]  = Query(None, pattern="^(corporate|individual)$"),
    is_active:   Optional[bool] = Query(True),
    sort_by:     str            = Query("display_name",
                                        pattern="^(display_name|unbilled_amount|created_at)$"),
    sort_order:  str            = Query("asc", pattern="^(asc|desc)$"),
    page:        int            = Query(1,  ge=1),
    page_size:   int            = Query(20, ge=1, le=100),
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(get_current_user),
    #_perm:        None          = Depends(require_permission("billing_clients:read")),
):
    items, total = await service_list_billing_clients(
        db, search=search, client_type=client_type, is_active=is_active,
        sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
    )
    return BillingClientListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@billing_router.get(
    "/clients/{client_id}",
    response_model=BillingClientResponse,
    summary="Get Billing Client",
)
async def get_billing_client(
    client_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("billing_clients:read")),
):
    try:
        return await service_get_billing_client(db, client_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@billing_router.post(
    "/clients",
    response_model=BillingClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Billing Client",
)
async def create_billing_client(
    payload:      BillingClientCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("billing_clients:manage")),
):
    try:
        return await service_create_billing_client(db, payload, current_user.user_id)
    except ConflictException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# =============================================================================
# ── TIME ENTRIES ──────────────────────────────────────────────────────────────
# NOTE: /time-entries/bulk-action declared BEFORE /{entry_id} to avoid conflict
# =============================================================================

@billing_router.post(
    "/time-entries/bulk-action",
    response_model=BulkActionResponse,
    summary="Bulk Action on Time Entries",
    description=(
        "Bottom action bar: add_to_invoice (requires invoice_id), "
        "mark_billed, or delete. Only 'unbilled' entries are affected; "
        "others are skipped and counted in skipped_count."
    ),
)
async def bulk_action_time_entries(
    payload:      BulkActionRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:bulk_action")),
):
    try:
        return await service_bulk_action(db, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@billing_router.get(
    "/time-entries",
    response_model=TimeEntryListResponse,
    summary="List Time Entries",
    description=(
        "Recent Time Entries table. "
        "Supports search (description, client, case number), "
        "status/client/application/billable/date filters, sorting, pagination."
    ),
)
async def list_time_entries(
    search:            Optional[str]       = Query(None),
    status:            Optional[str]       = Query(None,
                                                    pattern="^(unbilled|invoiced|paid|written_off)$"),
    billing_client_id: Optional[uuid.UUID] = Query(None),
    application_id:    Optional[uuid.UUID] = Query(None),
    is_billable:       Optional[bool]      = Query(None),
    date_from:         Optional[str]       = Query(None, description="YYYY-MM-DD"),
    date_to:           Optional[str]       = Query(None, description="YYYY-MM-DD"),
    sort_by:           str                 = Query("entry_date",
                                                    pattern="^(entry_date|amount|duration|client|status|created_at)$"),
    sort_order:        str                 = Query("desc", pattern="^(asc|desc)$"),
    page:              int                 = Query(1,  ge=1),
    page_size:         int                 = Query(20, ge=1, le=100),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:read")),
):
    items, total = await service_list_time_entries(
        db, attorney_id=current_user.user_id, search=search, status=status,
        billing_client_id=billing_client_id, application_id=application_id,
        is_billable=is_billable, date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
    )
    return TimeEntryListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@billing_router.get(
    "/time-entries/{entry_id}",
    response_model=TimeEntryResponse,
    summary="Get Time Entry",
)
async def get_time_entry(
    entry_id:     uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:read")),
):
    try:
        return await service_get_time_entry(db, entry_id, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@billing_router.post(
    "/time-entries",
    response_model=TimeEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log Time",
    description=(
        "Log Time modal. Hourly rate resolved automatically: "
        "client override → attorney default. "
        "amount = math.ceil(duration_minutes / 60 × rate)."
    ),
)
async def create_time_entry(
    payload:      TimeEntryCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:create")),
):
    try:
        return await service_create_time_entry(db, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@billing_router.patch(
    "/time-entries/{entry_id}",
    response_model=TimeEntryResponse,
    summary="Update Time Entry",
    description="Only 'unbilled' entries can be edited. Void the invoice first to unlock.",
)
async def update_time_entry(
    entry_id:     uuid.UUID,
    payload:      TimeEntryUpdate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:update")),
):
    try:
        return await service_update_time_entry(db, entry_id, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@billing_router.delete(
    "/time-entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Time Entry",
    description="Only 'unbilled' entries can be deleted.",
)
async def delete_time_entry(
    entry_id:     uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("time_entries:delete")),
):
    try:
        await service_delete_time_entry(db, entry_id, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# =============================================================================
# ── INVOICES ──────────────────────────────────────────────────────────────────
# NOTE: /invoices/draft declared BEFORE /{invoice_id} to avoid conflict
# =============================================================================

@billing_router.post(
    "/invoices/draft",
    response_model=AttorneyInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Draft Invoice from Time Entries",
    description=(
        "Draft Invoice button on Top Clients panel. "
        "Creates a draft invoice and attaches the selected unbilled time entries. "
        "All entries must belong to the specified billing_client_id."
    ),
)
async def draft_invoice_from_entries(
    payload:      InvoiceDraftFromEntries,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("invoices:create")),
):
    try:
        return await service_draft_from_entries(db, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@billing_router.get(
    "/invoices",
    response_model=AttorneyInvoiceListResponse,
    summary="List Invoices",
)
async def list_invoices(
    search:            Optional[str]       = Query(None),
    status:            Optional[str]       = Query(None,
                                                    pattern="^(draft|open|sent|paid|overdue|void)$"),
    billing_client_id: Optional[uuid.UUID] = Query(None),
    date_from:         Optional[str]       = Query(None, description="YYYY-MM-DD"),
    date_to:           Optional[str]       = Query(None, description="YYYY-MM-DD"),
    sort_by:           str                 = Query("created_at",
                                                    pattern="^(created_at|total|due_date|status|client|invoice_number)$"),
    sort_order:        str                 = Query("desc", pattern="^(asc|desc)$"),
    page:              int                 = Query(1,  ge=1),
    page_size:         int                 = Query(20, ge=1, le=100),
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("invoices:read")),
):
    items, total = await service_list_invoices(
        db, attorney_id=current_user.user_id, search=search, status=status,
        billing_client_id=billing_client_id, date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size,
    )
    return AttorneyInvoiceListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@billing_router.get(
    "/invoices/{invoice_id}",
    response_model=AttorneyInvoiceResponse,
    summary="Get Invoice Detail",
    description="Full invoice with all line items.",
)
async def get_invoice(
    invoice_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("invoices:read")),
):
    try:
        return await service_get_invoice(db, invoice_id, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@billing_router.post(
    "/invoices",
    response_model=AttorneyInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Invoice",
    description="New Invoice button — manual creation with optional line items.",
)
async def create_invoice(
    payload:      InvoiceCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    #_perm:        None         = Depends(require_permission("invoices:create")),
):
    try:
        return await service_create_invoice(db, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@billing_router.patch(
    "/invoices/{invoice_id}/status",
    response_model=AttorneyInvoiceResponse,
    summary="Update Invoice Status",
    description=(
        "State machine transitions: draft→open, open→sent|void, "
        "sent→paid|void, overdue→paid|void. "
        "Voiding releases time entries back to 'unbilled'. "
        "Marking paid transitions linked entries to 'paid'."
    ),
)
async def update_invoice_status(
    invoice_id:   uuid.UUID,
    payload:      InvoiceStatusUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    # _perm:        None         = Depends(require_permission("invoices:update")),
):
    try:
        return await service_update_invoice_status(db, invoice_id, payload, current_user.user_id)
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BadRequestException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
