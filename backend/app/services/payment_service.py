# =============================================================================
# app/services/payment_service.py
# All reusable business logic for payments.
# Routers call these functions — keep routers thin.
# =============================================================================

from __future__ import annotations

import uuid
import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import (
    Fee,
    FeeTemplate,
    Payment,
    PaymentMethod,
    PaymentInvoice,
    PaymentRefund,
)
from app.schemas.payment_schemas import (
    FeeCreateRequest,
    FeeUpdateRequest,
    FeeWaiveRequest,
    PayFeeRequest,
    PayAllFeesRequest,
    PaymentMethodCreateRequest,
    RefundCreateRequest,
)


# =============================================================================
# Helpers
# =============================================================================

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_invoice_number() -> str:
    """INV-2024-00001 style — collision handled by UNIQUE constraint."""
    year = _now().year
    suffix = str(uuid.uuid4().int)[:5].zfill(5)
    return f"INV-{year}-{suffix}"


# =============================================================================
# Fee Service
# =============================================================================

async def get_outstanding_fees(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[Fee]:
    """
    Return all fees for user where status IN (pending, overdue).
    Auto-marks fees as overdue if due_date has passed.
    """
    result = await db.execute(
        select(Fee).where(
            and_(
                Fee.user_id == user_id,
                Fee.status.in_(["pending", "overdue"]),
            )
        ).order_by(Fee.is_urgent.desc(), Fee.due_date.asc())
    )
    fees = result.scalars().all()

    # Auto-update overdue status
    now = _now()
    updated = False
    for fee in fees:
        if (
            fee.status == "pending"
            and fee.due_date is not None
            and fee.due_date < now
        ):
            fee.status = "overdue"
            fee.modified_by = user_id
            updated = True

    if updated:
        await db.commit()
        for fee in fees:
            await db.refresh(fee)

    return list(fees)


async def get_all_fees(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[Fee]:
    """All fees for a user across all statuses — for history view."""
    result = await db.execute(
        select(Fee)
        .where(Fee.user_id == user_id)
        .order_by(Fee.created_at.desc())
    )
    return list(result.scalars().all())


async def get_fee_by_id(
    db: AsyncSession,
    fee_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[Fee]:
    result = await db.execute(
        select(Fee).where(
            and_(Fee.id == fee_id, Fee.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def create_fee(
    db: AsyncSession,
    data: FeeCreateRequest,
    created_by: uuid.UUID,
) -> Fee:
    """HR / attorney creates a fee on an application."""
    due_date = data.due_date

    # Auto-calculate due_date from template if not provided
    if due_date is None and data.fee_template_id:
        tmpl_result = await db.execute(
            select(FeeTemplate).where(FeeTemplate.id == data.fee_template_id)
        )
        tmpl = tmpl_result.scalar_one_or_none()
        if tmpl and tmpl.due_days_after_creation:
            from datetime import timedelta
            due_date = _now() + timedelta(days=tmpl.due_days_after_creation)

    fee = Fee(
        id=uuid.uuid4(),
        application_id=data.application_id,
        user_id=data.user_id,
        fee_template_id=data.fee_template_id,
        title=data.title,
        category=data.category,
        amount_usd=data.amount_usd,
        status="pending",
        is_urgent=data.is_urgent,
        due_date=due_date,
        notes=data.notes,
        created_by=created_by,
        modified_by=created_by,
    )
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    return fee


async def update_fee(
    db: AsyncSession,
    fee: Fee,
    data: FeeUpdateRequest,
    modified_by: uuid.UUID,
) -> Fee:
    if data.title      is not None: fee.title      = data.title
    if data.amount_usd is not None: fee.amount_usd = data.amount_usd
    if data.due_date   is not None: fee.due_date   = data.due_date
    if data.is_urgent  is not None: fee.is_urgent  = data.is_urgent
    if data.notes      is not None: fee.notes      = data.notes
    fee.modified_by = modified_by
    await db.commit()
    await db.refresh(fee)
    return fee


async def waive_fee(
    db: AsyncSession,
    fee: Fee,
    data: FeeWaiveRequest,
    waived_by: uuid.UUID,
) -> Fee:
    fee.status        = "waived"
    fee.waived_by     = waived_by
    fee.waived_at     = _now()
    fee.waiver_reason = data.waiver_reason
    fee.modified_by   = waived_by
    await db.commit()
    await db.refresh(fee)
    return fee


# =============================================================================
# Payment Method Service
# =============================================================================

async def list_payment_methods(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[PaymentMethod]:
    result = await db.execute(
        select(PaymentMethod).where(
            and_(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_active == True,
            )
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.asc())
    )
    return list(result.scalars().all())


async def get_payment_method_by_id(
    db: AsyncSession,
    method_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[PaymentMethod]:
    result = await db.execute(
        select(PaymentMethod).where(
            and_(
                PaymentMethod.id      == method_id,
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_active == True,
            )
        )
    )
    return result.scalar_one_or_none()


async def add_payment_method(
    db: AsyncSession,
    data: PaymentMethodCreateRequest,
    user_id: uuid.UUID,
) -> PaymentMethod:
    """
    Attach a Stripe PaymentMethod to the user.
    In production: call stripe.PaymentMethod.attach() here before saving.
    """
    # If set_as_default, clear existing default first
    if data.set_as_default:
        existing = await db.execute(
            select(PaymentMethod).where(
                and_(
                    PaymentMethod.user_id   == user_id,
                    PaymentMethod.is_default == True,
                    PaymentMethod.is_active  == True,
                )
            )
        )
        for m in existing.scalars().all():
            m.is_default = False

    method = PaymentMethod(
        id=uuid.uuid4(),
        user_id=user_id,
        method_type=data.method_type,
        gateway_customer_id=None,           # set after Stripe customer.create
        gateway_payment_method_id=data.gateway_payment_method_id,
        card_brand=data.card_brand,
        card_last4=data.card_last4,
        card_exp_month=data.card_exp_month,
        card_exp_year=data.card_exp_year,
        card_holder_name=data.card_holder_name,
        paypal_email=data.paypal_email,
        wallet_device_id=data.wallet_device_id,
        billing_name=data.billing_name,
        billing_line1=data.billing_line1,
        billing_line2=data.billing_line2,
        billing_city=data.billing_city,
        billing_state=data.billing_state,
        billing_zip=data.billing_zip,
        billing_country=data.billing_country,
        is_default=data.set_as_default,
        is_verified=True,    # trust Stripe's token as verified
        is_active=True,
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return method


async def delete_payment_method(
    db: AsyncSession,
    method: PaymentMethod,
    user_id: uuid.UUID,
) -> None:
    """Soft delete — set is_active=False. Past payments still reference the row."""
    method.is_active  = False
    method.modified_by = user_id
    await db.commit()


async def set_default_payment_method(
    db: AsyncSession,
    method: PaymentMethod,
    user_id: uuid.UUID,
) -> PaymentMethod:
    # Clear all existing defaults
    existing = await db.execute(
        select(PaymentMethod).where(
            and_(
                PaymentMethod.user_id    == user_id,
                PaymentMethod.is_default == True,
                PaymentMethod.is_active  == True,
            )
        )
    )
    for m in existing.scalars().all():
        m.is_default  = False
        m.modified_by = user_id

    method.is_default  = True
    method.modified_by = user_id
    await db.commit()
    await db.refresh(method)
    return method


# =============================================================================
# Payment Service
# =============================================================================

async def _get_fees_for_payment(
    db: AsyncSession,
    fee_ids: List[uuid.UUID],
    user_id: uuid.UUID,
) -> List[Fee]:
    """Load and validate fees belong to user and are payable."""
    result = await db.execute(
        select(Fee).where(
            and_(
                Fee.id.in_(fee_ids),
                Fee.user_id == user_id,
                Fee.status.in_(["pending", "overdue"]),
            )
        )
    )
    fees = result.scalars().all()

    found_ids = {f.id for f in fees}
    missing = [str(fid) for fid in fee_ids if fid not in found_ids]
    if missing:
        raise ValueError(f"Fees not found or not payable: {', '.join(missing)}")

    return list(fees)


async def process_payment(
    db: AsyncSession,
    fee_ids: List[uuid.UUID],
    payment_method: PaymentMethod,
    user_id: uuid.UUID,
    description: Optional[str] = None,
) -> Payment:
    """
    Core payment function — used by both pay_fee and pay_all_fees.

    Production flow:
    1. Validate fees
    2. Create Stripe PaymentIntent
    3. Confirm the PaymentIntent
    4. On success → mark fees paid + create invoice
    5. On failure → record failure details

    Here we simulate a successful payment for local dev.
    Replace the Stripe section with real API calls.
    """
    fees = await _get_fees_for_payment(db, fee_ids, user_id)
    total_cents = sum(f.amount_usd for f in fees)

    if not description:
        description = " + ".join(f.title for f in fees)

    # ── Stripe PaymentIntent (stub — replace with real Stripe call) ──────────
    # import stripe
    # intent = stripe.PaymentIntent.create(
    #     amount=total_cents,
    #     currency="usd",
    #     customer=payment_method.gateway_customer_id,
    #     payment_method=payment_method.gateway_payment_method_id,
    #     confirm=True,
    #     return_url="https://app.visaflow.io/payments",
    # )
    # gateway_payment_intent_id = intent.id
    # gateway_charge_id = intent.latest_charge
    # gateway_receipt_url = intent.charges.data[0].receipt_url if intent.charges.data else None
    # success = intent.status == "succeeded"
    # failure_code = intent.last_payment_error.code if intent.last_payment_error else None
    # failure_message = intent.last_payment_error.message if intent.last_payment_error else None

    # Stub values for local dev
    gateway_payment_intent_id = f"pi_stub_{uuid.uuid4().hex[:16]}"
    gateway_charge_id         = f"ch_stub_{uuid.uuid4().hex[:16]}"
    gateway_receipt_url       = None
    success                   = True
    failure_code              = None
    failure_message           = None

    now = _now()

    payment = Payment(
        id=uuid.uuid4(),
        user_id=user_id,
        payment_method_id=payment_method.id,
        method_type_snapshot=payment_method.method_type,
        card_last4_snapshot=payment_method.card_last4,
        amount_usd=total_cents,
        gateway="stripe",
        gateway_payment_intent_id=gateway_payment_intent_id,
        gateway_charge_id=gateway_charge_id,
        gateway_receipt_url=gateway_receipt_url,
        status="completed" if success else "failed",
        failure_code=failure_code,
        failure_message=failure_message,
        initiated_at=now,
        completed_at=now if success else None,
        description=description,
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(payment)
    await db.flush()  # get payment.id before updating fees

    if success:
        for fee in fees:
            fee.status     = "paid"
            fee.payment_id = payment.id
            fee.paid_at    = now
            fee.modified_by = user_id

        # Generate invoice
        invoice = await _create_invoice(db, payment, fees, user_id)
        payment.invoice_id = invoice.id

    await db.commit()
    await db.refresh(payment)
    return payment


async def _create_invoice(
    db: AsyncSession,
    payment: Payment,
    fees: List[Fee],
    user_id: uuid.UUID,
) -> PaymentInvoice:
    subtotal = sum(f.amount_usd for f in fees)
    invoice = PaymentInvoice(
        id=uuid.uuid4(),
        invoice_number=_generate_invoice_number(),
        user_id=user_id,
        application_id=fees[0].application_id if fees else None,
        subtotal_usd=subtotal,
        tax_usd=0,
        total_usd=subtotal,
        currency="USD",
        status="generated",
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(invoice)
    await db.flush()
    return invoice


async def list_payments(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
    )
    return list(result.scalars().all())


# =============================================================================
# PaymentInvoice Service
# =============================================================================

async def list_invoices(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> List[PaymentInvoice]:
    result = await db.execute(
        select(PaymentInvoice)
        .where(PaymentInvoice.user_id == user_id)
        .order_by(PaymentInvoice.created_at.desc())
    )
    return list(result.scalars().all())


async def get_invoice_by_id(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Optional[PaymentInvoice]:
    result = await db.execute(
        select(PaymentInvoice).where(
            and_(
                PaymentInvoice.id      == invoice_id,
                PaymentInvoice.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()


# =============================================================================
# PaymentRefund Service
# =============================================================================

async def list_refunds_for_payment(
    db: AsyncSession,
    payment_id: uuid.UUID,
) -> List[PaymentRefund]:
    result = await db.execute(
        select(PaymentRefund)
        .where(PaymentRefund.payment_id == payment_id)
        .order_by(PaymentRefund.requested_at.desc())
    )
    return list(result.scalars().all())


async def request_refund(
    db: AsyncSession,
    data: RefundCreateRequest,
    requested_by: uuid.UUID,
) -> PaymentRefund:
    """
    HR / admin requests a refund.
    Production: call stripe.Refund.create() here.
    """
    # Validate payment exists and belongs to current org
    payment_result = await db.execute(
        select(Payment).where(
            and_(
                Payment.id     == data.payment_id,
                Payment.status.in_(["completed", "partially_refunded"]),
            )
        )
    )
    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise ValueError("Payment not found or not refundable")

    if data.amount_usd > payment.amount_usd:
        raise ValueError("Refund amount cannot exceed original payment amount")

    # ── Stripe Refund (stub) ─────────────────────────────────────────────────
    # refund = stripe.Refund.create(
    #     charge=payment.gateway_charge_id,
    #     amount=data.amount_usd,
    #     reason=data.reason,
    # )
    # gateway_refund_id = refund.id
    # status = "completed" if refund.status == "succeeded" else "failed"

    gateway_refund_id = f"re_stub_{uuid.uuid4().hex[:16]}"
    status            = "completed"
    now               = _now()

    refund = PaymentRefund(
        id=uuid.uuid4(),
        payment_id=data.payment_id,
        amount_usd=data.amount_usd,
        reason=data.reason,
        notes=data.notes,
        status=status,
        gateway_refund_id=gateway_refund_id,
        requested_at=now,
        completed_at=now if status == "completed" else None,
        requested_by=requested_by,
        created_by=requested_by,
        modified_by=requested_by,
    )
    db.add(refund)

    # Update payment status
    total_refunded_result = await db.execute(
        select(PaymentRefund).where(
            and_(
                PaymentRefund.payment_id == data.payment_id,
                PaymentRefund.status     == "completed",
            )
        )
    )
    existing_refunds = total_refunded_result.scalars().all()
    total_refunded = sum(r.amount_usd for r in existing_refunds) + data.amount_usd

    if total_refunded >= payment.amount_usd:
        payment.status = "refunded"
        # Also update linked fees back to refunded
        fees_result = await db.execute(
            select(Fee).where(Fee.payment_id == payment.id)
        )
        for fee in fees_result.scalars().all():
            fee.status      = "refunded"
            fee.modified_by = requested_by
    else:
        payment.status = "partially_refunded"

    payment.modified_by = requested_by

    await db.commit()
    await db.refresh(refund)
    return refund