"""
invoice_detail_router.py — V1 API routes for Invoice Detail (Screen 21).

FILE LOCATION
    app/routes/attorney/invoice_detail.py

Route map (4 endpoints):

  GET    /billing/invoices/{invoice_id}/detail                    → Full invoice detail
  PATCH  /billing/invoices/{invoice_id}                           → Edit details / tax / settings
  POST   /billing/invoices/{invoice_id}/line-items                → Add line item
  DELETE /billing/invoices/{invoice_id}/line-items/{line_item_id} → Remove line item

All endpoints:
  • Require JWT (get_current_user)
  • Scoped to the authenticated attorney's own invoices
  • Use existing permissions: invoices:read, invoices:update

Existing endpoints reused AS-IS from billing_router (NOT duplicated here):
  PATCH  /billing/invoices/{invoice_id}/status  → Send Invoice / Save Draft / Void
  GET    /billing/invoices                       → Back to Invoices list
  POST   /billing/invoices                       → New Invoice button
  POST   /billing/time-entries                   → Log Time button

Register in main.py BEFORE billing_router:
  from app.routes.attorney.invoice_detail import invoice_detail_router
  app.include_router(invoice_detail_router, prefix="/api/v1/billing",
                     tags=["Screen 21 - Invoice Detail"])
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.visamodels import User
from app.services.attorney import invoice_detail_service
from app.schemas.attorney.invoice_detail import (
    InvoiceDetailResponse,
    InvoiceLineItemCreate,
    InvoiceUpdateRequest,
)

invoice_detail_router = APIRouter()


# ===========================================================================
# A. INVOICE DETAIL — full load
# ===========================================================================

@invoice_detail_router.get(
    "/invoices/{invoice_id}/detail",
    response_model=InvoiceDetailResponse,
    summary="Get full invoice detail — Screen 21",
)
async def get_invoice_detail(
    invoice_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _perm:        None         = Depends(require_permission("invoices:read")),
):
    """
    Screen 21 — called when attorney opens an invoice.

    Returns:
    - Invoice header: number, status, client name + address, issue date,
      due date, matter
    - Billable Items table: each row has date, description, hours,
      rate, amount, timekeeper initials (all derived — no extra columns)
    - Subtotal, tax_rate_percent, tax_cents, discount_cents, total_cents
    - Actions panel metadata: sent_at, paid_at, voided_at
    - Audit Summary: total_hours, blended_rate, client_balance
    - Settings: payment_terms, notes_to_client
    """
    return await invoice_detail_service.get_invoice_detail(
        db, invoice_id, current_user.user_id
    )


# ===========================================================================
# B. EDIT INVOICE — details, tax, discount, settings
# ===========================================================================

@invoice_detail_router.patch(
    "/invoices/{invoice_id}",
    response_model=InvoiceDetailResponse,
    summary="Edit invoice details — Screen 21",
)
async def update_invoice(
    invoice_id:   uuid.UUID,
    payload:      InvoiceUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _perm:        None         = Depends(require_permission("invoices:update")),
):
    """
    Screen 21 — partial update, only provided fields are written.

    Powers four UI elements:
    - Edit Details button     → matter, issued_date, due_date
    - Tax % input field       → tax_rate_percent (auto-recalculates tax_cents + total)
    - Discount input field    → discount_cents (auto-recalculates total)
    - Settings panel          → payment_terms, notes_to_client

    Blocked if invoice status is 'paid' or 'void'.
    Always returns the full updated InvoiceDetailResponse.
    """
    return await invoice_detail_service.update_invoice(
        db, invoice_id, current_user.user_id, payload
    )


# ===========================================================================
# C. ADD LINE ITEM — "+ Add Line Item" button
# ===========================================================================

@invoice_detail_router.post(
    "/invoices/{invoice_id}/line-items",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a billable line item — Screen 21 '+ Add Line Item'",
)
async def add_line_item(
    invoice_id:   uuid.UUID,
    payload:      InvoiceLineItemCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
    _perm:        None         = Depends(require_permission("invoices:update")),
):
    """
    Screen 21 — adds a new row to the Billable Items table.

    Two modes:
    - time_entry_id provided  → links an existing unbilled TimeEntry.
      Rate and duration are copied from it. TimeEntry status → 'invoiced'.
    - time_entry_id = null    → manual flat-fee line.
      Use unit_amount_cents for the flat amount, quantity = 1.

    Invoice subtotal, tax, and total are recalculated automatically.
    Blocked if invoice is 'paid' or 'void'.
    Returns the full updated InvoiceDetailResponse.
    """
    return await invoice_detail_service.add_line_item(
        db, invoice_id, current_user.user_id, payload
    )


# ===========================================================================
# D. REMOVE LINE ITEM — trash icon on each row
# ===========================================================================

@invoice_detail_router.delete(
    "/invoices/{invoice_id}/line-items/{line_item_id}",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a billable line item — Screen 21 row delete",
)
async def delete_line_item(
    invoice_id:    uuid.UUID,
    line_item_id:  uuid.UUID,
    db:            AsyncSession = Depends(get_db),
    current_user:  User         = Depends(get_current_user),
    _perm:         None         = Depends(require_permission("invoices:update")),
):
    """
    Screen 21 — removes a row from the Billable Items table.

    If the row was linked to a TimeEntry, that entry is released back to
    'unbilled' so it can be added to a different invoice.
    Invoice subtotal, tax, and total are recalculated automatically.
    Blocked if invoice is 'paid' or 'void'.
    Returns the full updated InvoiceDetailResponse.
    """
    return await invoice_detail_service.delete_line_item(
        db, invoice_id, line_item_id, current_user.user_id
    )
