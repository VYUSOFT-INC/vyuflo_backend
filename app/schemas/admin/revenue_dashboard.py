"""
app/schemas/revenue_dashboard.py

NEW FILE — ADMIN-08 Revenue Dashboard schemas.

WHY NEW FILE (not added to subscription.py):
  - subscription.py already has 461 lines covering ADMIN-07
  - ADMIN-08 is a separate screen with different data contracts
  - Keeping them separate makes the codebase easier to navigate
  - The router (revenue_dashboard.py) imports ONLY from this file

INTERLINK WITH EXISTING FILES:
  - InvoiceStatus is RE-USED from subscription.py — imported here, not redefined
  - SubscriptionStatus is RE-USED from subscription.py — imported here
  - PlanDistributionItem is RE-USED from subscription.py — imported here
  - MRRDataPoint is RE-USED from subscription.py — imported here
  - The router imports from BOTH this file AND subscription.py where needed

USAGE IN ROUTER:
    from app.schemas.revenue_dashboard import (
        RevenueDashboardKPIResponse,
        RevenueTrendResponse,
        RecentTransactionsResponse,
        TrialConversionsResponse,
        FailingPaymentsBannerResponse,
        RevenueTargetCreate,
        RevenueTargetResponse,
        DateRangeFilter,
    )
    from app.schemas.subscription import (
        PlanDistributionItem,   # re-used
        MRRDataPoint,           # re-used
    )
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Re-use existing enums from subscription.py so they stay in sync
# The router imports these directly — no need to redefine them
# from app.schemas.subscription import InvoiceStatus, SubscriptionStatus


# =============================================================================
# DATE RANGE FILTER — shared query param model used by all dashboard endpoints
# =============================================================================

class DateRangeFilter(BaseModel):
    """
    Query param model for all ADMIN-08 endpoints.
    Maps to the date toggle buttons in the header:
      "This Month" | "Q1 2026" | "Last 12 Months" | "Custom"
    """
    period: Literal["this_month", "last_12_months", "quarter", "custom"] = "last_12_months"
    date_from: Optional[date] = Field(None, description="Required when period=custom")
    date_to:   Optional[date] = Field(None, description="Required when period=custom")

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        if info.data.get("period") == "custom":
            if not info.data.get("date_from") or not v:
                raise ValueError("date_from and date_to are required when period=custom")
            if info.data["date_from"] > v:
                raise ValueError("date_from must be before date_to")
        return v


# =============================================================================
# KPI CARDS — GET /admin/revenue/dashboard
# Powers all 4 KPI cards + failing payments alert in one call
# =============================================================================

class KPICardValue(BaseModel):
    """
    Reusable model for a single KPI card value + delta badge.
    Example: MRR = $124.5K with +12.5% vs last month
    """
    value_cents:    Optional[int]   = None   # for money values (MRR, ARR)
    value_display:  str             = ""     # "$124.5K" | "2,845" | "1.2%"
    delta_display:  Optional[str]   = None   # "+12.5%" | "+156" | "▼0.3%"
    delta_label:    Optional[str]   = None   # "vs last month" | "new this month" | "vs last year"
    delta_positive: Optional[bool]  = None   # True=green badge, False=red badge


class FailingPaymentsBanner(BaseModel):
    """
    Powers the red alert banner at top of ADMIN-08:
    "12 Failing Payments Detected — $4,250 in recurring revenue is at risk"
    """
    count:                  int    # "12 Failing Payments"
    mrr_at_risk_cents:      int    # 425000 = $4,250 at risk
    mrr_at_risk_display:    str    # "$4,250"
    by_failure_code: List["FailureCodeBreakdown"] = []
    # Breakdown: "8 expired cards, 4 insufficient funds"


class FailureCodeBreakdown(BaseModel):
    """
    One row in the failing payments breakdown.
    Powers: "expired cards or insufficient funds" text in banner.
    """
    failure_code:   str   # "card_expired" | "insufficient_funds" | "card_declined" etc.
    label:          str   # "Expired Cards" | "Insufficient Funds" (human-readable)
    count:          int
    mrr_at_risk_cents: int
    mrr_at_risk_display: str


class RevenueDashboardKPIResponse(BaseModel):
    """
    GET /admin/revenue/dashboard
    Single response powering the entire top section of ADMIN-08:
      - 4 KPI cards
      - Failing Payments alert banner
    """
    # KPI Card 1 — Monthly Recurring Revenue
    mrr: KPICardValue
    # value_display  = "$124.5K"
    # delta_display  = "+12.5%"
    # delta_label    = "vs last month"
    # delta_positive = True

    # KPI Card 2 — Annual Run Rate
    arr: KPICardValue
    # value_display  = "$1.49M"
    # delta_display  = "+8.2%"
    # delta_label    = "vs last year"
    # delta_positive = True

    # KPI Card 3 — Active Subscribers
    active_subscribers: KPICardValue
    # value_display  = "2,845"
    # delta_display  = "+156"
    # delta_label    = "new this month"
    # delta_positive = True

    # KPI Card 4 — Net Revenue Churn
    net_revenue_churn: KPICardValue
    # value_display  = "1.2%"
    # delta_display  = "0.3%"
    # delta_label    = "vs last month"
    # delta_positive = False (churn increase is bad)

    # Alert Banner (null if no failing payments)
    failing_payments: Optional[FailingPaymentsBanner] = None

    # Snapshot metadata
    data_as_of: Optional[date] = None     # date of the latest snapshot used
    is_live:    bool = False               # True = computed live (no snapshot yet)


# =============================================================================
# REVENUE TREND CHART — GET /admin/revenue/trend
# Powers the line chart (MRR actual + Target dashed line)
# =============================================================================

class RevenueTrendPoint(BaseModel):
    """
    One month data point on the Revenue Trend chart.
    X-axis = month label ("Jan", "Feb"...), Y-axis = MRR cents.
    """
    month_label:        str   # "Jan", "Feb", ..., "Dec"
    month_date:         str   # "2026-01" — for frontend charting libraries
    mrr_cents:          int   # actual MRR for this month
    mrr_display:        str   # "$80K"
    target_mrr_cents:   Optional[int] = None   # null if no target set for this month
    target_mrr_display: Optional[str] = None   # "$90K"


class RevenueTrendResponse(BaseModel):
    """
    GET /admin/revenue/trend
    Powers the Revenue Trend line chart on ADMIN-08.
    Returns actual MRR + optional Target line for each month.
    """
    data_points:    List[RevenueTrendPoint]
    period_months:  int = 12
    # Y-axis bounds for chart rendering
    y_axis_max_cents:  int = 0   # chart max (rounded up to nearest $20K)
    y_axis_step_cents: int = 0   # chart grid step (e.g. 20000 cents = $20K)


# =============================================================================
# PLAN DISTRIBUTION DONUT — GET /admin/revenue/plan-distribution
# Powers the donut chart: Enterprise 45% / Professional 35% / Starter 20%
# =============================================================================

class PlanDistributionSlice(BaseModel):
    """
    One slice in the Plan Distribution donut chart.
    Example: Enterprise → 45% → $56,025 MRR
    """
    plan_name:      str    # "Enterprise"
    plan_slug:      str    # "enterprise"
    mrr_cents:      int    # 5602500 = $56,025
    mrr_display:    str    # "$56K"
    percentage:     float  # 45.0 (%)
    color:          str    # "#764ba2" — hex color for the donut slice


class PlanDistributionResponse(BaseModel):
    """
    GET /admin/revenue/plan-distribution
    Powers the Plan Distribution donut chart.
    """
    slices:         List[PlanDistributionSlice]
    total_mrr_cents: int    # sum of all slices — shown in donut center "$124.5K"
    total_mrr_display: str  # "$124.5K"


# =============================================================================
# RECENT TRANSACTIONS TABLE — GET /admin/revenue/transactions
# Powers the "Recent Transactions" table at bottom-left of ADMIN-08
# Columns: CUSTOMER | AMOUNT | PLAN | DATE | STATUS
# =============================================================================

class TransactionStatusBadge(BaseModel):
    """
    The colored badge in the STATUS column.
    Maps invoice status → display label + color scheme.
    """
    status:     str   # "paid" | "failed" | "pending" | "refunded"
    label:      str   # "Success" | "Failed" | "Pending" | "Refunded"
    color:      str   # "green" | "red" | "yellow" | "gray"
    # Frontend uses these to pick the badge style


class TransactionRow(BaseModel):
    """
    One row in the Recent Transactions table.
    Shows: avatar initials + customer name + email | amount | plan | date | status badge
    """
    invoice_id:       uuid.UUID
    invoice_number:   str              # "VF-INV-2024-00001" (internal, not shown by default)

    # CUSTOMER column — avatar initials + name + email
    user_id:          uuid.UUID
    user_name:        str              # "Acme Corp" | "Sarah Jenkins"
    user_email:       str              # "acme@example.com"
    avatar_initials:  str              # "Ac" | "Gl" | "Ne" — first 2 chars of name
    avatar_color:     str              # "#e0e7ff" — bg color for initials box (deterministic)

    # AMOUNT column
    amount_cents:     int              # 89900 = $899.00
    amount_display:   str              # "$899.00"

    # PLAN column
    plan_name:        str              # "Enterprise" | "Professional" | "Starter"
    plan_slug:        str              # "enterprise"

    # DATE column
    transaction_date: datetime         # Oct 24, 2026
    date_display:     str              # "Oct 24, 2026"

    # STATUS column
    status:           TransactionStatusBadge

    # For "Review Failing Payments" action
    failure_code:     Optional[str] = None    # "card_expired" | "insufficient_funds"
    stripe_invoice_id: Optional[str] = None


class RecentTransactionsResponse(BaseModel):
    """
    GET /admin/revenue/transactions
    Powers the Recent Transactions table.
    Paginated to support "View All" link.
    """
    items:      List[TransactionRow]
    total:      int
    page:       int = 1
    page_size:  int = 10
    total_pages: int = 1


# =============================================================================
# TRIAL CONVERSIONS BAR CHART — GET /admin/revenue/trial-conversions
# Powers the grouped bar chart: Conversion vs Churn over 6 months
# X-axis: May Jun Jul Aug Sep Oct
# Y-axis: 0 / 50 / 100 / 150
# =============================================================================

class TrialConversionsPoint(BaseModel):
    """
    One month's trial data — one group of bars on the chart.
    """
    month_label:            str   # "May", "Jun", ..., "Oct"
    month_date:             str   # "2026-05"
    new_trials:             int   # total bar height
    converted_trials:       int   # solid/darker bar portion
    churned_trials:         int   # lighter/greyed bar portion
    conversion_rate_pct:    float # converted / new_trials * 100


class TrialConversionsResponse(BaseModel):
    """
    GET /admin/revenue/trial-conversions
    Powers the Trial Conversions bar chart.
    """
    data_points:        List[TrialConversionsPoint]
    period_months:      int = 6
    # Totals for the period (summary above chart)
    total_new_trials:       int = 0
    total_converted:        int = 0
    total_churned:          int = 0
    avg_conversion_rate_pct: float = 0.0


# =============================================================================
# FAILING PAYMENTS DETAIL — GET /admin/revenue/failing-payments
# Powers the "Review Failing Payments" button detail view
# =============================================================================

class FailingPaymentRow(BaseModel):
    """
    One row in the failing payments review list.
    Shown when admin clicks "Review Failing Payments" button.
    """
    invoice_id:          uuid.UUID
    invoice_number:      str

    # Customer
    user_id:             uuid.UUID
    user_name:           str
    user_email:          str
    avatar_initials:     str

    # Payment details
    amount_cents:        int
    amount_display:      str
    plan_name:           str
    attempt_count:       int       # how many retries so far
    next_attempt_at:     Optional[datetime]   # when Stripe will retry
    failed_at:           Optional[datetime]   # when it first failed

    # Failure reason
    failure_code:        Optional[str]   # "card_expired"
    failure_label:       Optional[str]   # "Expired Card"

    # MRR at risk for this subscription
    mrr_at_risk_cents:   int
    mrr_at_risk_display: str

    # Stripe direct link for admin action
    stripe_invoice_id:   Optional[str]


class FailingPaymentsDetailResponse(BaseModel):
    """
    GET /admin/revenue/failing-payments
    Full list of failing payments for the Review modal.
    """
    items:           List[FailingPaymentRow]
    total:           int
    total_mrr_at_risk_cents:   int
    total_mrr_at_risk_display: str
    page:      int = 1
    page_size: int = 20
    total_pages: int = 1


# =============================================================================
# REVENUE TARGETS — POST + GET /admin/revenue/targets
# Admin sets the target MRR per month (Target dashed line on Revenue Trend chart)
# =============================================================================

class RevenueTargetCreate(BaseModel):
    """
    POST /admin/revenue/targets
    Admin sets the MRR target for a specific month.
    """
    target_month:       date  = Field(
        ...,
        description="First day of the target month: 2026-01-01, 2026-02-01, etc."
    )
    target_mrr_cents:   int   = Field(..., gt=0, description="Target MRR in cents. 12000000 = $120,000")
    notes:              Optional[str] = Field(None, max_length=500)

    @field_validator("target_month")
    @classmethod
    def must_be_first_of_month(cls, v: date) -> date:
        """Enforce that target_month is always the 1st day of a month."""
        if v.day != 1:
            # Auto-normalize to first of month instead of raising error
            from datetime import date as dt
            return dt(v.year, v.month, 1)
        return v


class RevenueTargetUpdate(BaseModel):
    """PATCH /admin/revenue/targets/{id}"""
    target_mrr_cents:  Optional[int]  = Field(None, gt=0)
    notes:             Optional[str]  = Field(None, max_length=500)


class RevenueTargetResponse(BaseModel):
    """One month's target — shown as dashed line point on Revenue Trend chart."""
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    target_month:        date
    target_month_label:  str = ""          # "January 2026" — set in service
    target_mrr_cents:    int
    target_mrr_display:  str = ""          # "$120,000" — set in service
    notes:               Optional[str]
    created_by:          Optional[uuid.UUID]
    created_at:          datetime
    updated_at:          datetime


class RevenueTargetListResponse(BaseModel):
    """
    GET /admin/revenue/targets
    Returns all targets — frontend uses this to draw the dashed Target line.
    """
    items:  List[RevenueTargetResponse]
    total:  int


# =============================================================================
# EXPORT REPORT — GET /admin/revenue/export
# Powers the "Export Report" button in the header
# =============================================================================

class ExportReportRequest(BaseModel):
    """
    Query params for GET /admin/revenue/export
    Passed as query string: ?format=csv&period=last_12_months&include_transactions=true
    """
    format:                 Literal["csv", "json"] = "csv"
    period:                 Literal["this_month", "last_12_months", "quarter", "custom"] = "last_12_months"
    date_from:              Optional[date] = None
    date_to:                Optional[date] = None
    include_transactions:   bool = True
    include_kpi_summary:    bool = True
    include_plan_breakdown: bool = True


# =============================================================================
# FULL DASHBOARD RESPONSE — GET /admin/revenue/dashboard/full
# Optional: single endpoint returning ALL sections in one call
# Reduces waterfalling for dashboard initial load
# =============================================================================

class RevenueDashboardFullResponse(BaseModel):
    """
    GET /admin/revenue/dashboard/full
    Returns every section of ADMIN-08 in one API call.
    Frontend can also call individual endpoints if it needs separate loading states.
    """
    kpi:               RevenueDashboardKPIResponse
    trend:             RevenueTrendResponse
    plan_distribution: PlanDistributionResponse
    transactions:      RecentTransactionsResponse
    trial_conversions: TrialConversionsResponse
    # failing_payments is included in kpi.failing_payments for banner
    # targets are included in trend.data_points as target_mrr_cents
    generated_at:      datetime
