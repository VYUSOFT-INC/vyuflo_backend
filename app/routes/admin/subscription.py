"""
app/api/v1/admin_subscriptions.py

Admin-07 Subscription & Pricing Control — all endpoints.

Mount in main.py:
    from app.api.v1.admin_subscriptions import subscription_router
    app.include_router(subscription_router, prefix="/api/v1", tags=["Admin — Subscriptions"])

═══════════════════════════════════════════════════════════════════════
ENDPOINT MAP  →  UI Component
═══════════════════════════════════════════════════════════════════════

── Stats (KPI cards) ───────────────────────────────────────────────────
GET  /admin/subscriptions/stats               → 4 KPI cards at top

── Plan Management ─────────────────────────────────────────────────────
GET  /admin/subscription-plans                → Plan cards grid
POST /admin/subscription-plans                → "Add New Plan" button
GET  /admin/subscription-plans/{id}           → Plan detail panel
PATCH /admin/subscription-plans/{id}          → "Edit Plan" button
PATCH /admin/subscription-plans/{id}/toggle   → Active/Inactive toggle

── Subscriber Table ────────────────────────────────────────────────────
GET  /admin/subscriptions                     → Subscriber list table
GET  /admin/subscriptions/export              → "Export" button  ← BEFORE /{id}
GET  /admin/subscriptions/{id}                → Subscriber detail panel
POST /admin/subscriptions/assign              → Admin manual plan assign
PATCH /admin/subscriptions/{id}/change-plan  → "Change Plan" action
PATCH /admin/subscriptions/{id}/cancel       → "Cancel" action

── Coupon Management ───────────────────────────────────────────────────
GET  /admin/coupons                           → Coupon list table
POST /admin/coupons                           → "Create Coupon" button
GET  /admin/coupons/{id}                      → Coupon detail
PATCH /admin/coupons/{id}                     → Edit coupon
PATCH /admin/coupons/{id}/toggle              → Active/Inactive toggle

── Invoice / Billing History ───────────────────────────────────────────
GET  /admin/invoices                          → Invoice list table
GET  /admin/invoices/{id}                     → Invoice detail

── Analytics ───────────────────────────────────────────────────────────
GET  /admin/subscriptions/analytics           → MRR chart + plan distribution

── Public (all authenticated users) ────────────────────────────────────
GET  /subscription-plans                      → Public pricing page
POST /subscriptions/validate-coupon           → Coupon validation at checkout

NOTE ON ROUTE ORDER — critical FastAPI rule:
  /stats, /export, /analytics, /assign are declared BEFORE /{id}
  to prevent FastAPI treating those strings as UUID path parameters.
"""
from __future__ import annotations

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import Current_User, DBSession
from app.core.core_permissions import PermissionChecker
from app.schemas.admin.subscription import (
    AssignPlanRequest,
    CancelSubscriptionRequest,
    ChangePlanRequest,
    CouponCreate,
    CouponListResponse,
    CouponResponse,
    CouponToggle,
    CouponUpdate,
    InvoiceListResponse,
    PaymentGatewayToggle,       # NEW — add to app/schemas/admin/subscription.py
    PaymentGatewayUpsert,       # NEW — add to app/schemas/admin/subscription.py
    PlanToggle,
    RevenueAnalyticsResponse,
    SubscriberDetail,
    SubscriberListResponse,
    SubscriptionPlanCreate,
    SubscriptionPlanListResponse,
    SubscriptionPlanResponse,
    SubscriptionPlanUpdate,
    SubscriptionStats,
    ValidateCouponRequest,
    ValidateCouponResponse,
)
from app.services.admin.subscription_service import (
    service_admin_assign_plan,
    service_cancel_subscription,
    service_change_plan,
    service_create_coupon,
    service_create_plan,
    service_export_subscribers,
    service_get_my_subscription,
    service_get_plan,
    service_get_recent_activity,
    service_get_revenue_analytics,
    service_get_subscription,
    service_get_subscription_stats,
    service_list_coupons,
    service_list_invoices,
    service_list_payment_gateways,
    service_list_plans,
    service_list_subscribers,
    service_toggle_coupon,
    service_toggle_payment_gateway,
    service_toggle_plan,
    service_update_plan,
    service_upsert_payment_gateway,
    service_validate_coupon,
    _write_audit_log,
)

subscription_router = APIRouter()

# ── Permission guards ─────────────────────────────────────────────────────────
_admin_only   = PermissionChecker("subscriptions.manage")
_view_billing = PermissionChecker(["subscriptions.manage", "subscriptions.view"])


# =============================================================================
# ── STATS (KPI CARDS) ────────────────────────────────────────────────────────
# GET /admin/subscriptions/stats
# MUST be before /admin/subscriptions/{id}
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions/stats",
    response_model=SubscriptionStats,
    status_code=status.HTTP_200_OK,
    summary="Subscription KPI stats",
    description=(
        "Returns the 4 KPI card values at the top of the Subscriptions screen: "
        "MRR, active subscribers, trial users, churned this month. "
        "Recommend 60-second cache in production."
    ),
)
async def get_subscription_stats(
    db: DBSession,
    _:  Current_User = _view_billing,
) -> SubscriptionStats:
    data = await service_get_subscription_stats(db)
    return SubscriptionStats(**data)


# =============================================================================
# ── ANALYTICS ────────────────────────────────────────────────────────────────
# GET /admin/subscriptions/analytics
# MUST be before /admin/subscriptions/{id}
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions/analytics",
    response_model=RevenueAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Revenue analytics — MRR trend + plan distribution",
    description=(
        "Powers the revenue chart (MRR trend last N months) "
        "and the plan distribution pie/bar chart."
    ),
)
async def get_revenue_analytics(
    db:             DBSession,
    _:              Current_User = _view_billing,
    period_months:  int = Query(12, ge=1, le=24,
                                description="Number of months to include in MRR trend"),
) -> RevenueAnalyticsResponse:
    data = await service_get_revenue_analytics(db, period_months=period_months)
    return RevenueAnalyticsResponse(**data)


# =============================================================================
# ── SUBSCRIBER EXPORT ─────────────────────────────────────────────────────────
# GET /admin/subscriptions/export
# MUST be before /admin/subscriptions/{id}
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions/export",
    status_code=status.HTTP_200_OK,
    summary="Export subscribers as CSV",
    description="Downloads a CSV of all subscribers matching optional filters.",
)
async def export_subscribers(
    db:      DBSession,
    _:       Current_User = _admin_only,
    plan_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> StreamingResponse:
    csv_content = await service_export_subscribers(
        db, plan_id=plan_id, status=status_filter
    )

    def _iter():
        yield csv_content

    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=subscribers_export.csv"
        },
    )


# =============================================================================
# ── ADMIN ASSIGN PLAN ─────────────────────────────────────────────────────────
# POST /admin/subscriptions/assign
# MUST be before /admin/subscriptions/{id}
# =============================================================================

@subscription_router.post(
    "/admin/subscriptions/assign",
    status_code=status.HTTP_201_CREATED,
    summary="Admin manually assign a plan to a user",
    description=(
        "Assigns a plan without Stripe payment. "
        "Used for app_admin accounts, beta testers, comped plans. "
        "Cancels any existing active subscription first."
    ),
)
async def admin_assign_plan(
    payload:      AssignPlanRequest,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> dict:
    sub = await service_admin_assign_plan(db, payload, current_user.user_id)
    return {
        "message":         "Plan assigned successfully.",
        "subscription_id": str(sub.id),
        "user_id":         str(sub.user_id),
        "plan_id":         str(sub.plan_id),
        "status":          sub.status,
    }


# =============================================================================
# ── SUBSCRIBER LIST ───────────────────────────────────────────────────────────
# GET /admin/subscriptions
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions",
    response_model=SubscriberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all subscribers",
    description=(
        "Paginated table of all subscriptions. "
        "Search by user name/email. "
        "Filter by plan, status, date range. "
        "Sort by created_at, status, plan name, user name, period end."
    ),
)
async def list_subscribers(
    db:            DBSession,
    _:             Current_User = _view_billing,
    search:        Optional[str]       = Query(None, min_length=1),
    plan_id:       Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str]       = Query(None, alias="status",
                                                description="trialing|active|past_due|cancelled|paused|expired"),
    date_from:     Optional[str]       = Query(None, description="ISO datetime e.g. 2024-01-01"),
    date_to:       Optional[str]       = Query(None, description="ISO datetime e.g. 2024-12-31"),
    sort_by:       str                 = Query("created_at",
                                               description="created_at|status|plan|user|period_end"),
    sort_order:    str                 = Query("desc", pattern="^(asc|desc)$"),
    page:          int                 = Query(1,  ge=1),
    page_size:     int                 = Query(20, ge=1, le=100),
) -> SubscriberListResponse:
    from datetime import datetime

    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to)   if date_to   else None

    items, total = await service_list_subscribers(
        db,
        search     = search,
        plan_id    = plan_id,
        status     = status_filter,
        date_from  = df,
        date_to    = dt,
        sort_by    = sort_by,
        sort_order = sort_order,
        page       = page,
        page_size  = page_size,
    )

    total_pages = max(1, math.ceil(total / page_size))

    from app.schemas.admin.subscription import SubscriberListItem
    response_items = []
    for sub in items:
        item = SubscriberListItem(
            subscription_id      = sub.id,
            user_id              = sub.user_id,
            user_name            = getattr(sub, "_user_name", ""),
            user_email           = getattr(sub, "_user_email", ""),
            user_role            = getattr(sub, "_user_role", "user"),
            plan_name            = getattr(sub, "_plan_name", ""),
            plan_slug            = getattr(sub, "_plan_slug", ""),
            status               = sub.status,
            billing_cycle        = sub.billing_cycle,
            current_period_start = sub.current_period_start,
            current_period_end   = sub.current_period_end,
            trial_end            = sub.trial_end,
            cancel_at_period_end = sub.cancel_at_period_end,
            amount_display       = getattr(sub, "_amount_display", ""),
            coupon_code          = getattr(sub, "_coupon_code", None),
            discount_display     = getattr(sub, "_discount_display", None),
            payment_processor    = sub.payment_processor,
            stripe_subscription_id = sub.stripe_subscription_id,
            assigned_by_admin    = sub.assigned_by_admin,
            created_at           = sub.created_at,
        )
        response_items.append(item)

    return SubscriberListResponse(
        items       = response_items,
        total       = total,
        page        = page,
        page_size   = page_size,
        total_pages = total_pages,
    )


# =============================================================================
# ── SUBSCRIBER DETAIL ─────────────────────────────────────────────────────────
# GET /admin/subscriptions/{id}
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions/{subscription_id}",
    status_code=status.HTTP_200_OK,
    summary="Get subscriber detail",
    description="Full subscription detail including invoice history.",
)
async def get_subscription(
    subscription_id: uuid.UUID,
    db:              DBSession,
    _:               Current_User = _view_billing,
) -> dict:
    sub = await service_get_subscription(db, subscription_id)
    return {
        "id":                    str(sub.id),
        "user_id":               str(sub.user_id),
        "user_name":             getattr(sub, "_user_name", ""),
        "user_email":            getattr(sub, "_user_email", ""),
        "plan_id":               str(sub.plan_id),
        "plan_name":             getattr(sub, "_plan_name", ""),
        "status":                sub.status,
        "billing_cycle":         sub.billing_cycle,
        "current_period_start":  str(sub.current_period_start or ""),
        "current_period_end":    str(sub.current_period_end or ""),
        "trial_end":             str(sub.trial_end or ""),
        "cancel_at_period_end":  sub.cancel_at_period_end,
        "cancelled_at":          str(sub.cancelled_at or ""),
        "cancellation_reason":   sub.cancellation_reason,
        "payment_processor":     sub.payment_processor,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "assigned_by_admin":     sub.assigned_by_admin,
        "admin_notes":           sub.admin_notes,
        "created_at":            str(sub.created_at),
    }


# =============================================================================
# ── CHANGE PLAN ───────────────────────────────────────────────────────────────
# PATCH /admin/subscriptions/{id}/change-plan
# MUST be before PATCH /admin/subscriptions/{id}
# =============================================================================

@subscription_router.patch(
    "/admin/subscriptions/{subscription_id}/change-plan",
    status_code=status.HTTP_200_OK,
    summary="Change a subscriber's plan",
    description=(
        "Admin changes the plan for an existing subscriber. "
        "Updates the user's cached subscription_tier automatically."
    ),
)
async def change_plan(
    subscription_id: uuid.UUID,
    payload:         ChangePlanRequest,
    db:              DBSession,
    current_user:    Current_User,
    _:               Current_User = _admin_only,
) -> dict:
    sub = await service_change_plan(db, subscription_id, payload, current_user.user_id)
    return {
        "message":    "Plan changed successfully.",
        "subscription_id": str(sub.id),
        "new_plan_id":     str(sub.plan_id),
        "status":          sub.status,
    }


# =============================================================================
# ── CANCEL SUBSCRIPTION ───────────────────────────────────────────────────────
# PATCH /admin/subscriptions/{id}/cancel
# =============================================================================

@subscription_router.patch(
    "/admin/subscriptions/{subscription_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a subscription",
    description=(
        "Admin cancels a subscription. "
        "cancel_immediately=false (default) = cancel at period end. "
        "cancel_immediately=true = cancel right now, downgrade to free."
    ),
)
async def cancel_subscription(
    subscription_id: uuid.UUID,
    payload:         CancelSubscriptionRequest,
    db:              DBSession,
    current_user:    Current_User,
    _:               Current_User = _admin_only,
) -> dict:
    sub = await service_cancel_subscription(
        db, subscription_id, payload, current_user.user_id
    )
    return {
        "message":              "Subscription cancelled.",
        "subscription_id":      str(sub.id),
        "status":               sub.status,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "cancelled_at":         str(sub.cancelled_at or ""),
    }


# =============================================================================
# ── PLAN MANAGEMENT ───────────────────────────────────────────────────────────
# =============================================================================

@subscription_router.get(
    "/admin/subscription-plans",
    response_model=SubscriptionPlanListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all subscription plans",
    description="Returns all plan cards ordered by display_order, with live subscriber counts.",
)
async def list_plans(
    db: DBSession,
    _:  Current_User = _view_billing,
) -> SubscriptionPlanListResponse:
    plans = await service_list_plans(db)

    items = []
    for plan in plans:
        item = SubscriptionPlanResponse(
            id                       = plan.id,
            name                     = plan.name,
            slug                     = plan.slug,
            description              = plan.description,
            price_monthly_cents      = plan.price_monthly_cents,
            price_annual_cents       = plan.price_annual_cents,
            price_monthly_display    = getattr(plan, "_monthly_display", ""),
            price_annual_display     = getattr(plan, "_annual_display", ""),
            price_annual_monthly_equiv = getattr(plan, "_annual_monthly_equiv", ""),
            currency                 = plan.currency,
            trial_days               = plan.trial_days,
            max_applications         = plan.max_applications,
            max_documents            = plan.max_documents,
            max_messages             = plan.max_messages,
            stripe_product_id        = plan.stripe_product_id,
            stripe_price_id_monthly  = plan.stripe_price_id_monthly,
            stripe_price_id_annual   = plan.stripe_price_id_annual,
            is_active                = plan.is_active,
            is_public                = plan.is_public,
            is_featured              = plan.is_featured,
            display_order            = plan.display_order,
            highlight_color          = plan.highlight_color,
            active_subscribers       = getattr(plan, "_active_count", 0),
            trial_subscribers        = getattr(plan, "_trial_count", 0),
            total_subscribers        = getattr(plan, "_total_count", 0),
            features                 = [
                SubscriptionPlanResponse.model_fields  # handled below
                for _ in []  # populated next
            ],
            created_at               = plan.created_at,
            updated_at               = plan.updated_at,
        )
        # Populate features properly
        from app.schemas.admin.subscription import PlanFeatureResponse
        item.features = [
            PlanFeatureResponse(
                id             = f.id,
                plan_id        = f.plan_id,
                feature_text   = f.feature_text,
                is_included    = f.is_included,
                sort_order     = f.sort_order,
                is_highlighted = f.is_highlighted,
            )
            for f in sorted(plan.features, key=lambda x: x.sort_order)
        ]
        items.append(item)

    return SubscriptionPlanListResponse(items=items, total=len(items))


@subscription_router.post(
    "/admin/subscription-plans",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subscription plan",
    description="Creates a plan with features. 'Add New Plan' button.",
)
async def create_plan(
    payload:      SubscriptionPlanCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> SubscriptionPlanResponse:
    plan = await service_create_plan(db, payload, current_user.user_id)
    return SubscriptionPlanResponse.model_validate(plan)


@subscription_router.get(
    "/admin/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get plan detail",
)
async def get_plan(
    plan_id: uuid.UUID,
    db:      DBSession,
    _:       Current_User = _view_billing,
) -> SubscriptionPlanResponse:
    plan = await service_get_plan(db, plan_id)
    return SubscriptionPlanResponse.model_validate(plan)


@subscription_router.patch(
    "/admin/subscription-plans/{plan_id}/toggle",
    status_code=status.HTTP_200_OK,
    summary="Toggle plan active/inactive",
    description="Active badge switch on each plan card. Blocked if active subscribers exist.",
)
async def toggle_plan(
    plan_id:      uuid.UUID,
    payload:      PlanToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> dict:
    plan = await service_toggle_plan(db, plan_id, payload.is_active, current_user.user_id)
    return {
        "message":   f"Plan {'activated' if plan.is_active else 'deactivated'}.",
        "plan_id":   str(plan.id),
        "is_active": plan.is_active,
    }


@subscription_router.patch(
    "/admin/subscription-plans/{plan_id}",
    response_model=SubscriptionPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a subscription plan",
    description="Edit plan details. slug and currency are NOT updatable.",
)
async def update_plan(
    plan_id:      uuid.UUID,
    payload:      SubscriptionPlanUpdate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> SubscriptionPlanResponse:
    plan = await service_update_plan(db, plan_id, payload, current_user.user_id)
    return SubscriptionPlanResponse.model_validate(plan)


# =============================================================================
# ── COUPON MANAGEMENT ─────────────────────────────────────────────────────────
# =============================================================================

@subscription_router.get(
    "/admin/coupons",
    response_model=CouponListResponse,
    status_code=status.HTTP_200_OK,
    summary="List coupons",
    description="Paginated coupon list with search and active filter.",
)
async def list_coupons(
    db:            DBSession,
    _:             Current_User = _view_billing,
    search:        Optional[str]  = Query(None, min_length=1),
    is_active:     Optional[bool] = Query(None),
    page:          int            = Query(1,  ge=1),
    page_size:     int            = Query(20, ge=1, le=100),
) -> CouponListResponse:
    coupons, total = await service_list_coupons(
        db, search=search, is_active=is_active, page=page, page_size=page_size
    )
    total_pages = max(1, math.ceil(total / page_size))

    items = []
    for c in coupons:
        item = CouponResponse(
            id                    = c.id,
            code                  = c.code,
            name                  = c.name,
            description           = c.description,
            discount_type         = c.discount_type,
            discount_value        = c.discount_value,
            discount_display      = getattr(c, "_discount_display", ""),
            valid_from            = c.valid_from,
            valid_until           = c.valid_until,
            max_uses              = c.max_uses,
            uses_count            = c.uses_count,
            remaining_uses        = getattr(c, "_remaining", None),
            applicable_plan_slugs = c.applicable_plan_slugs,
            stripe_coupon_id      = c.stripe_coupon_id,
            stripe_promo_code_id  = c.stripe_promo_code_id,
            is_active             = c.is_active,
            is_expired            = getattr(c, "_is_expired", False),
            is_exhausted          = getattr(c, "_is_exhausted", False),
            created_at            = c.created_at,
            updated_at            = c.updated_at,
        )
        items.append(item)

    return CouponListResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@subscription_router.post(
    "/admin/coupons",
    response_model=CouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a coupon",
    description="'Create Coupon' button. Code is auto-uppercased.",
)
async def create_coupon(
    payload:      CouponCreate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> CouponResponse:
    coupon = await service_create_coupon(db, payload, current_user.user_id)
    return CouponResponse(
        id                    = coupon.id,
        code                  = coupon.code,
        name                  = coupon.name,
        description           = coupon.description,
        discount_type         = coupon.discount_type,
        discount_value        = coupon.discount_value,
        discount_display      = getattr(coupon, "_discount_display", ""),
        valid_from            = coupon.valid_from,
        valid_until           = coupon.valid_until,
        max_uses              = coupon.max_uses,
        uses_count            = coupon.uses_count,
        remaining_uses        = getattr(coupon, "_remaining", None),
        applicable_plan_slugs = coupon.applicable_plan_slugs,
        stripe_coupon_id      = coupon.stripe_coupon_id,
        stripe_promo_code_id  = coupon.stripe_promo_code_id,
        is_active             = coupon.is_active,
        is_expired            = False,
        is_exhausted          = False,
        created_at            = coupon.created_at,
        updated_at            = coupon.updated_at,
    )


@subscription_router.patch(
    "/admin/coupons/{coupon_id}/toggle",
    response_model=CouponResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle coupon active/inactive",
    description="Active switch on each coupon row.",
)
async def toggle_coupon(
    coupon_id:    uuid.UUID,
    payload:      CouponToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> CouponResponse:
    coupon = await service_toggle_coupon(
        db, coupon_id, payload.is_active, current_user.user_id
    )
    return CouponResponse(
        id                    = coupon.id,
        code                  = coupon.code,
        name                  = coupon.name,
        description           = coupon.description,
        discount_type         = coupon.discount_type,
        discount_value        = coupon.discount_value,
        discount_display      = getattr(coupon, "_discount_display", ""),
        valid_from            = coupon.valid_from,
        valid_until           = coupon.valid_until,
        max_uses              = coupon.max_uses,
        uses_count            = coupon.uses_count,
        remaining_uses        = getattr(coupon, "_remaining", None),
        applicable_plan_slugs = coupon.applicable_plan_slugs,
        stripe_coupon_id      = coupon.stripe_coupon_id,
        stripe_promo_code_id  = coupon.stripe_promo_code_id,
        is_active             = coupon.is_active,
        is_expired            = getattr(coupon, "_is_expired", False),
        is_exhausted          = getattr(coupon, "_is_exhausted", False),
        created_at            = coupon.created_at,
        updated_at            = coupon.updated_at,
    )


@subscription_router.patch(
    "/admin/coupons/{coupon_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a coupon",
    description="Edit coupon validity, usage limits, plan restrictions.",
)
async def update_coupon(
    coupon_id:    uuid.UUID,
    payload:      CouponUpdate,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> dict:
    from app.models.visamodels import SubscriptionCoupon
    from sqlalchemy import select
    from datetime import datetime, timezone

    result = await db.execute(
        select(SubscriptionCoupon).where(SubscriptionCoupon.id == coupon_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"Coupon {coupon_id} not found.")

    old_snapshot = {
        "valid_until": str(coupon.valid_until) if coupon.valid_until else None,
        "max_uses": coupon.max_uses,
        "is_active": coupon.is_active,
    }

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(coupon, field):
            setattr(coupon, field, value)

    coupon.modified_by = current_user.user_id
    coupon.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = current_user.user_id,
        action        = "coupon.updated",
        resource_type = "subscription_coupon",
        resource_id   = coupon.id,
        old_value     = old_snapshot,
        new_value     = update_data,
        description   = f"Coupon '{coupon.code}' updated.",
    )

    await db.commit()
    return {"message": "Coupon updated.", "coupon_id": str(coupon_id)}


# =============================================================================
# ── INVOICE LIST ──────────────────────────────────────────────────────────────
# =============================================================================

@subscription_router.get(
    "/admin/invoices",
    status_code=status.HTTP_200_OK,
    summary="List all invoices",
    description="Paginated invoice/billing history table.",
)
async def list_invoices(
    db:            DBSession,
    _:             Current_User = _view_billing,
    search:        Optional[str]       = Query(None, min_length=1),
    status_filter: Optional[str]       = Query(None, alias="status"),
    plan_id:       Optional[uuid.UUID] = Query(None),
    date_from:     Optional[str]       = Query(None),
    date_to:       Optional[str]       = Query(None),
    page:          int                 = Query(1,  ge=1),
    page_size:     int                 = Query(20, ge=1, le=100),
) -> dict:
    from datetime import datetime

    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to)   if date_to   else None

    invoices, total = await service_list_invoices(
        db,
        search    = search,
        status    = status_filter,
        plan_id   = plan_id,
        date_from = df,
        date_to   = dt,
        page      = page,
        page_size = page_size,
    )

    total_pages = max(1, math.ceil(total / page_size))

    items = []
    for inv in invoices:
        items.append({
            "id":                   str(inv.id),
            "invoice_number":       inv.invoice_number,
            "subscription_id":      str(inv.subscription_id),
            "user_name":            getattr(inv, "_user_name", ""),
            "user_email":           getattr(inv, "_user_email", ""),
            "plan_name":            getattr(inv, "_plan_name", ""),
            "total_cents":          inv.total_cents,
            "total_display":        getattr(inv, "_total_display", ""),
            "currency":             inv.currency,
            "status":               inv.status,
            "billing_period_start": str(inv.billing_period_start or ""),
            "billing_period_end":   str(inv.billing_period_end or ""),
            "paid_at":              str(inv.paid_at or ""),
            "invoice_pdf_url":      inv.invoice_pdf_url,
            "stripe_invoice_id":    inv.stripe_invoice_id,
            "created_at":           str(inv.created_at),
        })

    return {
        "items":       items,
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": total_pages,
    }


# =============================================================================
# ── PUBLIC — validate coupon (used at checkout by any authenticated user) ─────
# =============================================================================

@subscription_router.post(
    "/subscriptions/validate-coupon",
    response_model=ValidateCouponResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a coupon code at checkout",
    description=(
        "Called when a user enters a coupon code during checkout. "
        "Returns discount details if valid. No DB writes — read-only check."
    ),
)
async def validate_coupon(
    payload:      ValidateCouponRequest,
    db:           DBSession,
    current_user: Current_User,
) -> ValidateCouponResponse:
    result = await service_validate_coupon(db, payload.code, payload.plan_id)
    return ValidateCouponResponse(**result)


# =============================================================================
# ── PUBLIC — pricing page plans (visible to all authenticated users) ──────────
# =============================================================================

@subscription_router.get(
    "/subscription-plans",
    status_code=status.HTTP_200_OK,
    summary="Public pricing page — list active public plans",
    description=(
        "Returns only is_active=True + is_public=True plans. "
        "Used to render the pricing page for users choosing a plan."
    ),
)
async def list_public_plans(
    db:           DBSession,
    current_user: Current_User,
) -> dict:
    from sqlalchemy import select
    from app.models.visamodels import SubscriptionPlan, PlanFeature
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(SubscriptionPlan)
        .options(selectinload(SubscriptionPlan.features))
        .where(
            SubscriptionPlan.is_active == True,   # noqa
            SubscriptionPlan.is_public == True,   # noqa
        )
        .order_by(SubscriptionPlan.display_order.asc())
    )
    plans = result.scalars().all()

    from app.services.admin.subscription_service import _cents_to_display

    return {
        "items": [
            {
                "id":                    str(p.id),
                "name":                  p.name,
                "slug":                  p.slug,
                "description":           p.description,
                "price_monthly_display": _cents_to_display(p.price_monthly_cents, p.currency),
                "price_annual_display":  _cents_to_display(p.price_annual_cents, p.currency),
                "price_monthly_cents":   p.price_monthly_cents,
                "price_annual_cents":    p.price_annual_cents,
                "trial_days":            p.trial_days,
                "is_featured":           p.is_featured,
                "highlight_color":       p.highlight_color,
                "features": [
                    {
                        "feature_text":   f.feature_text,
                        "is_included":    f.is_included,
                        "is_highlighted": f.is_highlighted,
                    }
                    for f in sorted(p.features, key=lambda x: x.sort_order)
                ],
            }
            for p in plans
        ]
    }


# =============================================================================
# ── SELF-SERVICE — "My Subscription" (any authenticated user) ────────────────
# GET /subscriptions/me
# GET /subscriptions/me/invoices
# Used by HR / Lawyer / Employee / Student roles to view (never edit) their
# own subscription. Scoped to current_user.user_id — no admin permission
# required, and no other user's data can ever be reached through this path.
# =============================================================================

@subscription_router.get(
    "/subscriptions/me",
    status_code=status.HTTP_200_OK,
    summary="Get my own subscription",
    description=(
        "Returns the caller's own current plan, status, features, and usage "
        "against plan quotas. Read-only. Available to any authenticated role."
    ),
)
async def get_my_subscription(
    db:           DBSession,
    current_user: Current_User,
) -> dict:
    data = await service_get_my_subscription(db, current_user.user_id)
    return data


@subscription_router.get(
    "/subscriptions/me/invoices",
    status_code=status.HTTP_200_OK,
    summary="Get my own invoice/billing history",
    description="Paginated invoice history for the caller's own subscriptions only.",
)
async def get_my_invoices(
    db:           DBSession,
    current_user: Current_User,
    page:         int = Query(1, ge=1),
    page_size:    int = Query(20, ge=1, le=100),
) -> dict:
    invoices, total = await service_list_invoices(
        db, user_id=current_user.user_id, page=page, page_size=page_size
    )
    return {
        "items": [
            {
                "id":                   str(inv.id),
                "invoice_number":       inv.invoice_number,
                "plan_name":            getattr(inv, "_plan_name", ""),
                "total_cents":          inv.total_cents,
                "total_display":        getattr(inv, "_total_display", ""),
                "currency":             inv.currency,
                "status":               inv.status,
                "billing_period_start": inv.billing_period_start,
                "billing_period_end":   inv.billing_period_end,
                "paid_at":              inv.paid_at,
                "invoice_pdf_url":      inv.invoice_pdf_url,
                "created_at":           inv.created_at,
            }
            for inv in invoices
        ],
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "total_pages": math.ceil(total / page_size) if total else 0,
    }


# =============================================================================
# ── RECENT ACTIVITY FEED (admin) ──────────────────────────────────────────────
# GET /admin/subscriptions/activity
# =============================================================================

@subscription_router.get(
    "/admin/subscriptions/activity",
    status_code=status.HTTP_200_OK,
    summary="Recent subscription-related activity feed",
    description=(
        "Reads from the shared audit_logs table, filtered to subscription plan, "
        "coupon, and user-subscription changes. Powers the 'Recent Activity' panel."
    ),
)
async def get_recent_activity(
    db:    DBSession,
    _:     Current_User = _view_billing,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    items = await service_get_recent_activity(db, limit=limit)
    return {
        "items": [
            {
                "id":            str(i["id"]),
                "action":        i["action"],
                "actor_name":    i["actor_name"],
                "resource_type": i["resource_type"],
                "resource_id":   str(i["resource_id"]) if i["resource_id"] else None,
                "description":   i["description"],
                "severity":      i["severity"],
                "created_at":    i["created_at"],
            }
            for i in items
        ]
    }


# =============================================================================
# ── PAYMENT GATEWAY CONFIGURATION (admin only) ────────────────────────────────
# GET   /admin/payment-gateways
# PATCH /admin/payment-gateways/{gateway}
# PATCH /admin/payment-gateways/{gateway}/toggle
# =============================================================================

@subscription_router.get(
    "/admin/payment-gateways",
    status_code=status.HTTP_200_OK,
    summary="List payment gateway configurations",
    description="Stripe / PayPal / Bank Transfer connection status and settings.",
)
async def list_payment_gateways(
    db: DBSession,
    _:  Current_User = _admin_only,
) -> dict:
    configs = await service_list_payment_gateways(db)
    return {
        "items": [
            {
                "gateway":             c.gateway,
                "is_connected":        c.is_connected,
                "is_enabled":          c.is_enabled,
                "transaction_fee_display": (
                    f"{c.transaction_fee_percent_bps / 100:.2f}% + "
                    f"${c.transaction_fee_fixed_cents / 100:.2f}"
                    if c.transaction_fee_percent_bps is not None else None
                ),
                "settlement_days_display": (
                    f"{c.settlement_days_min}-{c.settlement_days_max} days"
                    if c.settlement_days_min is not None else None
                ),
                "supported_methods":   c.supported_methods,
                "connected_at":        c.connected_at,
            }
            for c in configs
        ]
    }


@subscription_router.patch(
    "/admin/payment-gateways/{gateway}",
    status_code=status.HTTP_200_OK,
    summary="Connect or update a payment gateway",
    description=(
        "Upserts gateway configuration. Credentials are encrypted before storage "
        "via the project's existing secrets encryption utility — never stored in plaintext."
    ),
)
async def upsert_payment_gateway(
    gateway:      str,
    payload:      PaymentGatewayUpsert,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> dict:
    from app.core.security import encrypt_secret  # use your project's existing helper
    config = await service_upsert_payment_gateway(
        db, gateway, payload, current_user.user_id, encrypt_fn=encrypt_secret
    )
    return {
        "message": f"Payment gateway '{gateway}' saved.",
        "gateway": config.gateway,
        "is_connected": config.is_connected,
    }


@subscription_router.patch(
    "/admin/payment-gateways/{gateway}/toggle",
    status_code=status.HTTP_200_OK,
    summary="Enable/disable a payment gateway",
)
async def toggle_payment_gateway(
    gateway:      str,
    payload:      PaymentGatewayToggle,
    db:           DBSession,
    current_user: Current_User,
    _:            Current_User = _admin_only,
) -> dict:
    config = await service_toggle_payment_gateway(
        db, gateway, payload.is_enabled, current_user.user_id
    )
    return {
        "message": f"Payment gateway '{gateway}' {'enabled' if config.is_enabled else 'disabled'}.",
        "gateway": config.gateway,
        "is_enabled": config.is_enabled,
    }
