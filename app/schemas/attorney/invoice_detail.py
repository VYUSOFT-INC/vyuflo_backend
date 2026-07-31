"""
invoice_detail_schema.py — Pydantic schemas for Invoice Detail (Screen 21).

FILE LOCATION
    app/schemas/attorney/invoice_detail.py

Covers all sections of Screen 21:
  Invoice Header  •  Billable Items Table  •  Totals
  Actions Panel   •  Audit Summary         •  Settings Panel

Existing schemas in app/schemas/attorney/billing.py are NOT redefined:
  InvoiceStatusUpdateRequest  → reused for Send Invoice / Save Draft / Void
  AttorneyInvoiceResponse     → reused for the invoices list screen
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# BILLABLE ITEMS TABLE — one row per line item
# ===========================================================================

class InvoiceLineItemResponse(BaseModel):
    """
    One row in the Billable Items table.

    entry_date and timekeeper_initials are DERIVED at query time:
      entry_date          → InvoiceLineItem.time_entry → TimeEntry.entry_date
      timekeeper_initials → TimeEntry.attorney → User.first_name[0]+last_name[0]
    No extra columns on invoice_line_items needed.
    """
    model_config = ConfigDict(from_attributes=True)

    id:            uuid.UUID
    invoice_id:    uuid.UUID
    time_entry_id: Optional[uuid.UUID] = None

    entry_date:          Optional[date] = None   # "Oct 20, 2023"
    description:         str                     # "Initial Consultation & Strategy"
    quantity:            int                     # duration_minutes for time entries, 1 for flat fee
    unit_amount_cents:   int                     # hourly rate in cents → shown as "$350"
    total_cents:         int                     # shown as "$525.00"
    timekeeper_initials: Optional[str] = None    # "JD" — attorney initials

    sort_order: int
    created_at: datetime


class InvoiceLineItemCreate(BaseModel):
    """POST /billing/invoices/{invoice_id}/line-items — '+ Add Line Item' button."""

    description:       str
    quantity:          int = 1
    unit_amount_cents: int            # flat fee amount in cents; ignored if time_entry_id provided
    sort_order:        int = 0

    # Optional: link to an existing unbilled TimeEntry instead of a manual line
    time_entry_id: Optional[uuid.UUID] = None


# ===========================================================================
# AUDIT SUMMARY — right panel card
# ===========================================================================

class InvoiceAuditSummary(BaseModel):
    """
    Audit Summary card on the right panel of Screen 21.
    All values computed at query time — not stored.
    """
    total_hours:    float = Field(..., description="Sum of all linked time entry minutes / 60")
    blended_rate:   float = Field(..., description="total_due / total_hours in dollars, e.g. 308.33")
    client_balance: int   = Field(..., description="Sum of all open/sent/overdue invoices for this client in cents")


# ===========================================================================
# FULL INVOICE DETAIL RESPONSE
# ===========================================================================

class InvoiceDetailResponse(BaseModel):
    """
    GET /billing/invoices/{invoice_id}/detail — full Screen 21 payload.
    Superset of AttorneyInvoiceResponse — includes line items + audit summary.
    """
    model_config = ConfigDict(from_attributes=True)

    # ── Invoice header ────────────────────────────────────────────────────────
    id:             uuid.UUID
    invoice_number: str   = Field(..., examples=["INV-2023-104"])
    status:         str   = Field(..., examples=["draft"])   # draft|open|sent|paid|overdue|void

    # ── Client block (from BillingClient) ────────────────────────────────────
    billing_client_id:    uuid.UUID
    client_display_name:  str              # "TechCorp Solutions"
    client_email:         Optional[str] = None
    client_billing_name:  Optional[str] = None   # address line shown under client name
    client_billing_line1: Optional[str] = None   # "123 Innovation Drive, Suite 400"
    client_billing_line2: Optional[str] = None
    client_billing_city:  Optional[str] = None   # "San Francisco"
    client_billing_state: Optional[str] = None   # "CA"
    client_billing_zip:   Optional[str] = None   # "94105"

    # ── Dates ─────────────────────────────────────────────────────────────────
    issued_date: Optional[date] = None   # "Oct 25, 2023"
    due_date:    Optional[date] = None   # "Nov 24, 2023"

    # ── New Screen 21 fields (4 new columns on attorney_invoices) ─────────────
    matter:           Optional[str] = None   # "H-1B Applications"
    tax_rate_percent: int           = 0      # editable tax % field; 0 = no tax
    payment_terms:    Optional[str] = None   # Settings panel — "Net 30"
    notes_to_client:  Optional[str] = None   # Settings panel — "Thank you for your business."

    # ── Totals ────────────────────────────────────────────────────────────────
    subtotal_cents: int   # sum of all line items
    tax_cents:      int   # subtotal × tax_rate_percent / 100
    discount_cents: int   # editable discount field
    total_cents:    int   # subtotal + tax - discount
    currency:       str = "USD"

    # ── Billable Items table ──────────────────────────────────────────────────
    line_items: List[InvoiceLineItemResponse] = []

    # ── Audit Summary (right panel) ───────────────────────────────────────────
    audit_summary: Optional[InvoiceAuditSummary] = None

    # ── Action state timestamps ───────────────────────────────────────────────
    sent_at:   Optional[datetime] = None
    paid_at:   Optional[datetime] = None
    voided_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


# ===========================================================================
# EDIT INVOICE — PATCH /billing/invoices/{invoice_id}
# ===========================================================================

class InvoiceUpdateRequest(BaseModel):
    """
    Partial update — only provided fields are written.

    Powers four distinct UI interactions on Screen 21:
      Edit Details button  → matter, issued_date, due_date
      Tax % input          → tax_rate_percent (auto-recalculates tax_cents + total)
      Discount input       → discount_cents (auto-recalculates total)
      Settings panel       → payment_terms, notes_to_client

    Blocked if invoice status is 'paid' or 'void'.
    """
    # Edit Details
    matter:      Optional[str]  = None
    issued_date: Optional[date] = None
    due_date:    Optional[date] = None

    # Totals
    tax_rate_percent: Optional[int] = Field(None, ge=0, le=100)   # whole number 0–100
    discount_cents:   Optional[int] = Field(None, ge=0)

    # Settings panel
    payment_terms:   Optional[str] = None
    notes_to_client: Optional[str] = None
