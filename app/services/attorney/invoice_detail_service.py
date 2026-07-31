"""
invoice_detail_service.py — Service layer for Invoice Detail (Screen 21).

FILE LOCATION
    app/services/attorney/invoice_detail_service.py

All data derived from existing tables — 4 new columns on attorney_invoices only:
  matter, tax_rate_percent, payment_terms, notes_to_client

Functions:
  get_invoice_detail()  → GET  /billing/invoices/{id}/detail
  update_invoice()      → PATCH /billing/invoices/{id}
  add_line_item()       → POST /billing/invoices/{id}/line-items
  delete_line_item()    → DELETE /billing/invoices/{id}/line-items/{lid}

Reused from billing_service.py (NOT duplicated here):
  service_update_invoice_status() → Send Invoice / Save Draft / Void buttons
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.visamodels import (
    AttorneyInvoice,
    BillingClient,
    InvoiceLineItem,
    TimeEntry,
    User,
)
from app.schemas.attorney.invoice_detail import (
    InvoiceAuditSummary,
    InvoiceDetailResponse,
    InvoiceLineItemCreate,
    InvoiceLineItemResponse,
    InvoiceUpdateRequest,
)


# ===========================================================================
# CONSTANTS
# ===========================================================================

_LOCKED_STATUSES = ("paid", "void")   # cannot edit line items or details


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

async def _get_invoice_or_404(
    db:          AsyncSession,
    invoice_id:  uuid.UUID,
    attorney_id: uuid.UUID,
) -> AttorneyInvoice:
    """
    Load AttorneyInvoice with all nested relationships needed for Screen 21.
    Validates ownership — raises 404 if not found or not owned by attorney.
    """
    result = await db.execute(
        select(AttorneyInvoice)
        .options(
            selectinload(AttorneyInvoice.billing_client),
            selectinload(AttorneyInvoice.line_items)
            .selectinload(InvoiceLineItem.time_entry)
            .selectinload(TimeEntry.attorney),
        )
        .where(
            AttorneyInvoice.id          == invoice_id,
            AttorneyInvoice.attorney_id == attorney_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found.",
        )
    return invoice


def _build_line_item_response(item: InvoiceLineItem) -> InvoiceLineItemResponse:
    """
    Builds InvoiceLineItemResponse with derived fields.

    entry_date and timekeeper_initials are derived from the linked TimeEntry:
      entry_date          → TimeEntry.entry_date
      timekeeper_initials → User.first_name[0] + User.last_name[0]
                            e.g. "James Doe" → "JD"

    No extra columns on invoice_line_items needed.
    """
    entry_date          = None
    timekeeper_initials = None

    if item.time_entry:
        entry_date = item.time_entry.entry_date

        attorney = item.time_entry.attorney
        if attorney:
            fn = (attorney.first_name or "")[:1].upper()
            ln = (attorney.last_name  or "")[:1].upper()
            timekeeper_initials = fn + ln if (fn or ln) else None

    return InvoiceLineItemResponse(
        id                  = item.id,
        invoice_id          = item.invoice_id,
        time_entry_id       = item.time_entry_id,
        entry_date          = entry_date,
        description         = item.description,
        quantity            = item.quantity,
        unit_amount_cents   = item.unit_amount_cents,
        total_cents         = item.total_cents,
        timekeeper_initials = timekeeper_initials,
        sort_order          = item.sort_order,
        created_at          = item.created_at,
    )


def _build_audit_summary(
    invoice:        AttorneyInvoice,
    client_balance: int,
) -> InvoiceAuditSummary:
    """
    Computes the Audit Summary right panel card.

    total_hours   = sum of (time_entry.duration_minutes / 60) across all line items
    blended_rate  = (total_cents / 100) / total_hours  [in dollars]
    client_balance = passed in from caller (sum of open/sent/overdue invoices)
    """
    total_minutes = sum(
        item.time_entry.duration_minutes
        for item in invoice.line_items
        if item.time_entry
    )
    total_hours  = round(total_minutes / 60, 1)
    blended_rate = round((invoice.total_cents / 100) / total_hours, 2) if total_hours > 0 else 0.0

    return InvoiceAuditSummary(
        total_hours    = total_hours,
        blended_rate   = blended_rate,
        client_balance = client_balance,
    )


def _recalculate_totals(invoice: AttorneyInvoice) -> None:
    """
    Recomputes subtotal → tax → total after any line item or rate change.
    Called automatically on every mutating operation.
    """
    subtotal = sum(item.total_cents for item in invoice.line_items)
    tax      = math.floor(subtotal * getattr(invoice, "tax_rate_percent", 0) / 100)
    total    = max(0, subtotal + tax - invoice.discount_cents)

    invoice.subtotal_cents = subtotal
    invoice.tax_cents      = tax
    invoice.total_cents    = total


async def _build_response(
    db:      AsyncSession,
    invoice: AttorneyInvoice,
) -> InvoiceDetailResponse:
    """
    Assembles the full InvoiceDetailResponse after any mutation.
    Fetches client balance, builds line items, computes audit summary.
    """
    client = invoice.billing_client

    # Client balance: sum of total_cents for all open/sent/overdue invoices for this client
    bal_result = await db.execute(
        select(func.coalesce(func.sum(AttorneyInvoice.total_cents), 0))
        .where(
            AttorneyInvoice.billing_client_id == invoice.billing_client_id,
            AttorneyInvoice.status.in_(["open", "sent", "overdue"]),
        )
    )
    client_balance = bal_result.scalar() or 0

    line_items    = [
        _build_line_item_response(item)
        for item in sorted(invoice.line_items, key=lambda x: x.sort_order)
    ]
    audit_summary = _build_audit_summary(invoice, client_balance)

    return InvoiceDetailResponse(
        id             = invoice.id,
        invoice_number = invoice.invoice_number,
        status         = invoice.status,

        billing_client_id    = invoice.billing_client_id,
        client_display_name  = client.display_name,
        client_email         = client.billing_email,
        client_billing_name  = getattr(client, "billing_name",  None),
        client_billing_line1 = getattr(client, "billing_line1", None),
        client_billing_line2 = getattr(client, "billing_line2", None),
        client_billing_city  = getattr(client, "billing_city",  None),
        client_billing_state = getattr(client, "billing_state", None),
        client_billing_zip   = getattr(client, "billing_zip",   None),

        issued_date = invoice.issued_date,
        due_date    = invoice.due_date,

        matter           = getattr(invoice, "matter",           None),
        tax_rate_percent = getattr(invoice, "tax_rate_percent", 0),
        payment_terms    = getattr(invoice, "payment_terms",    None),
        notes_to_client  = getattr(invoice, "notes_to_client",  None),

        subtotal_cents = invoice.subtotal_cents,
        tax_cents      = invoice.tax_cents,
        discount_cents = invoice.discount_cents,
        total_cents    = invoice.total_cents,
        currency       = invoice.currency,

        line_items    = line_items,
        audit_summary = audit_summary,

        sent_at    = invoice.sent_at,
        paid_at    = invoice.paid_at,
        voided_at  = invoice.voided_at,
        created_at = invoice.created_at,
        updated_at = invoice.updated_at,
    )


# ===========================================================================
# A. GET INVOICE DETAIL
# ===========================================================================

async def get_invoice_detail(
    db:          AsyncSession,
    invoice_id:  uuid.UUID,
    attorney_id: uuid.UUID,
) -> InvoiceDetailResponse:
    """
    Full invoice detail for Screen 21.
    Loads invoice + line_items + linked TimeEntry + attorney User for each row.
    """
    invoice = await _get_invoice_or_404(db, invoice_id, attorney_id)
    return await _build_response(db, invoice)


# ===========================================================================
# B. UPDATE INVOICE
# ===========================================================================

async def update_invoice(
    db:          AsyncSession,
    invoice_id:  uuid.UUID,
    attorney_id: uuid.UUID,
    payload:     InvoiceUpdateRequest,
) -> InvoiceDetailResponse:
    """
    Partial update — only provided fields are written.
    Blocked if status is 'paid' or 'void'.
    Recalculates totals if tax_rate_percent or discount_cents changes.
    """
    invoice = await _get_invoice_or_404(db, invoice_id, attorney_id)
    now     = datetime.now(timezone.utc)

    if invoice.status in _LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit a '{invoice.status}' invoice.",
        )

    # Apply only provided fields
    if payload.matter           is not None: invoice.matter           = payload.matter
    if payload.issued_date      is not None: invoice.issued_date      = payload.issued_date
    if payload.due_date         is not None: invoice.due_date         = payload.due_date
    if payload.payment_terms    is not None: invoice.payment_terms    = payload.payment_terms
    if payload.notes_to_client  is not None: invoice.notes_to_client  = payload.notes_to_client

    totals_dirty = False
    if payload.tax_rate_percent is not None:
        invoice.tax_rate_percent = payload.tax_rate_percent
        totals_dirty = True
    if payload.discount_cents is not None:
        invoice.discount_cents = payload.discount_cents
        totals_dirty = True

    if totals_dirty:
        _recalculate_totals(invoice)

    invoice.modified_by = attorney_id
    invoice.updated_at  = now

    await db.commit()
    return await _build_response(db, invoice)


# ===========================================================================
# C. ADD LINE ITEM
# ===========================================================================

async def add_line_item(
    db:          AsyncSession,
    invoice_id:  uuid.UUID,
    attorney_id: uuid.UUID,
    payload:     InvoiceLineItemCreate,
) -> InvoiceDetailResponse:
    """
    Adds a row to the Billable Items table.
    Two modes — time entry link or manual flat fee.
    Recalculates invoice totals after adding.
    """
    invoice = await _get_invoice_or_404(db, invoice_id, attorney_id)

    if invoice.status in _LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add line items to a '{invoice.status}' invoice.",
        )

    total_cents        = payload.quantity * payload.unit_amount_cents
    unit_amount_cents  = payload.unit_amount_cents

    # Mode 1: link to an existing unbilled TimeEntry
    if payload.time_entry_id:
        te_result = await db.execute(
            select(TimeEntry).where(
                TimeEntry.id          == payload.time_entry_id,
                TimeEntry.attorney_id == attorney_id,
                TimeEntry.status      == "unbilled",
            )
        )
        te = te_result.scalar_one_or_none()
        if not te:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Time entry not found or is not unbilled.",
            )
        # Use the time entry's own values
        total_cents       = te.amount_cents
        unit_amount_cents = te.hourly_rate_cents

        # Mark time entry as invoiced
        te.status      = "invoiced"
        te.invoice_id  = invoice_id
        te.invoiced_at = datetime.now(timezone.utc)

    new_item = InvoiceLineItem(
        id                = uuid.uuid4(),
        invoice_id        = invoice_id,
        time_entry_id     = payload.time_entry_id,
        description       = payload.description,
        quantity          = payload.quantity,
        unit_amount_cents = unit_amount_cents,
        total_cents       = total_cents,
        sort_order        = payload.sort_order,
        created_by        = attorney_id,
    )
    db.add(new_item)
    await db.flush()

    # Refresh line items list and recalculate
    invoice.line_items.append(new_item)
    _recalculate_totals(invoice)

    invoice.modified_by = attorney_id
    invoice.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    return await _build_response(db, invoice)


# ===========================================================================
# D. DELETE LINE ITEM
# ===========================================================================

async def delete_line_item(
    db:           AsyncSession,
    invoice_id:   uuid.UUID,
    line_item_id: uuid.UUID,
    attorney_id:  uuid.UUID,
) -> InvoiceDetailResponse:
    """
    Removes a row from the Billable Items table.
    Releases linked TimeEntry back to 'unbilled' if applicable.
    Recalculates invoice totals after deleting.
    """
    invoice = await _get_invoice_or_404(db, invoice_id, attorney_id)

    if invoice.status in _LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove line items from a '{invoice.status}' invoice.",
        )

    # Find the line item on this invoice
    item_result = await db.execute(
        select(InvoiceLineItem).where(
            InvoiceLineItem.id         == line_item_id,
            InvoiceLineItem.invoice_id == invoice_id,
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Line item not found on this invoice.",
        )

    # Release linked TimeEntry back to unbilled
    if item.time_entry_id:
        te_result = await db.execute(
            select(TimeEntry).where(TimeEntry.id == item.time_entry_id)
        )
        te = te_result.scalar_one_or_none()
        if te and te.status == "invoiced":
            te.status      = "unbilled"
            te.invoice_id  = None
            te.invoiced_at = None

    await db.delete(item)
    await db.flush()

    # Reload for recalculation
    invoice = await _get_invoice_or_404(db, invoice_id, attorney_id)
    _recalculate_totals(invoice)

    invoice.modified_by = attorney_id
    invoice.updated_at  = datetime.now(timezone.utc)

    await db.commit()
    return await _build_response(db, invoice)
