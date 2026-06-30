# =============================================================================
# app/api/v1/payment_routes.py
# All FastAPI routes for the Payments screen.
# Register in main.py:
#   from app.api.v1.payment_routes import payment_router as payment_router
#   app.include_router(payment_router, prefix="/api/v1", tags=["payments"])
# =============================================================================

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user   # your existing JWT dep
from app.models.visamodels import User
from app.schemas.employee.payment_schemas import (
    FeeOut,
    FeeCreateRequest,
    FeeUpdateRequest,
    FeeWaiveRequest,
    PaymentMethodOut,
    PaymentMethodCreateRequest,
    PaymentOut,
    PayFeeRequest,
    PayAllFeesRequest,
    PaymentInvoiceOut,
    PaymentRefundOut,
    RefundCreateRequest,
    OutstandingFeeSummary,
)
from app.services.employee.payment_service import (
    # Fees
    get_outstanding_fees,
    get_all_fees,
    get_fee_by_id,
    create_fee,
    update_fee,
    waive_fee,
    # Payment methods
    list_payment_methods,
    get_payment_method_by_id,
    add_payment_method,
    delete_payment_method,
    set_default_payment_method,
    # Payments
    process_payment,
    list_payments,
    # Invoices
    list_invoices,
    get_invoice_by_id,
    # Refunds
    list_refunds_for_payment,
    request_refund,
)

payment_router = APIRouter()


# =============================================================================
# ── FEES ─────────────────────────────────────────────────────────────────────
# =============================================================================

@payment_router.get(
    "/fees/outstanding",
    response_model=OutstandingFeeSummary,
    summary="Get outstanding fees for current user",
)
async def api_get_outstanding_fees(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Returns all fees with status pending or overdue for the logged-in user.
    Also auto-promotes any past-due 'pending' fees to 'overdue'.
    Used by: Screen 18 — outstanding fee cards + Pay All banner.
    """
    fees = await get_outstanding_fees(db, current_user.user_id)
    return OutstandingFeeSummary(
        fees=fees,
        total_due=sum(f.amount_usd for f in fees),
        urgent_count=sum(1 for f in fees if f.is_urgent),
    )


@payment_router.get(
    "/fees",
    response_model=List[FeeOut],
    summary="Get all fees for current user",
)
async def api_get_all_fees(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """All fees across all statuses — for payment history view."""
    return await get_all_fees(db, current_user.user_id)


@payment_router.get(
    "/fees/{fee_id}",
    response_model=FeeOut,
    summary="Get a single fee by ID",
)
async def api_get_fee(
    fee_id:       uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    fee = await get_fee_by_id(db, fee_id, current_user.user_id)
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee not found")
    return fee


@payment_router.post(
    "/fees",
    response_model=FeeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a fee on an application (HR / attorney)",
)
async def api_create_fee(
    body:         FeeCreateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    HR or attorney creates a fee for an employee application.
    Accepts fee_template_id (optional) — if provided the due_date is
    auto-calculated from the template's due_days_after_creation.
    """
    return await create_fee(db, body, created_by=current_user.user_id)


@payment_router.patch(
    "/fees/{fee_id}",
    response_model=FeeOut,
    summary="Update fee details (HR / attorney)",
)
async def api_update_fee(
    fee_id:       uuid.UUID,
    body:         FeeUpdateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    fee = await get_fee_by_id(db, fee_id, current_user.user_id)
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee not found")
    if fee.status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update a fee with status '{fee.status}'",
        )
    return await update_fee(db, fee, body, modified_by=current_user.user_id)


@payment_router.post(
    "/fees/{fee_id}/waive",
    response_model=FeeOut,
    summary="Waive a fee (HR / admin)",
)
async def api_waive_fee(
    fee_id:       uuid.UUID,
    body:         FeeWaiveRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    fee = await get_fee_by_id(db, fee_id, current_user.user_id)
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee not found")
    if fee.status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot waive a fee with status '{fee.status}'",
        )
    return await waive_fee(db, fee, body, waived_by=current_user.user_id)


# =============================================================================
# ── PAYMENT METHODS ───────────────────────────────────────────────────────────
# =============================================================================

@payment_router.get(
    "/payment-methods",
    response_model=List[PaymentMethodOut],
    summary="List saved payment methods",
)
async def api_list_payment_methods(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Returns all active payment methods for the user.
    Default method is returned first.
    Used by: Screen 18 — payment method selector.
    """
    return await list_payment_methods(db, current_user.user_id)


@payment_router.post(
    "/payment-methods",
    response_model=PaymentMethodOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new payment method",
)
async def api_add_payment_method(
    body:         PaymentMethodCreateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Attach a new payment method to the user's account.
    Frontend should first tokenise the card via Stripe.js / Stripe Elements
    and pass the resulting pm_xxx as gateway_payment_method_id.
    NEVER send raw card numbers to this endpoint.
    """
    return await add_payment_method(db, body, user_id=current_user.user_id)


@payment_router.delete(
    "/payment-methods/{method_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a saved payment method",
)
async def api_delete_payment_method(
    method_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    method = await get_payment_method_by_id(db, method_id, current_user.user_id)
    if not method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    await delete_payment_method(db, method, user_id=current_user.user_id)


@payment_router.patch(
    "/payment-methods/{method_id}/set-default",
    response_model=PaymentMethodOut,
    summary="Set a payment method as default",
)
async def api_set_default_payment_method(
    method_id:    uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    method = await get_payment_method_by_id(db, method_id, current_user.user_id)
    if not method:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    return await set_default_payment_method(db, method, user_id=current_user.user_id)


# =============================================================================
# ── PAYMENTS ──────────────────────────────────────────────────────────────────
# =============================================================================

@payment_router.get(
    "/payments",
    response_model=List[PaymentOut],
    summary="Get payment history",
)
async def api_list_payments(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    All payment transactions for the current user, newest first.
    Used by: Screen 18 — Payment History tab.
    """
    return await list_payments(db, current_user.user_id)


@payment_router.post(
    "/payments/pay-fee",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Pay a single fee",
)
async def api_pay_fee(
    body:         PayFeeRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Pay one outstanding fee using a saved payment method.
    Creates a Payment row, marks the Fee as paid, generates an invoice.
    """
    method = await get_payment_method_by_id(db, body.payment_method_id, current_user.user_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
    try:
        return await process_payment(
            db=db,
            fee_ids=[body.fee_id],
            payment_method=method,
            user_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@payment_router.post(
    "/payments/pay-all",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Pay all outstanding fees in one transaction",
)
async def api_pay_all_fees(
    body:         PayAllFeesRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    Pay multiple outstanding fees in one Stripe PaymentIntent.
    Total = sum of all fee.amount_usd.
    Used by: 'Pay All Securely' button on Screen 18.
    """
    method = await get_payment_method_by_id(db, body.payment_method_id, current_user.user_id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found",
        )
    try:
        return await process_payment(
            db=db,
            fee_ids=list(body.fee_ids),
            payment_method=method,
            user_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# ── INVOICES ──────────────────────────────────────────────────────────────────
# =============================================================================

@payment_router.get(
    "/payment-invoices",
    response_model=List[PaymentInvoiceOut],
    summary="List invoices",
)
async def api_list_invoices(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    All invoices for the current user, newest first.
    Used by: Screen 18 — Invoices tab.
    """
    return await list_invoices(db, current_user.user_id)


@payment_router.get(
    "/payment-invoices/{invoice_id}",
    response_model=PaymentInvoiceOut,
    summary="Get a single invoice",
)
async def api_get_invoice(
    invoice_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    invoice = await get_invoice_by_id(db, invoice_id, current_user.user_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


# =============================================================================
# ── REFUNDS ───────────────────────────────────────────────────────────────────
# =============================================================================

@payment_router.get(
    "/payments/{payment_id}/refunds",
    response_model=List[PaymentRefundOut],
    summary="List refunds for a payment",
)
async def api_list_refunds(
    payment_id:   uuid.UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    return await list_refunds_for_payment(db, payment_id)


@payment_router.post(
    "/payments/refund",
    response_model=PaymentRefundOut,
    status_code=status.HTTP_201_CREATED,
    summary="Request a refund (HR / admin)",
)
async def api_request_refund(
    body:         RefundCreateRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """
    HR or admin requests a full or partial refund on a completed payment.
    Calls the Stripe Refund API and updates fee statuses automatically.
    """
    try:
        return await request_refund(db, body, requested_by=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))