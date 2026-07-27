"""
app/schemas/subscription.py

Pydantic v2 schemas for Admin-07 Subscription & Pricing Control screen.

Covers every UI component:
  - 4 KPI stat cards (revenue, active, trial, churned)
  - Plan cards grid with subscriber counts
  - Subscriber list table with filters/search/pagination
  - Coupon management table
  - Revenue analytics (MRR chart, plan distribution)
  - All create/update/toggle actions
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# ENUMS (mirrored from models)
# =============================================================================

SubscriptionStatus = Literal[
    "trialing", "active", "past_due",
    "cancelled", "paused", "expired", "unpaid"
]

BillingCycle = Literal["monthly", "annual", "lifetime"]

CouponDiscountType = Literal["percentage", "fixed_amount"]

InvoiceStatus = Literal[
    "draft", "open","pending","failed", "paid", "void", "uncollectible", "refunded"
]


# =============================================================================
# ── PLAN SCHEMAS ─────────────────────────────────────────────────────────────
# =============================================================================

class PlanFeatureCreate(BaseModel):
    feature_text:   str  = Field(..., max_length=300)
    is_included:    bool = True
    sort_order:     int  = 0
    is_highlighted: bool = False


class PlanFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    plan_id:        uuid.UUID
    feature_text:   str
    is_included:    bool
    sort_order:     int
    is_highlighted: bool


class SubscriptionPlanCreate(BaseModel):
    """POST /admin/subscription-plans — 'Add New Plan' button"""
    name:                    str           = Field(..., max_length=100)
    slug:                    str           = Field(..., max_length=50,
                                                   description="Unique slug e.g. 'professional'. Never change after creation.")
    description:             Optional[str] = Field(None, max_length=500)
    price_monthly_cents:     int           = Field(0, ge=0,
                                                   description="Monthly price in cents. 2900 = $29.00")
    price_annual_cents:      int           = Field(0, ge=0,
                                                   description="Annual price in cents. 29000 = $290.00")
    currency:                str           = Field("USD", max_length=3)
    trial_days:              int           = Field(0, ge=0)
    max_applications:        Optional[int] = Field(None, ge=1,
                                                   description="null = unlimited")
    max_documents:           Optional[int] = Field(None, ge=1)
    max_messages:            Optional[int] = Field(None, ge=1)
    stripe_product_id:       Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_annual:  Optional[str] = None
    is_active:               bool          = True
    is_public:               bool          = True
    is_featured:             bool          = False
    display_order:           int           = 0
    highlight_color:         Optional[str] = Field(None, max_length=7,
                                                   description="Hex color e.g. '#5B6CF6'")
    features:                List[PlanFeatureCreate] = []

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower().strip().replace(" ", "-")

    @field_validator("highlight_color")
    @classmethod
    def valid_hex(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("#"):
            raise ValueError("highlight_color must be a hex color starting with #")
        return v


class SubscriptionPlanUpdate(BaseModel):
    """PATCH /admin/subscription-plans/{id} — 'Edit Plan' button"""
    name:                    Optional[str] = Field(None, max_length=100)
    description:             Optional[str] = Field(None, max_length=500)
    price_monthly_cents:     Optional[int] = Field(None, ge=0)
    price_annual_cents:      Optional[int] = Field(None, ge=0)
    trial_days:              Optional[int] = Field(None, ge=0)
    max_applications:        Optional[int] = Field(None, ge=1)
    max_documents:           Optional[int] = Field(None, ge=1)
    max_messages:            Optional[int] = Field(None, ge=1)
    stripe_product_id:       Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_annual:  Optional[str] = None
    is_active:               Optional[bool] = None
    is_public:               Optional[bool] = None
    is_featured:             Optional[bool] = None
    display_order:           Optional[int]  = None
    highlight_color:         Optional[str]  = Field(None, max_length=7)
    # slug and currency are intentionally NOT updatable


class PlanToggle(BaseModel):
    """PATCH /admin/subscription-plans/{id}/toggle — active badge switch"""
    is_active: bool


class SubscriptionPlanResponse(BaseModel):
    """Single plan card response — includes live subscriber count"""
    model_config = ConfigDict(from_attributes=True)

    id:                      uuid.UUID
    name:                    str
    slug:                    str
    description:             Optional[str]
    price_monthly_cents:     int
    price_annual_cents:      int
    # Computed display fields (set by service)
    price_monthly_display:   str = ""     # "$29.00"
    price_annual_display:    str = ""     # "$290.00"
    price_annual_monthly_equiv: str = ""  # "$24.17/mo" (annual / 12)
    currency:                str
    trial_days:              int
    max_applications:        Optional[int]
    max_documents:           Optional[int]
    max_messages:            Optional[int]
    stripe_product_id:       Optional[str]
    stripe_price_id_monthly: Optional[str]
    stripe_price_id_annual:  Optional[str]
    is_active:               bool
    is_public:               bool
    is_featured:             bool
    display_order:           int
    highlight_color:         Optional[str]
    # Live counts (joined from user_subscriptions)
    active_subscribers:      int = 0   # status = active
    trial_subscribers:       int = 0   # status = trialing
    total_subscribers:       int = 0   # all non-cancelled
    features:                List[PlanFeatureResponse] = []
    created_at:              datetime
    updated_at:              datetime


class SubscriptionPlanListResponse(BaseModel):
    """GET /admin/subscription-plans — plan cards grid"""
    items: List[SubscriptionPlanResponse]
    total: int


# =============================================================================
# ── SUBSCRIBER SCHEMAS ────────────────────────────────────────────────────────
# =============================================================================

class SubscriberListItem(BaseModel):
    """One row in the subscriber table"""
    model_config = ConfigDict(from_attributes=True)

    subscription_id:      uuid.UUID
    user_id:              uuid.UUID
    # User info (joined)
    user_name:            str           # "John Smith"
    user_email:           str
    user_role:            str           # "employee" | "hr" | "attorney"
    # Plan info
    plan_name:            str           # "Professional"
    plan_slug:            str
    # Subscription state
    status:               SubscriptionStatus
    billing_cycle:        BillingCycle
    current_period_start: Optional[datetime]
    current_period_end:   Optional[datetime]   # "Next billing date"
    trial_end:            Optional[datetime]
    cancel_at_period_end: bool
    # Amount
    amount_display:       str           # "$49.00/month"
    # Coupon
    coupon_code:          Optional[str] # applied coupon code
    discount_display:     Optional[str] # "20% off"
    # Payment
    payment_processor:    str
    stripe_subscription_id: Optional[str]
    assigned_by_admin:    bool
    created_at:           datetime


class SubscriberListResponse(BaseModel):
    """GET /admin/subscriptions — subscriber table with pagination"""
    items:        List[SubscriberListItem]
    total:        int
    page:         int
    page_size:    int
    total_pages:  int


class SubscriberDetail(SubscriberListItem):
    """GET /admin/subscriptions/{id} — subscriber detail panel"""
    # Invoice history
    invoices:     List["InvoiceListItem"] = []
    # Admin override fields
    admin_notes:  Optional[str]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]


class AssignPlanRequest(BaseModel):
    """
    POST /admin/subscriptions/assign
    Admin manually assigns a plan to a user (no Stripe payment)
    Used for app_admin accounts, beta testers, comped plans
    """
    user_id:       uuid.UUID
    plan_id:       uuid.UUID
    billing_cycle: BillingCycle = "monthly"
    admin_notes:   Optional[str] = Field(None, max_length=500)
    trial_days:    int           = Field(0, ge=0,
                                         description="Override trial days for this user")


class ChangePlanRequest(BaseModel):
    """
    PATCH /admin/subscriptions/{id}/change-plan
    Admin changes a subscriber's plan
    """
    new_plan_id:   uuid.UUID
    billing_cycle: Optional[BillingCycle] = None
    admin_notes:   Optional[str]          = Field(None, max_length=500)


class CancelSubscriptionRequest(BaseModel):
    """
    PATCH /admin/subscriptions/{id}/cancel
    Admin cancels a subscription
    """
    cancel_immediately:   bool   = False
    # False = cancel at period end | True = cancel right now
    cancellation_reason:  Optional[str] = Field(None, max_length=500)


# =============================================================================
# ── COUPON SCHEMAS ────────────────────────────────────────────────────────────
# =============================================================================

class CouponCreate(BaseModel):
    """POST /admin/coupons — 'Create Coupon' button"""
    code:                   str             = Field(..., max_length=50,
                                                    description="Uppercase code: SAVE20")
    name:                   str             = Field(..., max_length=200)
    description:            Optional[str]   = Field(None, max_length=500)
    discount_type:          CouponDiscountType
    discount_value:         int             = Field(..., gt=0,
                                                    description="20 = 20% | 1000 = $10.00 in cents")
    valid_from:             datetime
    valid_until:            Optional[datetime] = None
    max_uses:               Optional[int]   = Field(None, ge=1)
    applicable_plan_slugs:  Optional[str]   = Field(None,
                                                     description='JSON array: ["professional","enterprise"] or null for all plans')

    @field_validator("code")
    @classmethod
    def code_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("discount_value")
    @classmethod
    def validate_percentage_max(cls, v: int, info: Any) -> int:
        if hasattr(info, "data") and info.data.get("discount_type") == "percentage":
            if v > 100:
                raise ValueError("Percentage discount cannot exceed 100")
        return v


class CouponUpdate(BaseModel):
    """PATCH /admin/coupons/{id}"""
    name:                  Optional[str]      = Field(None, max_length=200)
    description:           Optional[str]      = Field(None, max_length=500)
    valid_until:           Optional[datetime] = None
    max_uses:              Optional[int]      = Field(None, ge=1)
    applicable_plan_slugs: Optional[str]      = None
    is_active:             Optional[bool]     = None
    # code, discount_type, discount_value are intentionally NOT updatable


class CouponToggle(BaseModel):
    """PATCH /admin/coupons/{id}/toggle"""
    is_active: bool


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    uuid.UUID
    code:                  str
    name:                  str
    description:           Optional[str]
    discount_type:         str
    discount_value:        int
    discount_display:      str = ""    # "20% off" or "$10.00 off" — computed
    valid_from:            datetime
    valid_until:           Optional[datetime]
    max_uses:              Optional[int]
    uses_count:            int
    remaining_uses:        Optional[int] = None  # max_uses - uses_count, null if unlimited
    applicable_plan_slugs: Optional[str]
    stripe_coupon_id:      Optional[str]
    stripe_promo_code_id:  Optional[str]
    is_active:             bool
    is_expired:            bool = False   # computed: valid_until < now
    is_exhausted:          bool = False   # computed: uses_count >= max_uses
    total_savings_cents:   int = 0        # NEW — sum of discounts actually redeemed
    total_savings_display: str = ""       # NEW — "$1,834.00"
    created_at:            datetime
    updated_at:            datetime


class CouponListResponse(BaseModel):
    items:      List[CouponResponse]
    total:      int
    page:       int
    page_size:  int
    total_pages: int


class ValidateCouponRequest(BaseModel):
    """
    POST /subscriptions/validate-coupon
    Called when user enters coupon code at checkout
    """
    code:    str
    plan_id: uuid.UUID


class ValidateCouponResponse(BaseModel):
    valid:            bool
    coupon_id:        Optional[uuid.UUID]
    discount_type:    Optional[str]
    discount_value:   Optional[int]
    discount_display: Optional[str]   # "20% off" — shown in checkout UI
    message:          str             # "Code applied!" or error reason


# =============================================================================
# ── INVOICE SCHEMAS ───────────────────────────────────────────────────────────
# =============================================================================

class InvoiceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                  uuid.UUID
    invoice_number:      str
    subscription_id:     uuid.UUID
    # User (joined)
    user_name:           str
    user_email:          str
    plan_name:           str
    # Amounts
    total_cents:         int
    total_display:       str = ""     # "$29.00"
    currency:            str
    # Status
    status:              InvoiceStatus
    billing_period_start: Optional[datetime]
    billing_period_end:   Optional[datetime]
    paid_at:             Optional[datetime]
    # Links
    invoice_pdf_url:     Optional[str]
    stripe_invoice_id:   Optional[str]
    created_at:          datetime


class InvoiceListResponse(BaseModel):
    items:      List[InvoiceListItem]
    total:      int
    page:       int
    page_size:  int
    total_pages: int


# =============================================================================
# ── STATS / ANALYTICS SCHEMAS ─────────────────────────────────────────────────
# =============================================================================

class SubscriptionStats(BaseModel):
    """
    Powers the 4 KPI cards at top of screen:
      Card 1 → Monthly Recurring Revenue  "$12,450"
      Card 2 → Active Subscribers         "248"
      Card 3 → Trial Users                "34"
      Card 4 → Churned This Month         "12"
    """
    # Card 1 — Revenue
    mrr_cents:            int     # Monthly Recurring Revenue in cents
    mrr_display:          str     # "$12,450.00"
    arr_cents:            int     # Annual Run Rate = MRR * 12
    arr_display:          str     # "$149,400.00"
    mrr_change_pct:       Optional[float]  # +12.5 (vs last month)

    # Card 2 — Active subscribers
    active_subscribers:   int
    active_change_pct:    Optional[float]

    # Card 3 — Trials
    trial_subscribers:    int
    trial_change_pct:     Optional[float]

    # Card 4 — Churn
    churned_this_month:   int
    churn_rate_pct:       Optional[float]  # churned / (start of month active) * 100

    # Supporting totals (used in plan breakdown section)
    total_subscribers:    int    # all non-cancelled
    past_due_count:       int
    paused_count:         int


class PlanDistributionItem(BaseModel):
    """One bar/slice in the plan distribution chart"""
    plan_name:          str
    plan_slug:          str
    subscriber_count:   int
    percentage:         float         # 45.2 (%)
    mrr_cents:          int
    mrr_display:        str


class MRRDataPoint(BaseModel):
    """One point on the MRR trend chart"""
    date:         str   # "2024-01" — monthly grain
    mrr_cents:    int
    mrr_display:  str
    new_mrr:      int   # from new subscribers that month
    churned_mrr:  int   # lost from cancellations


class RevenueAnalyticsResponse(BaseModel):
    """
    GET /admin/subscriptions/analytics
    Powers the revenue chart + plan distribution chart
    """
    mrr_trend:          List[MRRDataPoint]         # last 12 months
    plan_distribution:  List[PlanDistributionItem]
    period_months:      int = 12


# =============================================================================
# ── SELF-SERVICE "MY SUBSCRIPTION" (any authenticated role) ─────────────────
# NEW — supports HR / Lawyer / Employee / Student viewing their own plan
# =============================================================================

class MyQuotaItem(BaseModel):
    used:         int
    limit:        Optional[int]   # null = unlimited
    remaining:    Optional[int]
    is_unlimited: bool


class MyFeatureItem(BaseModel):
    feature_text: str
    is_included:  bool


class MySubscriptionResponse(BaseModel):
    """GET /subscriptions/me"""
    has_subscription:     bool
    subscription_id:      Optional[uuid.UUID] = None
    plan_id:               Optional[uuid.UUID] = None
    plan_name:             Optional[str] = None
    plan_slug:              Optional[str] = None
    status:                 Optional[str] = None
    billing_cycle:          Optional[str] = None
    current_period_start:   Optional[datetime] = None
    current_period_end:     Optional[datetime] = None
    trial_end:              Optional[datetime] = None
    cancel_at_period_end:   Optional[bool] = None
    features:               List[MyFeatureItem] = []
    usage:                  Optional[Dict[str, MyQuotaItem]] = None


class MyInvoiceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                   uuid.UUID
    invoice_number:       str
    plan_name:            str
    total_cents:          int
    total_display:        str
    currency:             str
    status:               str
    billing_period_start: Optional[datetime]
    billing_period_end:   Optional[datetime]
    paid_at:              Optional[datetime]
    invoice_pdf_url:      Optional[str]
    created_at:           datetime


class MyInvoiceListResponse(BaseModel):
    items:       List[MyInvoiceItem]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# =============================================================================
# ── RECENT ACTIVITY FEED (admin) — NEW ────────────────────────────────────────
# =============================================================================

class RecentActivityItem(BaseModel):
    id:            uuid.UUID
    action:        str
    actor_name:    str
    resource_type: str
    resource_id:   Optional[uuid.UUID]
    description:   Optional[str]
    severity:      str
    created_at:    datetime


class RecentActivityResponse(BaseModel):
    items: List[RecentActivityItem]


# =============================================================================
# ── PAYMENT GATEWAY CONFIGURATION (admin only) — NEW ──────────────────────────
# =============================================================================

class PaymentGatewayUpsert(BaseModel):
    """
    PATCH /admin/payment-gateways/{gateway}
    `credentials` is encrypted server-side before storage — never returned.
    """
    credentials:                  Optional[Dict[str, Any]] = None
    is_enabled:                   Optional[bool] = None
    transaction_fee_percent_bps:  Optional[int]  = Field(None, description="290 = 2.90%")
    transaction_fee_fixed_cents:  Optional[int]  = None
    settlement_days_min:          Optional[int]  = None
    settlement_days_max:          Optional[int]  = None
    supported_methods:            Optional[str]  = None


class PaymentGatewayToggle(BaseModel):
    is_enabled: bool


class PaymentGatewayResponse(BaseModel):
    gateway:                   str
    is_connected:              bool
    is_enabled:                bool
    transaction_fee_display:   Optional[str] = None
    settlement_days_display:   Optional[str] = None
    supported_methods:         Optional[str] = None
    connected_at:              Optional[datetime] = None


class PaymentGatewayListResponse(BaseModel):
    items: List[PaymentGatewayResponse]
