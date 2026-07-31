"""
app/services/billing_service.py

Business logic for Screen 19 — Billing & Time Tracking Dashboard.
One service file for one screen. Mirrors subscription_service.py exactly.

Functions map 1:1 to router endpoints:

  DASHBOARD
    service_get_dashboard_stats         → GET  /billing/dashboard/stats
    service_get_top_unbilled_clients    → GET  /billing/clients/top-unbilled

  BILLING CLIENTS
    service_list_billing_clients        → GET  /billing/clients
    service_get_billing_client          → GET  /billing/clients/{id}
    service_create_billing_client       → POST /billing/clients
    service_sync_from_user              → internal (called on case assignment)
    service_sync_from_employer          → internal (called on case assignment)

  TIME ENTRIES
    service_list_time_entries           → GET  /billing/time-entries
    service_get_time_entry              → GET  /billing/time-entries/{id}
    service_create_time_entry           → POST /billing/time-entries
    service_update_time_entry           → PATCH /billing/time-entries/{id}
    service_delete_time_entry           → DELETE /billing/time-entries/{id}
    service_bulk_action                 → POST /billing/time-entries/bulk-action

  INVOICES
    service_list_invoices               → GET  /billing/invoices
    service_get_invoice                 → GET  /billing/invoices/{id}
    service_create_invoice              → POST /billing/invoices
    service_draft_from_entries          → POST /billing/invoices/draft
    service_update_invoice_status       → PATCH /billing/invoices/{id}/status
"""
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models.visamodels import (
    AttorneyInvoice,
    BillingClient,
    InvoiceLineItem,
    TimeEntry,
)
from app.models.visamodels import Application, AttorneyProfile, EmployerProfile, User


# =============================================================================
# HELPERS
# =============================================================================

def _cents_to_display(cents: int, currency: str = "USD") -> str:
    """87500 → '$875.00'"""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{cents / 100:,.2f}"


def _minutes_to_display(minutes: int) -> str:
    """150 → '2h 30m'"""
    h, m = divmod(minutes, 60)
    if m == 0:
        return f"{h}h"
    if h == 0:
        return f"{m}m"
    return f"{h}h {m}m"


def _compute_amount(duration_minutes: int, hourly_rate_cents: int) -> int:
    """math.ceil — always round up to nearest cent."""
    return math.ceil(duration_minutes / 60 * hourly_rate_cents)


def _client_initials(name: str) -> str:
    """'TechCorp Solutions' → 'TS'"""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper() if len(name) >= 2 else name.upper()


def _deterministic_color(client_id: uuid.UUID) -> str:
    """Stable CSS color class from UUID — same client always same color."""
    colors = ["blue", "green", "purple", "orange", "pink", "teal", "red", "indigo"]
    idx = int(str(client_id).replace("-", ""), 16) % len(colors)
    return colors[idx]


def _period_bounds(period: str) -> Tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for the period."""
    now = datetime.now(timezone.utc)
    if period == "last_month":
        first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = first_this.replace(
            year=first_this.year - 1 if first_this.month == 1 else first_this.year,
            month=12 if first_this.month == 1 else first_this.month - 1,
        )
        end = first_this
    elif period == "ytd":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now
    else:  # this_month (default)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now
    return start, end


# Valid invoice status transitions
_ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    "draft":   ["open", "void"],
    "open":    ["sent", "void"],
    "sent":    ["paid", "void"],
    "overdue": ["paid", "void"],
    "paid":    [],
    "void":    [],
}


async def _resolve_hourly_rate(
    db: AsyncSession,
    attorney_id: uuid.UUID,
    billing_client_id: uuid.UUID,
) -> int:
    """
    Rate priority:
      1. billing_client.custom_rate_cents   (client override)
      2. attorney_profiles.hourly_rate_cents (attorney default)
      3. raise BadRequestException
    """
    client_q = await db.execute(
        select(BillingClient.custom_rate_cents)
        .where(BillingClient.id == billing_client_id)
    )
    row = client_q.first()
    if row and row.custom_rate_cents:
        return row.custom_rate_cents

    profile_q = await db.execute(
        select(AttorneyProfile.hourly_rate_cents)
        .where(AttorneyProfile.user_id == attorney_id)
    )
    profile_row = profile_q.first()
    if profile_row and profile_row.hourly_rate_cents:
        return profile_row.hourly_rate_cents

    raise BadRequestException(
        "No hourly rate configured. Set your default rate in Profile Settings "
        "or configure a client-specific rate before logging time."
    )


async def _generate_invoice_number(db: AsyncSession) -> str:
    """
    INV-{YEAR}-{NNNN}  e.g. INV-2026-0042
    Finds max existing sequence for current year and increments.
    """
    year   = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"
    result = await db.execute(
        select(func.max(AttorneyInvoice.invoice_number))
        .where(AttorneyInvoice.invoice_number.like(f"{prefix}%"))
    )
    max_num = result.scalar()
    try:
        seq = int(max_num.split("-")[-1]) + 1 if max_num else 1
    except (ValueError, IndexError, AttributeError):
        seq = 1
    return f"{prefix}{seq:04d}"


async def _recalculate_invoice_totals(db: AsyncSession, invoice_id: uuid.UUID) -> None:
    """Recomputes subtotal_cents / total_cents from current line items."""
    sum_q = await db.execute(
        select(func.coalesce(func.sum(InvoiceLineItem.total_cents), 0))
        .where(InvoiceLineItem.invoice_id == invoice_id)
    )
    subtotal = int(sum_q.scalar())
    inv_q    = await db.execute(
        select(AttorneyInvoice).where(AttorneyInvoice.id == invoice_id)
    )
    invoice = inv_q.scalar_one_or_none()
    if invoice:
        invoice.subtotal_cents = subtotal
        invoice.total_cents    = max(0, subtotal + invoice.tax_cents - invoice.discount_cents)
        invoice.updated_at     = datetime.now(timezone.utc)


def _enrich_entry(entry: TimeEntry, client_name: str, client_type: str,
                  case_number: Optional[str]) -> TimeEntry:
    entry._duration_display = _minutes_to_display(entry.duration_minutes)      # type: ignore
    entry._amount_display   = _cents_to_display(entry.amount_cents)             # type: ignore
    entry._rate_display     = f"{_cents_to_display(entry.hourly_rate_cents)}/hr"# type: ignore
    entry._client_name      = client_name                                        # type: ignore
    entry._client_type      = client_type.capitalize()                           # type: ignore
    entry._case_number      = case_number                                        # type: ignore
    return entry


def _enrich_invoice(invoice: AttorneyInvoice, client_name: str, client_type: str,
                    attorney_name: str, case_label: Optional[str]) -> AttorneyInvoice:
    invoice._subtotal_display = _cents_to_display(invoice.subtotal_cents, invoice.currency)  # type: ignore
    invoice._total_display    = _cents_to_display(invoice.total_cents,    invoice.currency)  # type: ignore
    invoice._client_name      = client_name                                                    # type: ignore
    invoice._client_type      = client_type.capitalize()                                       # type: ignore
    invoice._attorney_name    = attorney_name                                                  # type: ignore
    invoice._case_label       = case_label                                                     # type: ignore
    invoice._is_overdue       = (                                                              # type: ignore
        invoice.due_date is not None
        and invoice.due_date < date.today()
        and invoice.status not in ("paid", "void")
    )
    for item in getattr(invoice, "line_items", []):
        item._unit_amount_display = _cents_to_display(item.unit_amount_cents, invoice.currency)  # type: ignore
        item._total_display       = _cents_to_display(item.total_cents,       invoice.currency)  # type: ignore
    return invoice


def _enrich_client(client: BillingClient, unbilled_minutes: int,
                   unbilled_cents: int) -> BillingClient:
    hours_float  = unbilled_minutes / 60
    hours_str    = f"{hours_float:.1f}h" if hours_float != int(hours_float) else f"{int(hours_float)}h"
    client._unbilled_hours   = hours_str                               # type: ignore
    client._unbilled_amount  = _cents_to_display(unbilled_cents)       # type: ignore
    client._unbilled_minutes = unbilled_minutes                         # type: ignore
    client._unbilled_cents   = unbilled_cents                           # type: ignore
    client._rate_display     = (                                        # type: ignore
        f"{_cents_to_display(client.custom_rate_cents)}/hr"
        if client.custom_rate_cents else ""
    )
    return client


# =============================================================================
# ── DASHBOARD ─────────────────────────────────────────────────────────────────
# =============================================================================

async def service_get_dashboard_stats(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    period:      str = "this_month",
) -> Dict[str, Any]:
    """Powers the 4 KPI cards at the top of Screen 19."""
    start, end = _period_bounds(period)

    # Card 1 — Revenue (paid invoices in period)
    rev_q = await db.execute(
        select(func.coalesce(func.sum(AttorneyInvoice.total_cents), 0))
        .where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status      == "paid",
            AttorneyInvoice.paid_at     >= start,
            AttorneyInvoice.paid_at     <= end,
        )
    )
    revenue_cents = int(rev_q.scalar())

    # Trend vs previous period
    prev_start, prev_end = _period_bounds(
        "last_month" if period == "this_month" else "this_month"
    )
    prev_rev_q = await db.execute(
        select(func.coalesce(func.sum(AttorneyInvoice.total_cents), 0))
        .where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status      == "paid",
            AttorneyInvoice.paid_at     >= prev_start,
            AttorneyInvoice.paid_at     <= prev_end,
        )
    )
    prev_revenue_cents = int(prev_rev_q.scalar())
    trend_pct: Optional[float] = (
        round((revenue_cents - prev_revenue_cents) / prev_revenue_cents * 100, 1)
        if prev_revenue_cents > 0 else None
    )

    # Card 2 — Billable Hours
    hours_q = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0))
        .where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.is_billable.is_(True),
            TimeEntry.entry_date  >= start.date(),
            TimeEntry.entry_date  <= end.date(),
        )
    )
    billable_minutes = int(hours_q.scalar())

    unbilled_q = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0))
        .where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.is_billable.is_(True),
            TimeEntry.status      == "unbilled",
            TimeEntry.entry_date  >= start.date(),
            TimeEntry.entry_date  <= end.date(),
        )
    )
    unbilled_minutes = int(unbilled_q.scalar())

    # Card 3 — Outstanding Invoices
    outstanding_q = await db.execute(
        select(func.count(AttorneyInvoice.id))
        .where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status.in_(["open", "sent", "overdue"]),
        )
    )
    outstanding_count = int(outstanding_q.scalar())

    overdue_q = await db.execute(
        select(func.count(AttorneyInvoice.id))
        .where(
            AttorneyInvoice.attorney_id == attorney_id,
            AttorneyInvoice.status.in_(["open", "sent"]),
            AttorneyInvoice.due_date    <  date.today(),
        )
    )
    overdue_count = int(overdue_q.scalar())

    # Card 4 — Active Clients
    active_q = await db.execute(
        select(func.count(func.distinct(TimeEntry.billing_client_id)))
        .where(
            TimeEntry.attorney_id == attorney_id,
            TimeEntry.entry_date  >= start.date(),
            TimeEntry.entry_date  <= end.date(),
        )
    )
    active_client_count = int(active_q.scalar())

    new_clients_q = await db.execute(
        select(func.count(BillingClient.id))
        .where(
            BillingClient.created_at >= start,
            BillingClient.created_at <= end,
            BillingClient.is_active.is_(True),
        )
    )
    new_client_count = int(new_clients_q.scalar())

    # Build KPI cards
    billable_hours_float = billable_minutes / 60
    hours_val = (
        f"{billable_hours_float:.1f}"
        if billable_hours_float != int(billable_hours_float)
        else str(int(billable_hours_float))
    )

    return {
        "period":  period,
        "revenue": {
            "value":           _cents_to_display(revenue_cents),
            "label":           "This Month Revenue",
            "sub_label":       (f"+{trend_pct}% vs last month" if (trend_pct or 0) > 0
                                else f"{trend_pct}% vs last month" if trend_pct else None),
            "trend_pct":       trend_pct,
            "trend_direction": "up" if (trend_pct or 0) >= 0 else "down",
            "alert":           None,
        },
        "billable_hours": {
            "value":           hours_val,
            "label":           "Billable Hours",
            "sub_label":       f"{unbilled_minutes // 60} unbilled hours" if unbilled_minutes else None,
            "trend_pct":       None,
            "trend_direction": None,
            "alert":           None,
        },
        "outstanding": {
            "value":           str(outstanding_count),
            "label":           "Outstanding Invoices",
            "sub_label":       None,
            "trend_pct":       None,
            "trend_direction": None,
            "alert":           f"{overdue_count} overdue" if overdue_count else None,
        },
        "active_clients": {
            "value":           str(active_client_count),
            "label":           "Active Clients",
            "sub_label":       f"+{new_client_count} new this month" if new_client_count else None,
            "trend_pct":       None,
            "trend_direction": None,
            "alert":           None,
        },
        "revenue_cents":       revenue_cents,
        "billable_minutes":    billable_minutes,
        "outstanding_count":   outstanding_count,
        "overdue_count":       overdue_count,
        "active_client_count": active_client_count,
        "new_client_count":    new_client_count,
    }


async def service_get_top_unbilled_clients(
    db:          AsyncSession,
    attorney_id: uuid.UUID,
    limit:       int = 10,
) -> Dict[str, Any]:
    """Powers the Top Clients to Bill sidebar panel."""
    q = (
        select(
            BillingClient.id,
            BillingClient.display_name,
            BillingClient.client_type,
            func.coalesce(func.sum(TimeEntry.duration_minutes), 0).label("unbilled_minutes"),
            func.coalesce(func.sum(TimeEntry.amount_cents), 0).label("unbilled_cents"),
        )
        .outerjoin(
            TimeEntry,
            and_(
                TimeEntry.billing_client_id == BillingClient.id,
                TimeEntry.status            == "unbilled",
                TimeEntry.is_billable.is_(True),
                TimeEntry.attorney_id       == attorney_id,
            ),
        )
        .where(BillingClient.is_active.is_(True))
        .group_by(BillingClient.id, BillingClient.display_name, BillingClient.client_type)
        .having(func.coalesce(func.sum(TimeEntry.amount_cents), 0) > 0)
        .order_by(func.coalesce(func.sum(TimeEntry.amount_cents), 0).desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows   = result.all()

    items                  = []
    total_unbilled_cents   = 0
    total_unbilled_minutes = 0

    for row in rows:
        total_unbilled_cents   += row.unbilled_cents
        total_unbilled_minutes += row.unbilled_minutes
        hours_float  = row.unbilled_minutes / 60
        hours_str    = f"{hours_float:.1f}h" if hours_float != int(hours_float) else f"{int(hours_float)}h"
        items.append({
            "billing_client_id": row.id,
            "display_name":      row.display_name,
            "client_type":       row.client_type.capitalize(),
            "initials":          _client_initials(row.display_name),
            "color_class":       _deterministic_color(row.id),
            "unbilled_hours":    hours_str,
            "unbilled_amount":   _cents_to_display(row.unbilled_cents),
            "unbilled_minutes":  row.unbilled_minutes,
            "unbilled_cents":    row.unbilled_cents,
        })

    return {
        "items":                  items,
        "total_unbilled_cents":   total_unbilled_cents,
        "total_unbilled_minutes": total_unbilled_minutes,
        "total_unbilled_display": _cents_to_display(total_unbilled_cents),
    }


# =============================================================================
# ── BILLING CLIENTS ───────────────────────────────────────────────────────────
# =============================================================================

async def service_list_billing_clients(
    db:          AsyncSession,
    search:      Optional[str]  = None,
    client_type: Optional[str]  = None,
    is_active:   Optional[bool] = True,
    sort_by:     str            = "display_name",
    sort_order:  str            = "asc",
    page:        int            = 1,
    page_size:   int            = 20,
) -> Tuple[List[Any], int]:
    q = (
        select(
            BillingClient,
            func.coalesce(
                func.sum(TimeEntry.duration_minutes).filter(
                    TimeEntry.status     == "unbilled",
                    TimeEntry.is_billable.is_(True),
                ), 0
            ).label("unbilled_minutes"),
            func.coalesce(
                func.sum(TimeEntry.amount_cents).filter(
                    TimeEntry.status     == "unbilled",
                    TimeEntry.is_billable.is_(True),
                ), 0
            ).label("unbilled_cents"),
        )
        .outerjoin(TimeEntry, TimeEntry.billing_client_id == BillingClient.id)
        .group_by(BillingClient.id)
    )
    if is_active is not None:
        q = q.where(BillingClient.is_active.is_(is_active))
    if search:
        q = q.where(func.lower(BillingClient.display_name).like(f"%{search.lower()}%"))
    if client_type:
        q = q.where(BillingClient.client_type == client_type)

    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar() or 0

    sort_map = {
        "display_name":    BillingClient.display_name,
        "unbilled_amount": func.coalesce(func.sum(TimeEntry.amount_cents), 0),
        "created_at":      BillingClient.created_at,
    }
    col = sort_map.get(sort_by, BillingClient.display_name)
    q = q.order_by(col.asc() if sort_order == "asc" else col.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)

    rows     = (await db.execute(q)).all()
    enriched = []
    for row in rows:
        client: BillingClient = row.BillingClient
        _enrich_client(client, row.unbilled_minutes, row.unbilled_cents)
        enriched.append(client)
    return enriched, total


async def service_get_billing_client(
    db: AsyncSession, client_id: uuid.UUID
) -> BillingClient:
    q = (
        select(
            BillingClient,
            func.coalesce(
                func.sum(TimeEntry.duration_minutes).filter(
                    TimeEntry.status     == "unbilled",
                    TimeEntry.is_billable.is_(True),
                ), 0
            ).label("unbilled_minutes"),
            func.coalesce(
                func.sum(TimeEntry.amount_cents).filter(
                    TimeEntry.status     == "unbilled",
                    TimeEntry.is_billable.is_(True),
                ), 0
            ).label("unbilled_cents"),
        )
        .outerjoin(TimeEntry, TimeEntry.billing_client_id == BillingClient.id)
        .where(BillingClient.id == client_id)
        .group_by(BillingClient.id)
    )
    row = (await db.execute(q)).first()
    if not row:
        raise NotFoundException(f"Billing client {client_id} not found.")
    _enrich_client(row.BillingClient, row.unbilled_minutes, row.unbilled_cents)
    return row.BillingClient


async def service_create_billing_client(
    db: AsyncSession, payload: Any, created_by: uuid.UUID
) -> BillingClient:
    if payload.user_id:
        existing = (await db.execute(
            select(BillingClient).where(BillingClient.user_id == payload.user_id)
        )).scalar_one_or_none()
        if existing:
            raise ConflictException(f"Billing client for user {payload.user_id} already exists.")

    if payload.employer_profile_id:
        existing = (await db.execute(
            select(BillingClient).where(
                BillingClient.employer_profile_id == payload.employer_profile_id)
        )).scalar_one_or_none()
        if existing:
            raise ConflictException(
                f"Billing client for employer {payload.employer_profile_id} already exists.")

    now    = datetime.now(timezone.utc)
    client = BillingClient(
        id                  = uuid.uuid4(),
        user_id             = payload.user_id,
        employer_profile_id = payload.employer_profile_id,
        display_name        = payload.display_name,
        client_type         = payload.client_type,
        billing_email       = payload.billing_email,
        billing_phone       = payload.billing_phone,
        custom_rate_cents   = payload.custom_rate_cents,
        is_active           = True,
        created_by          = created_by,
        modified_by         = created_by,
        created_at          = now,
        updated_at          = now,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return await service_get_billing_client(db, client.id)


async def service_sync_from_user(
    db: AsyncSession, user_id: uuid.UUID, created_by: uuid.UUID
) -> BillingClient:
    """Idempotent upsert — call when attorney assigns a case to an individual client."""
    existing = (await db.execute(
        select(BillingClient).where(BillingClient.user_id == user_id)
    )).scalar_one_or_none()

    user_row = (await db.execute(
        select(User.first_name, User.last_name, User.email).where(User.id == user_id)
    )).first()
    if not user_row:
        raise NotFoundException(f"User {user_id} not found.")

    display_name = f"{user_row.first_name} {user_row.last_name}"
    now          = datetime.now(timezone.utc)

    if existing:
        existing.display_name  = display_name
        existing.billing_email = existing.billing_email or user_row.email
        existing.modified_by   = created_by
        existing.updated_at    = now
        await db.commit()
        await db.refresh(existing)
        return existing

    client = BillingClient(
        id            = uuid.uuid4(),
        user_id       = user_id,
        display_name  = display_name,
        client_type   = "individual",
        billing_email = user_row.email,
        is_active     = True,
        created_by    = created_by,
        modified_by   = created_by,
        created_at    = now,
        updated_at    = now,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def service_sync_from_employer(
    db: AsyncSession, employer_profile_id: uuid.UUID, created_by: uuid.UUID
) -> BillingClient:
    """Idempotent upsert — call when attorney assigns a case to a corporate client."""
    existing = (await db.execute(
        select(BillingClient).where(
            BillingClient.employer_profile_id == employer_profile_id)
    )).scalar_one_or_none()

    emp_row = (await db.execute(
        select(EmployerProfile.company_name, EmployerProfile.contact_email,
               EmployerProfile.contact_phone)
        .where(EmployerProfile.id == employer_profile_id)
    )).first()
    if not emp_row:
        raise NotFoundException(f"Employer profile {employer_profile_id} not found.")

    now = datetime.now(timezone.utc)

    if existing:
        existing.display_name  = emp_row.company_name
        existing.billing_email = existing.billing_email or emp_row.contact_email
        existing.billing_phone = existing.billing_phone or emp_row.contact_phone
        existing.modified_by   = created_by
        existing.updated_at    = now
        await db.commit()
        await db.refresh(existing)
        return existing

    client = BillingClient(
        id                  = uuid.uuid4(),
        employer_profile_id = employer_profile_id,
        display_name        = emp_row.company_name,
        client_type         = "corporate",
        billing_email       = emp_row.contact_email,
        billing_phone       = emp_row.contact_phone,
        is_active           = True,
        created_by          = created_by,
        modified_by         = created_by,
        created_at          = now,
        updated_at          = now,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


# =============================================================================
# ── TIME ENTRIES ──────────────────────────────────────────────────────────────
# =============================================================================

async def service_list_time_entries(
    db:                AsyncSession,
    attorney_id:       uuid.UUID,
    search:            Optional[str]       = None,
    status:            Optional[str]       = None,
    billing_client_id: Optional[uuid.UUID] = None,
    application_id:    Optional[uuid.UUID] = None,
    is_billable:       Optional[bool]      = None,
    date_from:         Optional[str]       = None,
    date_to:           Optional[str]       = None,
    sort_by:           str                 = "entry_date",
    sort_order:        str                 = "desc",
    page:              int                 = 1,
    page_size:         int                 = 20,
) -> Tuple[List[Any], int]:
    q = (
        select(
            TimeEntry,
            BillingClient.display_name.label("client_name"),
            BillingClient.client_type.label("client_type"),
            Application.application_number.label("case_number"),
        )
        .join(BillingClient, TimeEntry.billing_client_id == BillingClient.id)
        .outerjoin(Application, TimeEntry.application_id == Application.id)
        .where(TimeEntry.attorney_id == attorney_id)
    )

    if search:
        term = f"%{search.lower()}%"
        q = q.where(or_(
            func.lower(TimeEntry.description).like(term),
            func.lower(BillingClient.display_name).like(term),
            func.lower(Application.application_number).like(term),
        ))
    if status:
        q = q.where(TimeEntry.status == status)
    if billing_client_id:
        q = q.where(TimeEntry.billing_client_id == billing_client_id)
    if application_id:
        q = q.where(TimeEntry.application_id == application_id)
    if is_billable is not None:
        q = q.where(TimeEntry.is_billable.is_(is_billable))
    if date_from:
        q = q.where(TimeEntry.entry_date >= date_from)
    if date_to:
        q = q.where(TimeEntry.entry_date <= date_to)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0

    sort_map = {
        "entry_date": TimeEntry.entry_date,
        "amount":     TimeEntry.amount_cents,
        "duration":   TimeEntry.duration_minutes,
        "client":     BillingClient.display_name,
        "status":     TimeEntry.status,
        "created_at": TimeEntry.created_at,
    }
    col = sort_map.get(sort_by, TimeEntry.entry_date)
    q   = q.order_by(col.asc() if sort_order == "asc" else col.desc())
    q   = q.offset((page - 1) * page_size).limit(page_size)

    rows     = (await db.execute(q)).all()
    enriched = []
    for row in rows:
        _enrich_entry(row.TimeEntry, row.client_name, row.client_type, row.case_number)
        enriched.append(row.TimeEntry)
    return enriched, total


async def service_get_time_entry(
    db: AsyncSession, entry_id: uuid.UUID, attorney_id: uuid.UUID
) -> TimeEntry:
    q = (
        select(
            TimeEntry,
            BillingClient.display_name.label("client_name"),
            BillingClient.client_type.label("client_type"),
            Application.application_number.label("case_number"),
        )
        .join(BillingClient, TimeEntry.billing_client_id == BillingClient.id)
        .outerjoin(Application, TimeEntry.application_id == Application.id)
        .where(TimeEntry.id == entry_id, TimeEntry.attorney_id == attorney_id)
    )
    row = (await db.execute(q)).first()
    if not row:
        raise NotFoundException(f"Time entry {entry_id} not found.")
    _enrich_entry(row.TimeEntry, row.client_name, row.client_type, row.case_number)
    return row.TimeEntry


async def service_create_time_entry(
    db: AsyncSession, payload: Any, attorney_id: uuid.UUID
) -> TimeEntry:
    if not (await db.execute(
        select(BillingClient).where(
            BillingClient.id == payload.billing_client_id,
            BillingClient.is_active.is_(True),
        )
    )).scalar_one_or_none():
        raise NotFoundException(f"Billing client {payload.billing_client_id} not found.")

    if payload.application_id:
        if not (await db.execute(
            select(Application).where(Application.id == payload.application_id)
        )).scalar_one_or_none():
            raise NotFoundException(f"Application {payload.application_id} not found.")

    rate   = await _resolve_hourly_rate(db, attorney_id, payload.billing_client_id)
    amount = _compute_amount(payload.duration_minutes, rate)
    now    = datetime.now(timezone.utc)

    entry = TimeEntry(
        id                = uuid.uuid4(),
        attorney_id       = attorney_id,
        billing_client_id = payload.billing_client_id,
        application_id    = payload.application_id,
        entry_date        = payload.entry_date,
        duration_minutes  = payload.duration_minutes,
        description       = payload.description,
        is_billable       = payload.is_billable,
        hourly_rate_cents = rate,
        amount_cents      = amount,
        status            = "unbilled",
        created_by        = attorney_id,
        modified_by       = attorney_id,
        created_at        = now,
        updated_at        = now,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return await service_get_time_entry(db, entry.id, attorney_id)


async def service_update_time_entry(
    db: AsyncSession, entry_id: uuid.UUID, payload: Any, attorney_id: uuid.UUID
) -> TimeEntry:
    entry = (await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == entry_id, TimeEntry.attorney_id == attorney_id)
    )).scalar_one_or_none()
    if not entry:
        raise NotFoundException(f"Time entry {entry_id} not found.")
    if entry.status != "unbilled":
        raise BadRequestException(
            f"Cannot edit a '{entry.status}' entry. Void the invoice first."
        )

    update_data  = payload.model_dump(exclude_unset=True)
    new_client   = update_data.get("billing_client_id", entry.billing_client_id)
    new_duration = update_data.get("duration_minutes",  entry.duration_minutes)
    needs_recalc = "billing_client_id" in update_data or "duration_minutes" in update_data

    for field, value in update_data.items():
        if hasattr(entry, field):
            setattr(entry, field, value)

    if needs_recalc:
        rate                  = await _resolve_hourly_rate(db, attorney_id, new_client)
        entry.hourly_rate_cents = rate
        entry.amount_cents      = _compute_amount(new_duration, rate)

    entry.modified_by = attorney_id
    entry.updated_at  = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)
    return await service_get_time_entry(db, entry.id, attorney_id)


async def service_delete_time_entry(
    db: AsyncSession, entry_id: uuid.UUID, attorney_id: uuid.UUID
) -> None:
    entry = (await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == entry_id, TimeEntry.attorney_id == attorney_id)
    )).scalar_one_or_none()
    if not entry:
        raise NotFoundException(f"Time entry {entry_id} not found.")
    if entry.status != "unbilled":
        raise BadRequestException(
            f"Cannot delete a '{entry.status}' entry."
        )
    await db.delete(entry)
    await db.commit()


async def service_bulk_action(
    db: AsyncSession, payload: Any, attorney_id: uuid.UUID
) -> Dict[str, Any]:
    """Drives the bottom action bar: Add to Invoice | Mark Billed | Delete."""
    entries = list((await db.execute(
        select(TimeEntry).where(
            TimeEntry.id.in_(payload.entry_ids),
            TimeEntry.attorney_id == attorney_id,
        )
    )).scalars().all())

    if not entries:
        raise NotFoundException("No matching time entries found.")

    now      = datetime.now(timezone.utc)
    affected = 0
    skipped  = 0

    if payload.action == "add_to_invoice":
        invoice = (await db.execute(
            select(AttorneyInvoice).where(
                AttorneyInvoice.id          == payload.invoice_id,
                AttorneyInvoice.attorney_id == attorney_id,
            )
        )).scalar_one_or_none()
        if not invoice:
            raise NotFoundException(f"Invoice {payload.invoice_id} not found.")
        if invoice.status not in ("draft", "open"):
            raise BadRequestException(
                f"Cannot add entries to a '{invoice.status}' invoice."
            )
        for entry in entries:
            if entry.status != "unbilled":
                skipped += 1
                continue
            entry.status      = "invoiced"
            entry.invoice_id  = payload.invoice_id
            entry.invoiced_at = now
            entry.modified_by = attorney_id
            entry.updated_at  = now
            affected += 1
        if affected:
            await _recalculate_invoice_totals(db, payload.invoice_id)

    elif payload.action == "mark_billed":
        for entry in entries:
            if entry.status != "unbilled":
                skipped += 1
                continue
            entry.status      = "paid"
            entry.modified_by = attorney_id
            entry.updated_at  = now
            affected += 1

    elif payload.action == "delete":
        for entry in entries:
            if entry.status != "unbilled":
                skipped += 1
                continue
            await db.delete(entry)
            affected += 1

    await db.commit()

    labels = {"add_to_invoice": "added to invoice", "mark_billed": "marked as billed",
               "delete": "deleted"}
    label  = labels.get(payload.action, payload.action)
    return {
        "action":         payload.action,
        "affected_count": affected,
        "skipped_count":  skipped,
        "message": (
            f"{affected} entr{'y' if affected == 1 else 'ies'} {label}."
            + (f" {skipped} skipped (wrong status)." if skipped else "")
        ),
    }


# =============================================================================
# ── INVOICES ──────────────────────────────────────────────────────────────────
# =============================================================================

async def _fetch_invoice(
    db: AsyncSession, invoice_id: uuid.UUID, attorney_id: Optional[uuid.UUID]
) -> AttorneyInvoice:
    """Load full invoice with line_items + joined names."""
    q = (
        select(
            AttorneyInvoice,
            BillingClient.display_name.label("client_name"),
            BillingClient.client_type.label("client_type"),
            User.first_name.label("attorney_first"),
            User.last_name.label("attorney_last"),
            Application.application_number.label("case_number"),
        )
        .options(selectinload(AttorneyInvoice.line_items))
        .join(BillingClient, AttorneyInvoice.billing_client_id == BillingClient.id)
        .join(User, AttorneyInvoice.attorney_id == User.id)
        .outerjoin(Application, AttorneyInvoice.application_id == Application.id)
        .where(AttorneyInvoice.id == invoice_id)
    )
    if attorney_id:
        q = q.where(AttorneyInvoice.attorney_id == attorney_id)
    row = (await db.execute(q)).first()
    if not row:
        raise NotFoundException(f"Invoice {invoice_id} not found.")
    _enrich_invoice(
        row.AttorneyInvoice,
        client_name   = row.client_name,
        client_type   = row.client_type,
        attorney_name = f"{row.attorney_first} {row.attorney_last}",
        case_label    = row.case_number,
    )
    return row.AttorneyInvoice


async def service_list_invoices(
    db:                AsyncSession,
    attorney_id:       uuid.UUID,
    search:            Optional[str]       = None,
    status:            Optional[str]       = None,
    billing_client_id: Optional[uuid.UUID] = None,
    date_from:         Optional[str]       = None,
    date_to:           Optional[str]       = None,
    sort_by:           str                 = "created_at",
    sort_order:        str                 = "desc",
    page:              int                 = 1,
    page_size:         int                 = 20,
) -> Tuple[List[Any], int]:
    q = (
        select(
            AttorneyInvoice,
            BillingClient.display_name.label("client_name"),
            BillingClient.client_type.label("client_type"),
            User.first_name.label("attorney_first"),
            User.last_name.label("attorney_last"),
            Application.application_number.label("case_number"),
        )
        .join(BillingClient, AttorneyInvoice.billing_client_id == BillingClient.id)
        .join(User, AttorneyInvoice.attorney_id == User.id)
        .outerjoin(Application, AttorneyInvoice.application_id == Application.id)
        .where(AttorneyInvoice.attorney_id == attorney_id)
    )
    if search:
        term = f"%{search.lower()}%"
        q = q.where(or_(
            func.lower(AttorneyInvoice.invoice_number).like(term),
            func.lower(BillingClient.display_name).like(term),
        ))
    if status:
        q = q.where(AttorneyInvoice.status == status)
    if billing_client_id:
        q = q.where(AttorneyInvoice.billing_client_id == billing_client_id)
    if date_from:
        q = q.where(AttorneyInvoice.created_at >= date_from)
    if date_to:
        q = q.where(AttorneyInvoice.created_at <= date_to)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0

    sort_map = {
        "created_at":     AttorneyInvoice.created_at,
        "total":          AttorneyInvoice.total_cents,
        "due_date":       AttorneyInvoice.due_date,
        "status":         AttorneyInvoice.status,
        "client":         BillingClient.display_name,
        "invoice_number": AttorneyInvoice.invoice_number,
    }
    col = sort_map.get(sort_by, AttorneyInvoice.created_at)
    q   = q.order_by(col.asc() if sort_order == "asc" else col.desc())
    q   = q.offset((page - 1) * page_size).limit(page_size)

    rows     = (await db.execute(q)).all()
    today    = date.today()
    enriched = []
    for row in rows:
        inv: AttorneyInvoice = row.AttorneyInvoice
        inv._subtotal_display = _cents_to_display(inv.subtotal_cents, inv.currency)    # type: ignore
        inv._total_display    = _cents_to_display(inv.total_cents,    inv.currency)    # type: ignore
        inv._client_name      = row.client_name                                         # type: ignore
        inv._client_type      = row.client_type.capitalize()                            # type: ignore
        inv._attorney_name    = f"{row.attorney_first} {row.attorney_last}"             # type: ignore
        inv._case_label       = row.case_number                                         # type: ignore
        inv._is_overdue       = (                                                       # type: ignore
            inv.due_date is not None
            and inv.due_date < today
            and inv.status not in ("paid", "void")
        )
        enriched.append(inv)
    return enriched, total


async def service_get_invoice(
    db: AsyncSession, invoice_id: uuid.UUID, attorney_id: uuid.UUID
) -> AttorneyInvoice:
    return await _fetch_invoice(db, invoice_id, attorney_id)


async def service_create_invoice(
    db: AsyncSession, payload: Any, attorney_id: uuid.UUID
) -> AttorneyInvoice:
    if not (await db.execute(
        select(BillingClient).where(
            BillingClient.id == payload.billing_client_id,
            BillingClient.is_active.is_(True),
        )
    )).scalar_one_or_none():
        raise NotFoundException(f"Billing client {payload.billing_client_id} not found.")

    invoice_number = await _generate_invoice_number(db)
    now = datetime.now(timezone.utc)

    invoice = AttorneyInvoice(
        id                = uuid.uuid4(),
        invoice_number    = invoice_number,
        attorney_id       = attorney_id,
        billing_client_id = payload.billing_client_id,
        application_id    = payload.application_id,
        due_date          = payload.due_date,
        subtotal_cents    = 0,
        tax_cents         = 0,
        discount_cents    = 0,
        total_cents       = 0,
        currency          = "USD",
        status            = "draft",
        notes             = payload.notes,
        created_by        = attorney_id,
        modified_by       = attorney_id,
        created_at        = now,
        updated_at        = now,
    )
    db.add(invoice)
    await db.flush()

    subtotal = 0
    for idx, li in enumerate(payload.line_items):
        total = li.quantity * li.unit_amount_cents
        db.add(InvoiceLineItem(
            id                = uuid.uuid4(),
            invoice_id        = invoice.id,
            time_entry_id     = li.time_entry_id,
            description       = li.description,
            quantity          = li.quantity,
            unit_amount_cents = li.unit_amount_cents,
            total_cents       = total,
            sort_order        = li.sort_order or idx,
            created_by        = attorney_id,
            modified_by       = attorney_id,
            created_at        = now,
            updated_at        = now,
        ))
        subtotal += total

    invoice.subtotal_cents = subtotal
    invoice.total_cents    = subtotal
    await db.commit()
    await db.refresh(invoice)
    return await _fetch_invoice(db, invoice.id, attorney_id)


async def service_draft_from_entries(
    db: AsyncSession, payload: Any, attorney_id: uuid.UUID
) -> AttorneyInvoice:
    """Draft Invoice button — creates invoice from selected unbilled entries."""
    entries = list((await db.execute(
        select(TimeEntry).where(
            TimeEntry.id.in_(payload.entry_ids),
            TimeEntry.attorney_id       == attorney_id,
            TimeEntry.billing_client_id == payload.billing_client_id,
            TimeEntry.status            == "unbilled",
        )
    )).scalars().all())

    if not entries:
        raise BadRequestException(
            "No eligible unbilled entries found for this client."
        )
    if len(entries) != len(payload.entry_ids):
        found   = {e.id for e in entries}
        missing = [str(eid) for eid in payload.entry_ids if eid not in found]
        raise BadRequestException(
            f"Some entries are ineligible (wrong client/status/not found): {', '.join(missing)}"
        )

    invoice_number = await _generate_invoice_number(db)
    subtotal       = sum(e.amount_cents for e in entries)
    now            = datetime.now(timezone.utc)

    invoice = AttorneyInvoice(
        id                = uuid.uuid4(),
        invoice_number    = invoice_number,
        attorney_id       = attorney_id,
        billing_client_id = payload.billing_client_id,
        application_id    = payload.application_id,
        due_date          = payload.due_date,
        subtotal_cents    = subtotal,
        tax_cents         = 0,
        discount_cents    = 0,
        total_cents       = subtotal,
        currency          = "USD",
        status            = "draft",
        notes             = payload.notes,
        created_by        = attorney_id,
        modified_by       = attorney_id,
        created_at        = now,
        updated_at        = now,
    )
    db.add(invoice)
    await db.flush()

    for idx, entry in enumerate(entries):
        h, m         = divmod(entry.duration_minutes, 60)
        duration_str = _minutes_to_display(entry.duration_minutes)
        rate_str     = _cents_to_display(entry.hourly_rate_cents)
        db.add(InvoiceLineItem(
            id                = uuid.uuid4(),
            invoice_id        = invoice.id,
            time_entry_id     = entry.id,
            description       = f"{entry.description} — {duration_str} @ {rate_str}/hr",
            quantity          = entry.duration_minutes,
            unit_amount_cents = entry.hourly_rate_cents,
            total_cents       = entry.amount_cents,
            sort_order        = idx,
            created_by        = attorney_id,
            modified_by       = attorney_id,
            created_at        = now,
            updated_at        = now,
        ))
        entry.status      = "invoiced"
        entry.invoice_id  = invoice.id
        entry.invoiced_at = now
        entry.modified_by = attorney_id
        entry.updated_at  = now

    await db.commit()
    await db.refresh(invoice)
    return await _fetch_invoice(db, invoice.id, attorney_id)


async def service_update_invoice_status(
    db: AsyncSession, invoice_id: uuid.UUID, payload: Any, attorney_id: uuid.UUID
) -> AttorneyInvoice:
    invoice = (await db.execute(
        select(AttorneyInvoice).where(
            AttorneyInvoice.id          == invoice_id,
            AttorneyInvoice.attorney_id == attorney_id,
        )
    )).scalar_one_or_none()
    if not invoice:
        raise NotFoundException(f"Invoice {invoice_id} not found.")

    allowed = _ALLOWED_TRANSITIONS.get(invoice.status, [])
    if payload.status not in allowed:
        raise BadRequestException(
            f"Cannot transition from '{invoice.status}' to '{payload.status}'. "
            f"Allowed: {allowed or ['none — terminal state']}."
        )

    now             = datetime.now(timezone.utc)
    invoice.status  = payload.status
    invoice.modified_by = attorney_id
    invoice.updated_at  = now

    if payload.status == "open":
        invoice.issued_date = invoice.issued_date or now.date()

    elif payload.status == "sent":
        invoice.sent_at     = now
        invoice.issued_date = invoice.issued_date or now.date()

    elif payload.status == "paid":
        invoice.paid_at = payload.paid_at or now
        for entry in (await db.execute(
            select(TimeEntry).where(
                TimeEntry.invoice_id == invoice_id,
                TimeEntry.status     == "invoiced",
            )
        )).scalars().all():
            entry.status      = "paid"
            entry.modified_by = attorney_id
            entry.updated_at  = now

    elif payload.status == "void":
        invoice.voided_at   = now
        invoice.void_reason = payload.void_reason
        invoice.voided_by   = attorney_id
        # Release time entries back to unbilled
        for entry in (await db.execute(
            select(TimeEntry).where(
                TimeEntry.invoice_id == invoice_id,
                TimeEntry.status     == "invoiced",
            )
        )).scalars().all():
            entry.status      = "unbilled"
            entry.invoice_id  = None
            entry.invoiced_at = None
            entry.modified_by = attorney_id
            entry.updated_at  = now

    await db.commit()
    await db.refresh(invoice)
    return await _fetch_invoice(db, invoice.id, attorney_id)
