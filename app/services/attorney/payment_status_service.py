# app/services/attorney/payment_status_service.py
#
# Two-step relay for "attorney is currently processing a payment" status
# updates. Mirrors the exact same "HR is the deliberate checkpoint" pattern
# already used for document assignment (hr_approval_service.py) and the
# task relay state machine (task_relay.py):
#
#   1. attorney_mark_payment_in_progress() — attorney creates the status,
#      HR is notified immediately.
#   2. hr_relay_payment_status_to_employee() — HR's explicit action that
#      passes it on to the employee. Idempotent: a status already relayed
#      cannot be relayed again (409), matching the same guard used
#      elsewhere in this codebase for one-way state transitions.

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visamodels import Application, PaymentStatusUpdate, User, Notification
from app.schemas.attorney.payment_status import (
    PaymentStatusCreate,
    PaymentStatusResponse,
    PaymentStatusListResponse,
)
from app.services.employee.services import db_create, db_update, db_get_by_id


def _user_name(user: Optional[User]) -> str:
    if user is None:
        return "Unknown"
    first = (user.first_name or "").strip()
    last  = (user.last_name  or "").strip()
    name  = f"{first} {last}".strip()
    return name if name else (user.email or "Unknown")


FILING_TYPE_LABEL = {
    "lca":          "LCA (Labor Condition Application)",
    "petition":     "Petition (I-129 / I-140)",
    "rfe_response": "RFE Response",
    "appeal":       "Appeal",
}


async def _build_response(db: AsyncSession, row: PaymentStatusUpdate) -> PaymentStatusResponse:
    creator = await db_get_by_id(db, User, row.created_by_user)
    resp = PaymentStatusResponse.model_validate(row)
    resp.created_by_name = _user_name(creator)
    return resp


# =============================================================================
# 1. ATTORNEY MARKS A PAYMENT IN PROGRESS
# =============================================================================

async def attorney_mark_payment_in_progress(
    db: AsyncSession,
    application_id: uuid.UUID,
    payload: PaymentStatusCreate,
    attorney_user_id: uuid.UUID,
) -> PaymentStatusResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Case not found.")
    if application.assigned_attorney_id != attorney_user_id:
        raise HTTPException(status_code=403, detail="You are not the assigned attorney for this case.")

    row = PaymentStatusUpdate(
        application_id  = application_id,
        filing_type     = payload.filing_type,
        note            = payload.note,
        created_by_user = attorney_user_id,
        created_by      = attorney_user_id,
    )
    row = await db_create(db, row)

    label = FILING_TYPE_LABEL.get(payload.filing_type, payload.filing_type)

    # Notify HR only — the employee hears nothing until HR explicitly relays it.
    try:
        if application.assigned_hr_id:
            db.add(Notification(
                id=uuid.uuid4(),
                user_id=application.assigned_hr_id,
                notification_type="payment_in_progress",
                category="case_update",
                priority="medium",
                title=f"Attorney is processing: {label}",
                body=payload.note or f"Attorney has started the {label} payment process.",
                application_id=application_id,
                actor_id=attorney_user_id,
                created_by=attorney_user_id,
            ))
    except Exception as e:
        print(f"[attorney_mark_payment_in_progress] notification failed: {e}")

    return await _build_response(db, row)


# =============================================================================
# 2. HR LISTS PAYMENT STATUS UPDATES FOR A CASE
# =============================================================================

async def hr_list_payment_statuses(
    db: AsyncSession,
    application_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> PaymentStatusListResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Case not found.")
    if application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    result = await db.execute(
        select(PaymentStatusUpdate)
        .where(PaymentStatusUpdate.application_id == application_id)
        .order_by(PaymentStatusUpdate.created_at.desc())
    )
    rows = result.scalars().all()
    items = [await _build_response(db, r) for r in rows]
    return PaymentStatusListResponse(items=items, total=len(items))


# =============================================================================
# 3. HR RELAYS A PAYMENT STATUS TO THE EMPLOYEE — the explicit gate
# =============================================================================

async def hr_relay_payment_status_to_employee(
    db: AsyncSession,
    application_id: uuid.UUID,
    payment_status_id: uuid.UUID,
    hr_user_id: uuid.UUID,
) -> PaymentStatusResponse:
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Case not found.")
    if application.assigned_hr_id != hr_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    row = await db_get_by_id(db, PaymentStatusUpdate, payment_status_id)
    if not row or row.application_id != application_id:
        raise HTTPException(status_code=404, detail="Payment status update not found.")
    if row.relayed_to_employee_at is not None:
        raise HTTPException(
            status_code=409,
            detail="This update has already been shared with the employee.",
        )

    await db_update(db, PaymentStatusUpdate, payment_status_id, {
        "relayed_to_employee_at": datetime.now(timezone.utc),
        "relayed_to_employee_by": hr_user_id,
        "modified_by":            hr_user_id,
    })

    label = FILING_TYPE_LABEL.get(row.filing_type, row.filing_type)

    try:
        db.add(Notification(
            id=uuid.uuid4(),
            user_id=application.user_id,
            notification_type="payment_in_progress",
            category="case_update",
            priority="medium",
            title=f"Your attorney is processing: {label}",
            body=row.note or f"Your attorney has started the {label} payment process.",
            application_id=application_id,
            actor_id=hr_user_id,
            created_by=hr_user_id,
        ))
    except Exception as e:
        print(f"[hr_relay_payment_status_to_employee] notification failed: {e}")

    updated = await db_get_by_id(db, PaymentStatusUpdate, payment_status_id)
    return await _build_response(db, updated)


# =============================================================================
# 4. LIST — used by BOTH the attorney's own case page (to see status/history,
#    same access pattern as list_filings) and could back an employee-facing
#    view later if one exists (not built here — no employee frontend seen).
# =============================================================================

async def list_payment_statuses_for_case(
    db: AsyncSession,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PaymentStatusListResponse:
    """
    GET /lawyer/applications/{id}/payment-status

    Allows either the case's assigned attorney OR its assigned HR user —
    same access rule as list_filings() in new_case_service.py.
    """
    application = await db_get_by_id(db, Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Case not found.")
    if user_id not in (application.assigned_attorney_id, application.assigned_hr_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    result = await db.execute(
        select(PaymentStatusUpdate)
        .where(PaymentStatusUpdate.application_id == application_id)
        .order_by(PaymentStatusUpdate.created_at.desc())
    )
    rows = result.scalars().all()
    items = [await _build_response(db, r) for r in rows]
    return PaymentStatusListResponse(items=items, total=len(items))