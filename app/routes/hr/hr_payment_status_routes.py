# app/routes/hr/hr_payment_status_routes.py
#
# HR's side of the payment-status relay.
# Register in main.py alongside the other hr_* routers:
#
#   from app.routes.hr.hr_payment_status_routes import hr_payment_status_router
#   app.include_router(hr_payment_status_router, prefix="/api/v1/hr", tags=["HR Payment Status"])

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.attorney.payment_status import (
    PaymentStatusResponse,
    PaymentStatusListResponse,
)
from app.services.attorney.payment_status_service import (
    hr_list_payment_statuses,
    hr_relay_payment_status_to_employee,
)

hr_payment_status_router = APIRouter()


@hr_payment_status_router.get(
    "/cases/{application_id}/payment-status",
    response_model=PaymentStatusListResponse,
    summary="HR: list payment status updates the attorney has recorded on this case",
)
async def api_hr_list_payment_statuses(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> PaymentStatusListResponse:
    return await hr_list_payment_statuses(db, application_id, current_user.user_id)


@hr_payment_status_router.patch(
    "/cases/{application_id}/payment-status/{payment_status_id}/notify-employee",
    response_model=PaymentStatusResponse,
    summary="HR: relay a payment status update to the employee",
)
async def api_hr_relay_payment_status(
    application_id: uuid.UUID,
    payment_status_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> PaymentStatusResponse:
    return await hr_relay_payment_status_to_employee(
        db, application_id, payment_status_id, current_user.user_id,
    )