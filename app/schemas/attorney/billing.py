"""
app/schemas/billing.py

Pydantic v2 schemas for Screen 19 — Billing & Time Tracking Dashboard.

Covers every UI component on the screen:
  - 4 KPI cards (revenue, billable hours, outstanding invoices, active clients)
  - Recent Time Entries table (list, search, filter, pagination, bulk actions)
  - Log Time modal
  - Top Clients to Bill panel (right sidebar)
  - Draft Invoice / New Invoice
  - Invoice list and detail

Mirrors subscription.py style exactly:
  - Literal types mirror model Enums
  - Response models use ConfigDict(from_attributes=True)
  - Computed display fields default to "" (set by service)
  - Pagination: items / total / page / page_size / total_pages
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# LITERALS  (mirror billing_models.py Enum values exactly)
# =============================================================================

BillingClientType    = Literal["corporate", "individual"]
TimeEntryStatus      = Literal["unbilled", "invoiced", "paid", "written_off"]
AttorneyInvoiceStatus = Literal["draft", "open", "sent", "paid", "overdue", "void"]
BulkActionType       = Literal["add_to_invoice", "mark_billed", "delete"]
BillingPeriod        = Literal["this_month", "last_month", "ytd"]


# =============================================================================
# ── BILLING CLIENT ────────────────────────────────────────────────────────────
# =============================================================================

class BillingClientCreate(BaseModel):
    """POST /billing/clients"""
    user_id:             Optional[uuid.UUID] = None
    employer_profile_id: Optional[uuid.UUID] = None
    display_name:        str                 = Field(..., max_length=300)
    client_type:         BillingClientType   = "individual"
    billing_email:       Optional[str]       = Field(None, max_length=255)
    billing_phone:       Optional[str]       = Field(None, max_length=30)
    custom_rate_cents:   Optional[int]       = Field(None, ge=0,
                                                     description="35000 = $350.00/hr")


class BillingClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    display_name:      str
    client_type:       str
    billing_email:     Optional[str]
    billing_phone:     Optional[str]
    custom_rate_cents: Optional[int]
    is_active:         bool
    created_at:        datetime
    # Computed by service
    rate_display:      str = ""   # "$350.00/hr"
    unbilled_hours:    str = ""   # "12.5h"
    unbilled_amount:   str = ""   # "$4,375"
    unbilled_minutes:  int = 0
    unbilled_cents:    int = 0


class BillingClientListResponse(BaseModel):
    items:       List[BillingClientResponse]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# =============================================================================
# ── TIME ENTRY ────────────────────────────────────────────────────────────────
# =============================================================================

class TimeEntryCreate(BaseModel):
    """POST /billing/time-entries — Log Time modal"""
    billing_client_id: uuid.UUID
    application_id:    Optional[uuid.UUID] = None
    entry_date:        date
    duration_minutes:  int  = Field(..., gt=0,
                                    description="Whole minutes only. 150 = 2h 30m")
    description:       str  = Field(..., min_length=1, max_length=2000)
    is_billable:       bool = True
    # hourly_rate_cents resolved by service: client override → attorney default
    # amount_cents computed by service: math.ceil(duration / 60 * rate)


class TimeEntryUpdate(BaseModel):
    """PATCH /billing/time-entries/{id} — only unbilled entries"""
    billing_client_id: Optional[uuid.UUID] = None
    application_id:    Optional[uuid.UUID] = None
    entry_date:        Optional[date]      = None
    duration_minutes:  Optional[int]       = Field(None, gt=0)
    description:       Optional[str]       = Field(None, min_length=1, max_length=2000)
    is_billable:       Optional[bool]      = None


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    attorney_id:       uuid.UUID
    billing_client_id: uuid.UUID
    application_id:    Optional[uuid.UUID]
    entry_date:        date
    duration_minutes:  int
    description:       str
    is_billable:       bool
    hourly_rate_cents: int
    amount_cents:      int
    status:            str
    invoice_id:        Optional[uuid.UUID]
    invoiced_at:       Optional[datetime]
    created_at:        datetime
    updated_at:        datetime
    # Computed by service
    duration_display:    str          = ""    # "2h 30m"
    amount_display:      str          = ""    # "$875.00"
    rate_display:        str          = ""    # "$350.00/hr"
    client_name:         str          = ""    # "TechCorp Solutions"
    client_type:         str          = ""    # "Corporate"
    case_number:         Optional[str] = None  # "H-1B Application"


class TimeEntryListResponse(BaseModel):
    items:       List[TimeEntryResponse]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


class BulkActionRequest(BaseModel):
    """POST /billing/time-entries/bulk-action — bottom action bar"""
    entry_ids:  List[uuid.UUID] = Field(..., min_length=1)
    action:     BulkActionType
    invoice_id: Optional[uuid.UUID] = None   # required when action = add_to_invoice

    @model_validator(mode="after")
    def invoice_required_for_add(self) -> "BulkActionRequest":
        if self.action == "add_to_invoice" and not self.invoice_id:
            raise ValueError(
                "invoice_id is required when action is 'add_to_invoice'."
            )
        return self


class BulkActionResponse(BaseModel):
    action:         str
    affected_count: int
    skipped_count:  int
    message:        str


# =============================================================================
# ── INVOICE LINE ITEM ─────────────────────────────────────────────────────────
# =============================================================================

class InvoiceLineItemCreate(BaseModel):
    """Manual (non-time-entry) line item"""
    time_entry_id:     Optional[uuid.UUID] = None
    description:       str   = Field(..., max_length=500)
    quantity:          int   = Field(1, ge=1)
    unit_amount_cents: int   = Field(..., ge=0)
    sort_order:        int   = 0


class InvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    invoice_id:        uuid.UUID
    time_entry_id:     Optional[uuid.UUID]
    description:       str
    quantity:          int
    unit_amount_cents: int
    total_cents:       int
    sort_order:        int
    # Computed by service
    unit_amount_display: str = ""    # "$350.00"
    total_display:       str = ""    # "$875.00"


# =============================================================================
# ── ATTORNEY INVOICE ──────────────────────────────────────────────────────────
# =============================================================================

class InvoiceCreate(BaseModel):
    """POST /billing/invoices — New Invoice button (manual)"""
    billing_client_id: uuid.UUID
    application_id:    Optional[uuid.UUID]          = None
    due_date:          Optional[date]               = None
    notes:             Optional[str]                = Field(None, max_length=2000)
    line_items:        List[InvoiceLineItemCreate]  = []


class InvoiceDraftFromEntries(BaseModel):
    """POST /billing/invoices/draft — Draft Invoice button on Top Clients panel"""
    billing_client_id: uuid.UUID
    entry_ids:         List[uuid.UUID] = Field(..., min_length=1)
    application_id:    Optional[uuid.UUID] = None
    due_date:          Optional[date]      = None
    notes:             Optional[str]       = Field(None, max_length=2000)


class InvoiceStatusUpdateRequest(BaseModel):
    """PATCH /billing/invoices/{id}/status"""
    status:      Literal["open", "sent", "paid", "void"]
    void_reason: Optional[str]      = Field(None, max_length=300)
    paid_at:     Optional[datetime] = None

    @model_validator(mode="after")
    def void_reason_required(self) -> "InvoiceStatusUpdateRequest":
        if self.status == "void" and not self.void_reason:
            raise ValueError("void_reason is required when voiding an invoice.")
        return self


class AttorneyInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    invoice_number:   str
    attorney_id:      uuid.UUID
    billing_client_id: uuid.UUID
    application_id:   Optional[uuid.UUID]
    issued_date:      Optional[date]
    due_date:         Optional[date]
    subtotal_cents:   int
    tax_cents:        int
    discount_cents:   int
    total_cents:      int
    currency:         str
    status:           str
    sent_at:          Optional[datetime]
    paid_at:          Optional[datetime]
    voided_at:        Optional[datetime]
    void_reason:      Optional[str]
    pdf_url:          Optional[str]
    notes:            Optional[str]
    created_at:       datetime
    updated_at:       datetime
    # Computed by service
    subtotal_display: str          = ""
    total_display:    str          = ""
    client_name:      str          = ""
    client_type:      str          = ""
    attorney_name:    str          = ""
    case_label:       Optional[str] = None
    is_overdue:       bool         = False
    line_items:       List[InvoiceLineItemResponse] = []


class AttorneyInvoiceListItem(BaseModel):
    """Lightweight row for the invoices table — no line_items loaded"""
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    invoice_number:   str
    attorney_id:      uuid.UUID
    billing_client_id: uuid.UUID
    application_id:   Optional[uuid.UUID]
    issued_date:      Optional[date]
    due_date:         Optional[date]
    total_cents:      int
    currency:         str
    status:           str
    paid_at:          Optional[datetime]
    pdf_url:          Optional[str]
    created_at:       datetime
    # Computed by service
    total_display:  str          = ""
    client_name:    str          = ""
    client_type:    str          = ""
    attorney_name:  str          = ""
    case_label:     Optional[str] = None
    is_overdue:     bool         = False


class AttorneyInvoiceListResponse(BaseModel):
    items:       List[AttorneyInvoiceListItem]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# =============================================================================
# ── BILLING DASHBOARD ─────────────────────────────────────────────────────────
# =============================================================================

class KPICard(BaseModel):
    """One of the 4 stat cards at the top of Screen 19"""
    value:           str            # "$24,500.00" | "142.5" | "3" | "24"
    label:           str            # "This Month Revenue"
    sub_label:       Optional[str]  # "+12% vs last month" | "45 unbilled hours"
    trend_pct:       Optional[float] = None   # +12.0
    trend_direction: Optional[str]  = None    # "up" | "down" | "neutral"
    alert:           Optional[str]  = None    # "3 overdue" (shown in orange)


class TopClientItem(BaseModel):
    """One card in the Top Clients to Bill sidebar"""
    billing_client_id: uuid.UUID
    display_name:      str
    client_type:       str     # "Corporate" | "Individual"
    initials:          str     # "TS"
    color_class:       str     # deterministic from UUID for avatar color
    unbilled_hours:    str     # "12.5h"
    unbilled_amount:   str     # "$4,375"
    unbilled_minutes:  int
    unbilled_cents:    int


class BillingDashboardStats(BaseModel):
    """GET /billing/dashboard/stats — entire top section of Screen 19"""
    period:              str       # "this_month" | "last_month" | "ytd"
    revenue:             KPICard
    billable_hours:      KPICard
    outstanding:         KPICard
    active_clients:      KPICard
    # Raw values for client-side use
    revenue_cents:       int
    billable_minutes:    int
    outstanding_count:   int
    overdue_count:       int
    active_client_count: int
    new_client_count:    int


class TopClientsToBillResponse(BaseModel):
    """GET /billing/clients/top-unbilled — right sidebar panel"""
    items:                  List[TopClientItem]
    total_unbilled_cents:   int
    total_unbilled_minutes: int
    total_unbilled_display: str   # "$10,400"
