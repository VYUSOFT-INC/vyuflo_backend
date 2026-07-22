"""
app/services/subscription_service.py

Business logic for Admin-07 Subscription & Pricing Control screen.
Stripe-only architecture — no PayPal.

Each function maps 1:1 to a router endpoint.
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.models.visamodels import User, UserRole, Role
from app.models.visamodels import (
    Application,
    AuditLog,
    Document,
    PaymentGatewayConfig,
    PlanFeature,
    SubscriptionCoupon,
    SubscriptionInvoice,
    SubscriptionPlan,
    UserSubscription,
)


# =============================================================================
# HELPERS
# =============================================================================

def _cents_to_display(cents: int, currency: str = "USD") -> str:
    """2900 → '$29.00'"""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{cents / 100:,.2f}"


def _compute_discount_display(
    discount_type: str, discount_value: int, currency: str = "USD"
) -> str:
    if discount_type == "percentage":
        return f"{discount_value}% off"
    return f"{_cents_to_display(discount_value, currency)} off"


def _processing_days_label(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    if days <= 14:
        return f"{days} days"
    months = round(days / 30)
    return f"{months}-{months + 1} months"


ACTIVE_STATUSES = ("trialing", "active", "past_due", "paused")
# statuses that count as "has a subscription"


# =============================================================================
# AUDIT LOG HELPER
# Reuses the existing shared `audit_logs` table — no new table needed.
# Call this BEFORE db.commit() in the same function so the audit row and the
# actual change land in the same transaction (both succeed or both roll back).
# =============================================================================

async def _write_audit_log(
    db:            AsyncSession,
    actor_id:      Optional[uuid.UUID],
    action:        str,
    resource_type: str,
    resource_id:   uuid.UUID,
    old_value:     Optional[Dict[str, Any]] = None,
    new_value:     Optional[Dict[str, Any]] = None,
    description:   Optional[str] = None,
    severity:      str = "info",
) -> None:
    entry = AuditLog(
        id            = uuid.uuid4(),
        actor_id      = actor_id,
        actor_type    = "user",
        action        = action,
        resource_type = resource_type,
        resource_id   = resource_id,
        old_value     = json.dumps(old_value, default=str) if old_value is not None else None,
        new_value     = json.dumps(new_value, default=str) if new_value is not None else None,
        description   = description,
        severity      = severity,
        created_at    = datetime.now(timezone.utc),
    )
    db.add(entry)


def _plan_snapshot(plan: SubscriptionPlan) -> Dict[str, Any]:
    """Small, log-friendly snapshot of the fields that actually matter for pricing changes."""
    return {
        "name":                plan.name,
        "price_monthly_cents": plan.price_monthly_cents,
        "price_annual_cents":  plan.price_annual_cents,
        "trial_days":          plan.trial_days,
        "is_active":           plan.is_active,
        "is_public":           plan.is_public,
    }


# =============================================================================
# 1. PLAN STATS — 4 KPI CARDS
# GET /admin/subscription-plans/stats
# =============================================================================

async def service_get_subscription_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Computes all 4 KPI card values in one function.
    Runs 5 focused queries — keep cached for ~60 seconds in prod.
    """
    now = datetime.now(timezone.utc)

    # Active subscriber count
    active_q = await db.execute(
        select(func.count(UserSubscription.id))
        .where(UserSubscription.status == "active")
    )
    active_count = active_q.scalar() or 0

    # Trial subscriber count
    trial_q = await db.execute(
        select(func.count(UserSubscription.id))
        .where(UserSubscription.status == "trialing")
    )
    trial_count = trial_q.scalar() or 0

    # Churned this calendar month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    churned_q = await db.execute(
        select(func.count(UserSubscription.id))
        .where(
            UserSubscription.status == "cancelled",
            UserSubscription.cancelled_at >= month_start,
        )
    )
    churned_count = churned_q.scalar() or 0

    # Past due count
    past_due_q = await db.execute(
        select(func.count(UserSubscription.id))
        .where(UserSubscription.status == "past_due")
    )
    past_due_count = past_due_q.scalar() or 0

    # MRR — sum active monthly amounts
    # Join subscription → plan to get price
    mrr_q = await db.execute(
        select(
            func.sum(
                case(
                    (UserSubscription.billing_cycle == "monthly",
                     SubscriptionPlan.price_monthly_cents),
                    (UserSubscription.billing_cycle == "annual",
                     SubscriptionPlan.price_annual_cents / 12),
                    else_=0
                )
            )
        )
        .select_from(UserSubscription)                                    # ← ADD THIS
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .where(UserSubscription.status == "active")
    )
    mrr_cents = int(mrr_q.scalar() or 0)

    # Apply discounts (approximate — subtract cached discounts)
    discount_q = await db.execute(
        select(
            func.sum(
                case(
                    (UserSubscription.discount_percent.isnot(None),
                     case(
                         (UserSubscription.billing_cycle == "monthly",
                          SubscriptionPlan.price_monthly_cents *
                          UserSubscription.discount_percent / 100),
                         else_=SubscriptionPlan.price_annual_cents / 12 *
                               UserSubscription.discount_percent / 100
                     )),
                    else_=0
                )
            )
        )
        .select_from(UserSubscription)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .where(UserSubscription.status == "active")
    )
    discount_total = int(discount_q.scalar() or 0)
    mrr_cents = max(0, mrr_cents - discount_total)

    total_q = await db.execute(
        select(func.count(UserSubscription.id))
        .where(UserSubscription.status.in_(list(ACTIVE_STATUSES)))
    )
    total_count = total_q.scalar() or 0

    currency = "USD"
    return {
        "mrr_cents":           mrr_cents,
        "mrr_display":         _cents_to_display(mrr_cents, currency),
        "arr_cents":           mrr_cents * 12,
        "arr_display":         _cents_to_display(mrr_cents * 12, currency),
        "mrr_change_pct":      None,   # wire to historical snapshot when ready
        "active_subscribers":  active_count,
        "active_change_pct":   None,
        "trial_subscribers":   trial_count,
        "trial_change_pct":    None,
        "churned_this_month":  churned_count,
        "churn_rate_pct":      None,
        "total_subscribers":   total_count,
        "past_due_count":      past_due_count,
        "paused_count":        0,
    }


# =============================================================================
# 2. LIST PLANS — plan cards grid
# GET /admin/subscription-plans
# =============================================================================

async def service_list_plans(db: AsyncSession) -> List[SubscriptionPlan]:
    """
    Returns all plans ordered by display_order.
    Eagerly loads features.
    Attaches live subscriber counts as temp attributes.
    """
    result = await db.execute(
        select(SubscriptionPlan)
        .options(selectinload(SubscriptionPlan.features))
        .order_by(SubscriptionPlan.display_order.asc())
    )
    plans = result.scalars().all()

    # Attach subscriber counts per plan in one query
    counts_q = await db.execute(
        select(
            UserSubscription.plan_id,
            UserSubscription.status,
            func.count(UserSubscription.id).label("cnt"),
        )
        .where(UserSubscription.status.in_(["active", "trialing"]))
        .group_by(UserSubscription.plan_id, UserSubscription.status)
    )
    counts_raw = counts_q.all()

    # Build lookup: {plan_id: {status: count}}
    counts: Dict[uuid.UUID, Dict[str, int]] = {}
    for row in counts_raw:
        pid = row.plan_id
        counts.setdefault(pid, {})
        counts[pid][row.status] = row.cnt

    for plan in plans:
        plan_counts = counts.get(plan.id, {})
        plan._active_count = plan_counts.get("active", 0)    # type: ignore
        plan._trial_count  = plan_counts.get("trialing", 0)  # type: ignore
        plan._total_count  = sum(plan_counts.values())        # type: ignore
        # Computed display fields
        plan._monthly_display = _cents_to_display(plan.price_monthly_cents, plan.currency)  # type: ignore
        plan._annual_display  = _cents_to_display(plan.price_annual_cents, plan.currency)   # type: ignore
        monthly_equiv = plan.price_annual_cents / 12 if plan.price_annual_cents else 0
        plan._annual_monthly_equiv = _cents_to_display(int(monthly_equiv), plan.currency)   # type: ignore

    return plans


# =============================================================================
# 3. GET ONE PLAN
# GET /admin/subscription-plans/{id}
# =============================================================================

async def service_get_plan(
    db: AsyncSession, plan_id: uuid.UUID
) -> SubscriptionPlan:
    result = await db.execute(
        select(SubscriptionPlan)
        .options(selectinload(SubscriptionPlan.features))
        .where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundException(f"Subscription plan {plan_id} not found.")

    counts_q = await db.execute(
        select(UserSubscription.status, func.count(UserSubscription.id))
        .where(UserSubscription.plan_id == plan_id)
        .group_by(UserSubscription.status)
    )
    counts = {row[0]: row[1] for row in counts_q.all()}

    plan._active_count = counts.get("active", 0)    # type: ignore
    plan._trial_count  = counts.get("trialing", 0)  # type: ignore
    plan._total_count  = sum(v for k, v in counts.items() if k in ACTIVE_STATUSES)  # type: ignore
    plan._monthly_display = _cents_to_display(plan.price_monthly_cents, plan.currency)  # type: ignore
    plan._annual_display  = _cents_to_display(plan.price_annual_cents, plan.currency)   # type: ignore
    monthly_equiv = plan.price_annual_cents / 12 if plan.price_annual_cents else 0
    plan._annual_monthly_equiv = _cents_to_display(int(monthly_equiv), plan.currency)   # type: ignore

    return plan


# =============================================================================
# 4. CREATE PLAN
# POST /admin/subscription-plans
# =============================================================================

async def service_create_plan(
    db:         AsyncSession,
    payload:    Any,
    created_by: uuid.UUID,
) -> SubscriptionPlan:
    # Guard: slug must be unique
    existing = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.slug == payload.slug
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            f"A plan with slug '{payload.slug}' already exists."
        )

    plan = SubscriptionPlan(
        id                    = uuid.uuid4(),
        name                  = payload.name,
        slug                  = payload.slug,
        description           = payload.description,
        price_monthly_cents   = payload.price_monthly_cents,
        price_annual_cents    = payload.price_annual_cents,
        currency              = payload.currency,
        trial_days            = payload.trial_days,
        max_applications      = payload.max_applications,
        max_documents         = payload.max_documents,
        max_messages          = payload.max_messages,
        stripe_product_id     = payload.stripe_product_id,
        stripe_price_id_monthly = payload.stripe_price_id_monthly,
        stripe_price_id_annual  = payload.stripe_price_id_annual,
        is_active             = payload.is_active,
        is_public             = payload.is_public,
        is_featured           = payload.is_featured,
        display_order         = payload.display_order,
        highlight_color       = payload.highlight_color,
        created_by            = created_by,
        modified_by           = created_by,
        created_at            = datetime.now(timezone.utc),
        updated_at            = datetime.now(timezone.utc),
    )
    db.add(plan)
    await db.flush()  # get plan.id before inserting features

    # Insert features
    for f in payload.features:
        feature = PlanFeature(
            id             = uuid.uuid4(),
            plan_id        = plan.id,
            feature_text   = f.feature_text,
            is_included    = f.is_included,
            sort_order     = f.sort_order,
            is_highlighted = f.is_highlighted,
            created_by     = created_by,
            created_at     = datetime.now(timezone.utc),
            updated_at     = datetime.now(timezone.utc),
        )
        db.add(feature)

    await db.commit()
    await db.refresh(plan)
    return await service_get_plan(db, plan.id)


# =============================================================================
# 5. UPDATE PLAN
# PATCH /admin/subscription-plans/{id}
# =============================================================================

async def service_update_plan(
    db:          AsyncSession,
    plan_id:     uuid.UUID,
    payload:     Any,
    modified_by: uuid.UUID,
) -> SubscriptionPlan:
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundException(f"Plan {plan_id} not found.")

    old_snapshot = _plan_snapshot(plan)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(plan, field):
            setattr(plan, field, value)

    plan.modified_by = modified_by
    plan.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "subscription_plan.updated",
        resource_type = "subscription_plan",
        resource_id   = plan.id,
        old_value     = old_snapshot,
        new_value     = _plan_snapshot(plan),
        description   = f"Plan '{plan.name}' updated.",
        severity      = "warning" if update_data.get("price_monthly_cents") is not None
                                    or update_data.get("price_annual_cents") is not None
                                 else "info",
    )

    await db.commit()
    await db.refresh(plan)
    return await service_get_plan(db, plan_id)


# =============================================================================
# 6. TOGGLE PLAN ACTIVE/INACTIVE
# PATCH /admin/subscription-plans/{id}/toggle
# =============================================================================

async def service_toggle_plan(
    db:          AsyncSession,
    plan_id:     uuid.UUID,
    is_active:   bool,
    modified_by: uuid.UUID,
) -> SubscriptionPlan:
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise NotFoundException(f"Plan {plan_id} not found.")

    # Guard: cannot deactivate if active subscribers exist
    if not is_active:
        active_sub_q = await db.execute(
            select(func.count(UserSubscription.id))
            .where(
                UserSubscription.plan_id == plan_id,
                UserSubscription.status.in_(["active", "trialing"]),
            )
        )
        active_count = active_sub_q.scalar() or 0
        if active_count > 0:
            raise BadRequestException(
                f"Cannot deactivate plan — {active_count} active subscriber(s) are on this plan. "
                "Migrate them first or let their subscriptions expire."
            )

    plan.is_active   = is_active
    plan.modified_by = modified_by
    plan.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "subscription_plan.toggled",
        resource_type = "subscription_plan",
        resource_id   = plan.id,
        old_value     = {"is_active": not is_active},
        new_value     = {"is_active": is_active},
        description   = f"Plan '{plan.name}' {'activated' if is_active else 'deactivated'}.",
    )

    await db.commit()
    await db.refresh(plan)
    return await service_get_plan(db, plan_id)


# =============================================================================
# 7. LIST SUBSCRIBERS
# GET /admin/subscriptions
# =============================================================================

async def service_list_subscribers(
    db:          AsyncSession,
    search:      Optional[str]  = None,
    plan_id:     Optional[uuid.UUID] = None,
    status:      Optional[str]  = None,
    date_from:   Optional[datetime] = None,
    date_to:     Optional[datetime] = None,
    sort_by:     str            = "created_at",
    sort_order:  str            = "desc",
    page:        int            = 1,
    page_size:   int            = 20,
) -> Tuple[List[Any], int]:
    """
    Returns enriched subscription rows with user + plan info joined.
    """
    q = (
        select(
            UserSubscription,
            User.first_name,
            User.last_name,
            User.email,
            SubscriptionPlan.name.label("plan_name"),
            SubscriptionPlan.slug.label("plan_slug"),
            SubscriptionPlan.price_monthly_cents,
            SubscriptionPlan.price_annual_cents,
            SubscriptionPlan.currency,
            SubscriptionCoupon.code.label("coupon_code"),
        )
        .join(User, UserSubscription.user_id == User.id)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
        .outerjoin(SubscriptionCoupon,
                   UserSubscription.coupon_id == SubscriptionCoupon.id)
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            or_(
                func.lower(User.first_name).like(term),
                func.lower(User.last_name).like(term),
                func.lower(User.email).like(term),
            )
        )
    if plan_id:
        q = q.where(UserSubscription.plan_id == plan_id)
    if status:
        q = q.where(UserSubscription.status == status)
    if date_from:
        q = q.where(UserSubscription.created_at >= date_from)
    if date_to:
        q = q.where(UserSubscription.created_at <= date_to)

    # ── Count ─────────────────────────────────────────────────────────────────
    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # ── Sort ──────────────────────────────────────────────────────────────────
    sort_col_map = {
        "created_at":  UserSubscription.created_at,
        "status":      UserSubscription.status,
        "plan":        SubscriptionPlan.name,
        "user":        User.last_name,
        "period_end":  UserSubscription.current_period_end,
    }
    sort_col = sort_col_map.get(sort_by, UserSubscription.created_at)
    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    # ── Pagination ────────────────────────────────────────────────────────────
    offset = (page - 1) * page_size
    q = q.offset(offset).limit(page_size)

    result = await db.execute(q)
    rows = result.all()

    # ── Enrich ────────────────────────────────────────────────────────────────
    enriched = []
    for row in rows:
        sub: UserSubscription = row.UserSubscription
        sub._user_name    = f"{row.first_name} {row.last_name}"  # type: ignore
        sub._user_email   = row.email                             # type: ignore
        sub._user_role    = "user"                                # type: ignore
        sub._plan_name    = row.plan_name                         # type: ignore
        sub._plan_slug    = row.plan_slug                         # type: ignore
        sub._coupon_code  = row.coupon_code                       # type: ignore

        # Amount display
        if sub.billing_cycle == "monthly":
            amount = row.price_monthly_cents
        elif sub.billing_cycle == "annual":
            amount = row.price_annual_cents
        else:
            amount = 0

        # Apply discount
        if sub.discount_percent:
            amount = int(amount * (1 - sub.discount_percent / 100))
        elif sub.discount_amount_cents:
            amount = max(0, amount - sub.discount_amount_cents)

        cycle_label = "month" if sub.billing_cycle == "monthly" else "year"
        sub._amount_display = (                                   # type: ignore
            f"{_cents_to_display(amount, row.currency)}/{cycle_label}"
        )

        sub._discount_display = (                                 # type: ignore
            _compute_discount_display("percentage", sub.discount_percent)
            if sub.discount_percent
            else (
                _compute_discount_display("fixed_amount", sub.discount_amount_cents, row.currency)
                if sub.discount_amount_cents else None
            )
        )
        enriched.append(sub)

    return enriched, total


# =============================================================================
# 8. GET SUBSCRIBER DETAIL
# GET /admin/subscriptions/{id}
# =============================================================================

async def service_get_subscription(
    db: AsyncSession, subscription_id: uuid.UUID
) -> Any:
    result = await db.execute(
        select(UserSubscription)
        .options(selectinload(UserSubscription.invoices))
        .where(UserSubscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException(f"Subscription {subscription_id} not found.")

    # Fetch user info
    user_q = await db.execute(
        select(User.first_name, User.last_name, User.email)
        .where(User.id == sub.user_id)
    )
    user_row = user_q.first()
    if user_row:
        sub._user_name  = f"{user_row.first_name} {user_row.last_name}"  # type: ignore
        sub._user_email = user_row.email                                   # type: ignore

    # Fetch plan info
    plan_q = await db.execute(
        select(SubscriptionPlan.name, SubscriptionPlan.slug,
               SubscriptionPlan.price_monthly_cents,
               SubscriptionPlan.price_annual_cents,
               SubscriptionPlan.currency)
        .where(SubscriptionPlan.id == sub.plan_id)
    )
    plan_row = plan_q.first()
    if plan_row:
        sub._plan_name = plan_row.name   # type: ignore
        sub._plan_slug = plan_row.slug   # type: ignore

    return sub


# =============================================================================
# 9. ADMIN ASSIGN PLAN (manual — no Stripe payment)
# POST /admin/subscriptions/assign
# =============================================================================

async def service_admin_assign_plan(
    db:          AsyncSession,
    payload:     Any,
    assigned_by: uuid.UUID,
) -> UserSubscription:
    """
    Admin manually gives a user a plan.
    No Stripe involved — sets assigned_by_admin=True.
    Cancels any existing active subscription first.
    """
    # Check user exists
    user_q = await db.execute(
        select(User).where(User.id == payload.user_id)
    )
    user = user_q.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found.")

    # Check plan exists
    plan_q = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == payload.plan_id)
    )
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise NotFoundException("Plan not found.")

    # Cancel any existing active subscription
    existing_q = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == payload.user_id,
            UserSubscription.status.in_(list(ACTIVE_STATUSES)),
        )
    )
    existing = existing_q.scalars().all()
    now = datetime.now(timezone.utc)
    for sub in existing:
        sub.status         = "cancelled"
        sub.cancelled_at   = now
        sub.cancellation_reason = "Superseded by admin plan assignment"
        sub.modified_by    = assigned_by
        sub.updated_at     = now

    # Create new subscription
    new_sub = UserSubscription(
        id                = uuid.uuid4(),
        user_id           = payload.user_id,
        plan_id           = payload.plan_id,
        status            = "trialing" if payload.trial_days > 0 else "active",
        billing_cycle     = payload.billing_cycle,
        trial_start       = now if payload.trial_days > 0 else None,
        trial_end         = (
            datetime(now.year, now.month, now.day + payload.trial_days,
                     tzinfo=timezone.utc)
            if payload.trial_days > 0 else None
        ),
        current_period_start = now,
        current_period_end   = None,
        payment_processor = "manual",
        assigned_by_admin = True,
        admin_notes       = payload.admin_notes,
        created_by        = assigned_by,
        modified_by       = assigned_by,
        created_at        = now,
        updated_at        = now,
    )
    db.add(new_sub)

    # Update user's cached tier
    await db.execute(
        update(User)
        .where(User.id == payload.user_id)
        .values(subscription_tier=plan.slug)
    )

    await _write_audit_log(
        db,
        actor_id      = assigned_by,
        action        = "subscription.admin_assigned",
        resource_type = "user_subscription",
        resource_id   = new_sub.id,
        new_value     = {
            "user_id":  str(payload.user_id),
            "plan_id":  str(payload.plan_id),
            "plan_name": plan.name,
            "status":   new_sub.status,
        },
        description   = f"Admin manually assigned plan '{plan.name}' to user {payload.user_id}.",
        severity      = "warning",
    )

    await db.commit()
    await db.refresh(new_sub)
    return new_sub


# =============================================================================
# 10. CHANGE PLAN
# PATCH /admin/subscriptions/{id}/change-plan
# =============================================================================

async def service_change_plan(
    db:              AsyncSession,
    subscription_id: uuid.UUID,
    payload:         Any,
    modified_by:     uuid.UUID,
) -> UserSubscription:
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException(f"Subscription {subscription_id} not found.")

    # Verify new plan exists
    plan_q = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == payload.new_plan_id)
    )
    plan = plan_q.scalar_one_or_none()
    if not plan:
        raise NotFoundException("New plan not found.")

    old_plan_id = sub.plan_id

    sub.plan_id     = payload.new_plan_id
    if payload.billing_cycle:
        sub.billing_cycle = payload.billing_cycle
    if payload.admin_notes:
        sub.admin_notes = payload.admin_notes
    sub.modified_by = modified_by
    sub.updated_at  = datetime.now(timezone.utc)

    # Update cached tier on user
    await db.execute(
        update(User)
        .where(User.id == sub.user_id)
        .values(subscription_tier=plan.slug)
    )

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "subscription.plan_changed",
        resource_type = "user_subscription",
        resource_id   = sub.id,
        old_value     = {"plan_id": str(old_plan_id)},
        new_value     = {"plan_id": str(payload.new_plan_id), "plan_name": plan.name},
        description   = f"Subscription {sub.id} moved to plan '{plan.name}'.",
        severity      = "warning",
    )

    await db.commit()
    await db.refresh(sub)
    return sub


# =============================================================================
# 11. CANCEL SUBSCRIPTION
# PATCH /admin/subscriptions/{id}/cancel
# =============================================================================

async def service_cancel_subscription(
    db:              AsyncSession,
    subscription_id: uuid.UUID,
    payload:         Any,
    cancelled_by:    uuid.UUID,
) -> UserSubscription:
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise NotFoundException(f"Subscription {subscription_id} not found.")

    if sub.status == "cancelled":
        raise BadRequestException("Subscription is already cancelled.")

    now = datetime.now(timezone.utc)

    if payload.cancel_immediately:
        sub.status       = "cancelled"
        sub.cancelled_at = now
    else:
        sub.cancel_at_period_end = True

    sub.cancellation_reason = payload.cancellation_reason
    sub.modified_by         = cancelled_by
    sub.updated_at          = now

    # If immediate: downgrade user to free tier
    if payload.cancel_immediately:
        await db.execute(
            update(User)
            .where(User.id == sub.user_id)
            .values(subscription_tier="free")
        )

    await _write_audit_log(
        db,
        actor_id      = cancelled_by,
        action        = "subscription.cancelled",
        resource_type = "user_subscription",
        resource_id   = sub.id,
        new_value     = {
            "cancel_immediately": payload.cancel_immediately,
            "reason":             payload.cancellation_reason,
        },
        description   = f"Subscription {sub.id} cancelled "
                        f"({'immediately' if payload.cancel_immediately else 'at period end'}).",
        severity      = "warning",
    )

    await db.commit()
    await db.refresh(sub)
    return sub


# =============================================================================
# 12. LIST COUPONS
# GET /admin/coupons
# =============================================================================

async def service_list_coupons(
    db:        AsyncSession,
    search:    Optional[str]  = None,
    is_active: Optional[bool] = None,
    page:      int            = 1,
    page_size: int            = 20,
) -> Tuple[List[SubscriptionCoupon], int]:
    q = select(SubscriptionCoupon)

    if search:
        term = f"%{search.upper()}%"
        q = q.where(
            or_(
                SubscriptionCoupon.code.like(term),
                func.lower(SubscriptionCoupon.name).like(f"%{search.lower()}%"),
            )
        )
    if is_active is not None:
        q = q.where(SubscriptionCoupon.is_active == is_active)

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.order_by(SubscriptionCoupon.created_at.desc())
    offset = (page - 1) * page_size
    q = q.offset(offset).limit(page_size)

    result = await db.execute(q)
    coupons = result.scalars().all()

    now = datetime.now(timezone.utc)

    # Total savings per coupon — sum of discount_cents on every invoice generated
    # under a subscription that used this coupon. Reuses existing subscription_invoices
    # table; no new table needed.
    coupon_ids = [c.id for c in coupons]
    savings_by_coupon: Dict[uuid.UUID, int] = {}
    if coupon_ids:
        savings_q = await db.execute(
            select(
                UserSubscription.coupon_id,
                func.coalesce(func.sum(SubscriptionInvoice.discount_cents), 0),
            )
            .join(SubscriptionInvoice,
                  SubscriptionInvoice.subscription_id == UserSubscription.id)
            .where(UserSubscription.coupon_id.in_(coupon_ids))
            .group_by(UserSubscription.coupon_id)
        )
        savings_by_coupon = {row[0]: int(row[1]) for row in savings_q.all()}

    for c in coupons:
        c._discount_display = _compute_discount_display(  # type: ignore
            c.discount_type, c.discount_value
        )
        c._is_expired   = bool(c.valid_until and c.valid_until < now)   # type: ignore
        c._is_exhausted = bool(c.max_uses and c.uses_count >= c.max_uses)  # type: ignore
        c._remaining    = (                                               # type: ignore
            (c.max_uses - c.uses_count) if c.max_uses else None
        )
        savings_cents = savings_by_coupon.get(c.id, 0)               # type: ignore
        c._total_savings_cents  = savings_cents                       # type: ignore
        c._total_savings_display = _cents_to_display(savings_cents)  # type: ignore

    return coupons, total


# =============================================================================
# 13. CREATE COUPON
# POST /admin/coupons
# =============================================================================

async def service_create_coupon(
    db:         AsyncSession,
    payload:    Any,
    created_by: uuid.UUID,
) -> SubscriptionCoupon:
    # Guard: code must be unique
    existing = await db.execute(
        select(SubscriptionCoupon).where(
            SubscriptionCoupon.code == payload.code.upper()
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException(
            f"Coupon code '{payload.code}' already exists."
        )

    coupon = SubscriptionCoupon(
        id                    = uuid.uuid4(),
        code                  = payload.code.upper(),
        name                  = payload.name,
        description           = payload.description,
        discount_type         = payload.discount_type,
        discount_value        = payload.discount_value,
        valid_from            = payload.valid_from,
        valid_until           = payload.valid_until,
        max_uses              = payload.max_uses,
        uses_count            = 0,
        applicable_plan_slugs = payload.applicable_plan_slugs,
        is_active             = True,
        created_by            = created_by,
        modified_by           = created_by,
        created_at            = datetime.now(timezone.utc),
        updated_at            = datetime.now(timezone.utc),
    )
    db.add(coupon)

    await _write_audit_log(
        db,
        actor_id      = created_by,
        action        = "coupon.created",
        resource_type = "subscription_coupon",
        resource_id   = coupon.id,
        new_value     = {
            "code": coupon.code, "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
        },
        description   = f"Coupon '{coupon.code}' created.",
    )

    await db.commit()
    await db.refresh(coupon)

    coupon._discount_display = _compute_discount_display(  # type: ignore
        coupon.discount_type, coupon.discount_value
    )
    coupon._is_expired   = False  # type: ignore
    coupon._is_exhausted = False  # type: ignore
    coupon._remaining    = coupon.max_uses  # type: ignore
    coupon._total_savings_cents  = 0        # type: ignore  # brand new, no redemptions yet
    coupon._total_savings_display = _cents_to_display(0)  # type: ignore
    return coupon


# =============================================================================
# 14. TOGGLE COUPON
# PATCH /admin/coupons/{id}/toggle
# =============================================================================

async def service_toggle_coupon(
    db:          AsyncSession,
    coupon_id:   uuid.UUID,
    is_active:   bool,
    modified_by: uuid.UUID,
) -> SubscriptionCoupon:
    result = await db.execute(
        select(SubscriptionCoupon).where(SubscriptionCoupon.id == coupon_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise NotFoundException(f"Coupon {coupon_id} not found.")

    coupon.is_active   = is_active
    coupon.modified_by = modified_by
    coupon.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "coupon.toggled",
        resource_type = "subscription_coupon",
        resource_id   = coupon.id,
        old_value     = {"is_active": not is_active},
        new_value     = {"is_active": is_active},
        description   = f"Coupon '{coupon.code}' {'activated' if is_active else 'deactivated'}.",
    )

    await db.commit()
    await db.refresh(coupon)
    coupon._discount_display = _compute_discount_display(  # type: ignore
        coupon.discount_type, coupon.discount_value
    )
    now = datetime.now(timezone.utc)
    coupon._is_expired   = bool(coupon.valid_until and coupon.valid_until < now)   # type: ignore
    coupon._is_exhausted = bool(coupon.max_uses and coupon.uses_count >= coupon.max_uses)  # type: ignore
    coupon._remaining    = ((coupon.max_uses - coupon.uses_count) if coupon.max_uses else None)  # type: ignore
    return coupon


# =============================================================================
# 15. VALIDATE COUPON (used at checkout by any user role)
# POST /subscriptions/validate-coupon
# =============================================================================

async def service_validate_coupon(
    db:      AsyncSession,
    code:    str,
    plan_id: uuid.UUID,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(SubscriptionCoupon).where(
            SubscriptionCoupon.code == code.upper(),
            SubscriptionCoupon.is_active == True,  # noqa
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        return {"valid": False, "message": "Invalid or inactive coupon code."}

    if coupon.valid_until and coupon.valid_until < now:
        return {"valid": False, "message": "This coupon has expired."}

    if coupon.max_uses and coupon.uses_count >= coupon.max_uses:
        return {"valid": False, "message": "This coupon has reached its usage limit."}

    if coupon.valid_from > now:
        return {"valid": False, "message": "This coupon is not yet active."}

    # Check plan restriction
    if coupon.applicable_plan_slugs:
        plan_q = await db.execute(
            select(SubscriptionPlan.slug).where(SubscriptionPlan.id == plan_id)
        )
        plan_slug = plan_q.scalar_one_or_none()
        try:
            allowed_slugs = json.loads(coupon.applicable_plan_slugs)
            if plan_slug not in allowed_slugs:
                return {
                    "valid": False,
                    "message": f"This coupon is not valid for the selected plan.",
                }
        except (json.JSONDecodeError, TypeError):
            pass

    discount_display = _compute_discount_display(
        coupon.discount_type, coupon.discount_value
    )

    return {
        "valid":            True,
        "coupon_id":        coupon.id,
        "discount_type":    coupon.discount_type,
        "discount_value":   coupon.discount_value,
        "discount_display": discount_display,
        "message":          f"Coupon applied — {discount_display}",
    }


# =============================================================================
# 16. LIST INVOICES
# GET /admin/invoices
# =============================================================================

async def service_list_invoices(
    db:          AsyncSession,
    search:      Optional[str]  = None,
    status:      Optional[str]  = None,
    plan_id:     Optional[uuid.UUID] = None,
    date_from:   Optional[datetime] = None,
    date_to:     Optional[datetime] = None,
    user_id:     Optional[uuid.UUID] = None,
    page:        int            = 1,
    page_size:   int            = 20,
) -> Tuple[List[Any], int]:
    q = (
        select(
            SubscriptionInvoice,
            User.first_name,
            User.last_name,
            User.email,
            SubscriptionPlan.name.label("plan_name"),
            SubscriptionPlan.currency,
        )
        .join(UserSubscription,
              SubscriptionInvoice.subscription_id == UserSubscription.id)
        .join(User, UserSubscription.user_id == User.id)
        .join(SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id)
    )

    if search:
        term = f"%{search.lower()}%"
        q = q.where(
            or_(
                func.lower(User.first_name).like(term),
                func.lower(User.last_name).like(term),
                func.lower(User.email).like(term),
                func.lower(SubscriptionInvoice.invoice_number).like(term),
            )
        )
    if status:
        q = q.where(SubscriptionInvoice.status == status)
    if plan_id:
        q = q.where(UserSubscription.plan_id == plan_id)
    if date_from:
        q = q.where(SubscriptionInvoice.created_at >= date_from)
    if date_to:
        q = q.where(SubscriptionInvoice.created_at <= date_to)
    if user_id:
        q = q.where(UserSubscription.user_id == user_id)

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    q = q.order_by(SubscriptionInvoice.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(q)
    rows = result.all()

    enriched = []
    for row in rows:
        inv: SubscriptionInvoice = row.SubscriptionInvoice
        inv._user_name   = f"{row.first_name} {row.last_name}"  # type: ignore
        inv._user_email  = row.email                             # type: ignore
        inv._plan_name   = row.plan_name                         # type: ignore
        inv._total_display = _cents_to_display(inv.total_cents, row.currency)  # type: ignore
        enriched.append(inv)

    return enriched, total


# =============================================================================
# 17. REVENUE ANALYTICS
# GET /admin/subscriptions/analytics
# =============================================================================

async def service_get_revenue_analytics(
    db:            AsyncSession,
    period_months: int = 12,
) -> Dict[str, Any]:
    """Powers the MRR trend chart and plan distribution chart."""
    from dateutil.relativedelta import relativedelta  # type: ignore

    now = datetime.now(timezone.utc)

    # Plan distribution — current snapshot
    dist_q = await db.execute(
        select(
            SubscriptionPlan.name,
            SubscriptionPlan.slug,
            SubscriptionPlan.price_monthly_cents,
            SubscriptionPlan.currency,
            func.count(UserSubscription.id).label("count"),
        )
        .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
        .where(UserSubscription.status == "active")
        .group_by(
            SubscriptionPlan.id,
            SubscriptionPlan.name,
            SubscriptionPlan.slug,
            SubscriptionPlan.price_monthly_cents,
            SubscriptionPlan.currency,
        )
    )
    dist_rows = dist_q.all()
    total_active = sum(r.count for r in dist_rows) or 1

    plan_distribution = []
    for row in dist_rows:
        plan_mrr = row.price_monthly_cents * row.count
        plan_distribution.append({
            "plan_name":        row.name,
            "plan_slug":        row.slug,
            "subscriber_count": row.count,
            "percentage":       round(row.count / total_active * 100, 1),
            "mrr_cents":        plan_mrr,
            "mrr_display":      _cents_to_display(plan_mrr, row.currency),
        })

    # MRR trend — monthly grain for last N months
    mrr_trend = []
    for i in range(period_months - 1, -1, -1):
        period_start = (now - relativedelta(months=i)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        period_end = (period_start + relativedelta(months=1))

        # Active subs at end of that month
        active_q = await db.execute(
            select(
                func.sum(SubscriptionPlan.price_monthly_cents)
            )
            .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
            .where(
                UserSubscription.status == "active",
                UserSubscription.created_at < period_end,
                or_(
                    UserSubscription.cancelled_at.is_(None),
                    UserSubscription.cancelled_at >= period_end,
                ),
            )
        )
        mrr = int(active_q.scalar() or 0)

        mrr_trend.append({
            "date":       period_start.strftime("%Y-%m"),
            "mrr_cents":  mrr,
            "mrr_display": _cents_to_display(mrr),
            "new_mrr":    0,      # wire to detailed tracking when ready
            "churned_mrr": 0,
        })

    return {
        "mrr_trend":         mrr_trend,
        "plan_distribution": plan_distribution,
        "period_months":     period_months,
    }


# =============================================================================
# 18. EXPORT SUBSCRIBERS (CSV)
# GET /admin/subscriptions/export
# =============================================================================

async def service_export_subscribers(
    db:        AsyncSession,
    plan_id:   Optional[uuid.UUID] = None,
    status:    Optional[str]       = None,
) -> str:
    import csv
    import io

    rows, _ = await service_list_subscribers(
        db, plan_id=plan_id, status=status,
        page=1, page_size=10000
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Email", "Plan", "Status", "Billing Cycle",
        "Amount", "Period Start", "Period End",
        "Trial End", "Cancel At Period End",
        "Payment Processor", "Stripe Sub ID",
        "Admin Assigned", "Joined Date",
    ])

    for sub in rows:
        writer.writerow([
            getattr(sub, "_user_name", ""),
            getattr(sub, "_user_email", ""),
            getattr(sub, "_plan_name", ""),
            sub.status,
            sub.billing_cycle,
            getattr(sub, "_amount_display", ""),
            str(sub.current_period_start or ""),
            str(sub.current_period_end or ""),
            str(sub.trial_end or ""),
            "Yes" if sub.cancel_at_period_end else "No",
            sub.payment_processor,
            sub.stripe_subscription_id or "",
            "Yes" if sub.assigned_by_admin else "No",
            str(sub.created_at),
        ])

    return output.getvalue()


# =============================================================================
# 19. MY SUBSCRIPTION (self-service — any authenticated user)
# GET /subscriptions/me
# =============================================================================

async def service_get_my_subscription(
    db:      AsyncSession,
    user_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Returns the caller's own current subscription plus live usage against
    plan quotas. No admin fields are exposed (no other users' data, no
    Stripe internals beyond what the subscriber themself should see).
    """
    result = await db.execute(
        select(UserSubscription)
        .options(selectinload(UserSubscription.plan).selectinload(SubscriptionPlan.features))
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.status.in_(list(ACTIVE_STATUSES)),
        )
        .order_by(UserSubscription.created_at.desc())
    )
    sub = result.scalars().first()

    if not sub:
        return {
            "has_subscription": False,
            "plan_name": None,
            "status": None,
        }

    plan = sub.plan

    # Usage counts — reuses existing tables, no new columns needed.
    apps_count = (await db.execute(
        select(func.count(Application.id)).where(Application.user_id == user_id)
    )).scalar() or 0
    docs_count = (await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )).scalar() or 0

    def _quota(used: int, limit: Optional[int]) -> Dict[str, Any]:
        return {
            "used": used,
            "limit": limit,               # null = unlimited
            "remaining": (limit - used) if limit is not None else None,
            "is_unlimited": limit is None,
        }

    return {
        "has_subscription":     True,
        "subscription_id":      sub.id,
        "plan_id":              plan.id,
        "plan_name":            plan.name,
        "plan_slug":            plan.slug,
        "status":               sub.status,
        "billing_cycle":        sub.billing_cycle,
        "current_period_start": sub.current_period_start,
        "current_period_end":   sub.current_period_end,
        "trial_end":            sub.trial_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "features": [
            {
                "feature_text": f.feature_text,
                "is_included":  f.is_included,
            }
            for f in sorted(plan.features, key=lambda x: x.sort_order)
        ],
        "usage": {
            "applications": _quota(apps_count, plan.max_applications),
            "documents":    _quota(docs_count, plan.max_documents),
        },
    }


# =============================================================================
# 20. RECENT ACTIVITY FEED
# GET /admin/subscriptions/activity
# =============================================================================

async def service_get_recent_activity(
    db:    AsyncSession,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Reads from the existing shared `audit_logs` table — filtered to
    subscription-related resource types. No new table needed.
    """
    result = await db.execute(
        select(AuditLog, User.first_name, User.last_name)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .where(
            AuditLog.resource_type.in_([
                "subscription_plan", "user_subscription", "subscription_coupon",
            ])
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    items = []
    for row in rows:
        log: AuditLog = row.AuditLog
        actor_name = (
            f"{row.first_name} {row.last_name}".strip()
            if row.first_name else "System"
        )
        items.append({
            "id":            log.id,
            "action":        log.action,
            "actor_name":    actor_name,
            "resource_type": log.resource_type,
            "resource_id":   log.resource_id,
            "description":   log.description,
            "severity":      log.severity,
            "created_at":    log.created_at,
        })
    return items


# =============================================================================
# 21. PAYMENT GATEWAY CONFIGURATION
# GET/PATCH /admin/payment-gateways
# =============================================================================

async def service_list_payment_gateways(
    db: AsyncSession,
) -> List[PaymentGatewayConfig]:
    result = await db.execute(
        select(PaymentGatewayConfig).order_by(PaymentGatewayConfig.gateway)
    )
    return list(result.scalars().all())


async def service_upsert_payment_gateway(
    db:          AsyncSession,
    gateway:     str,
    payload:     Any,
    modified_by: uuid.UUID,
    encrypt_fn,  # inject your existing secrets/encryption helper here
) -> PaymentGatewayConfig:
    """
    Create or update a gateway's configuration.
    `encrypt_fn` must be your project's existing encryption utility —
    this function never stores plaintext credentials.
    """
    result = await db.execute(
        select(PaymentGatewayConfig).where(PaymentGatewayConfig.gateway == gateway)
    )
    config = result.scalar_one_or_none()

    update_data = payload.model_dump(exclude_unset=True)
    raw_credentials = update_data.pop("credentials", None)

    is_new = config is None
    if is_new:
        config = PaymentGatewayConfig(
            id         = uuid.uuid4(),
            gateway    = gateway,
            created_by = modified_by,
            created_at = datetime.now(timezone.utc),
        )
        db.add(config)

    for field, value in update_data.items():
        if hasattr(config, field):
            setattr(config, field, value)

    if raw_credentials is not None:
        config.credentials_encrypted = encrypt_fn(json.dumps(raw_credentials))
        config.is_connected = True
        config.connected_at = datetime.now(timezone.utc)

    config.modified_by = modified_by
    config.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "payment_gateway.connected" if is_new else "payment_gateway.updated",
        resource_type = "payment_gateway_config",
        resource_id   = config.id,
        new_value     = {
            "gateway": gateway,
            "is_enabled": config.is_enabled,
            # never log credentials, even encrypted ones
        },
        description   = f"Payment gateway '{gateway}' {'connected' if is_new else 'updated'}.",
        severity      = "critical",
    )

    await db.commit()
    await db.refresh(config)
    return config


async def service_toggle_payment_gateway(
    db:          AsyncSession,
    gateway:     str,
    is_enabled:  bool,
    modified_by: uuid.UUID,
) -> PaymentGatewayConfig:
    result = await db.execute(
        select(PaymentGatewayConfig).where(PaymentGatewayConfig.gateway == gateway)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise NotFoundException(f"Gateway '{gateway}' is not configured yet.")

    config.is_enabled  = is_enabled
    config.modified_by = modified_by
    config.updated_at  = datetime.now(timezone.utc)

    await _write_audit_log(
        db,
        actor_id      = modified_by,
        action        = "payment_gateway.toggled",
        resource_type = "payment_gateway_config",
        resource_id   = config.id,
        old_value     = {"is_enabled": not is_enabled},
        new_value     = {"is_enabled": is_enabled},
        description   = f"Payment gateway '{gateway}' {'enabled' if is_enabled else 'disabled'}.",
        severity      = "critical",
    )

    await db.commit()
    await db.refresh(config)
    return config
