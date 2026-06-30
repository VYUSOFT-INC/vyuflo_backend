# =============================================================================
# app/schemas/payment_schemas.py
# Pydantic v2 schemas for all payment-related models.
# Mirrors visamodels.py tables: FeeTemplate(43), Fee(44),
# PaymentMethod(45), Payment(46), PaymentInvoice(47), PaymentRefund(48)
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


# =============================================================================
# Shared config — all response schemas use this
# =============================================================================

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# FeeTemplate schemas (TABLE 43)
# =============================================================================

class FeeTemplateOut(ORMBase):
    id:                    uuid.UUID
    code:                  str
    name:                  str
    description:           Optional[str]
    category:              str
    visa_type_id:          Optional[uuid.UUID]
    default_amount_usd:    int          # US cents
    is_government_fee:     bool
    is_optional:           bool
    due_days_after_creation: Optional[int]
    sort_order:            int
    is_active:             bool
    created_at:            datetime
    updated_at:            datetime


# =============================================================================
# Fee schemas (TABLE 44)
# =============================================================================

class FeeOut(ORMBase):
    id:              uuid.UUID
    application_id:  uuid.UUID
    user_id:         uuid.UUID
    fee_template_id: Optional[uuid.UUID]
    title:           str
    category:        str
    amount_usd:      int          # US cents  e.g. 280500 = $2,805.00
    status:          str          # pending | paid | overdue | waived | refunded | cancelled
    is_urgent:       bool
    due_date:        Optional[datetime]
    payment_id:      Optional[uuid.UUID]
    paid_at:         Optional[datetime]
    waived_by:       Optional[uuid.UUID]
    waived_at:       Optional[datetime]
    waiver_reason:   Optional[str]
    notes:           Optional[str]
    created_at:      datetime
    updated_at:      datetime


class FeeCreateRequest(BaseModel):
    """HR / attorney creates a fee on an application."""
    application_id:  uuid.UUID
    user_id:         uuid.UUID
    fee_template_id: Optional[uuid.UUID] = None
    title:           str
    category:        str = "filing_fee"
    amount_usd:      int           # US cents
    due_date:        Optional[datetime] = None
    is_urgent:       bool = False
    notes:           Optional[str] = None


class FeeWaiveRequest(BaseModel):
    """HR / admin waives a fee."""
    waiver_reason: str


class FeeUpdateRequest(BaseModel):
    """HR updates fee details."""
    title:      Optional[str]     = None
    amount_usd: Optional[int]     = None
    due_date:   Optional[datetime] = None
    is_urgent:  Optional[bool]    = None
    notes:      Optional[str]     = None


# =============================================================================
# PaymentMethod schemas (TABLE 45)
# =============================================================================

class PaymentMethodOut(ORMBase):
    id:               uuid.UUID
    user_id:          uuid.UUID
    method_type:      str   # credit_card | debit_card | paypal | apple_pay | google_pay | bank_transfer
    card_brand:       Optional[str]
    card_last4:       Optional[str]
    card_exp_month:   Optional[int]
    card_exp_year:    Optional[int]
    card_holder_name: Optional[str]
    paypal_email:     Optional[str]
    billing_name:     Optional[str]
    billing_city:     Optional[str]
    billing_state:    Optional[str]
    billing_country:  Optional[str]
    is_default:       bool
    is_verified:      bool
    is_active:        bool
    created_at:       datetime
    updated_at:       datetime


class PaymentMethodCreateRequest(BaseModel):
    """
    Frontend sends Stripe PaymentMethod ID (from Stripe.js / Elements).
    Backend calls Stripe to attach it to the customer.
    NEVER send raw card numbers.
    """
    method_type:               str         # credit_card | paypal | apple_pay ...
    gateway_payment_method_id: str         # Stripe pm_xxx / PayPal token
    card_brand:                Optional[str]   = None
    card_last4:                Optional[str]   = None
    card_exp_month:            Optional[int]   = None
    card_exp_year:             Optional[int]   = None
    card_holder_name:          Optional[str]   = None
    paypal_email:              Optional[str]   = None
    wallet_device_id:          Optional[str]   = None
    billing_name:              Optional[str]   = None
    billing_line1:             Optional[str]   = None
    billing_line2:             Optional[str]   = None
    billing_city:              Optional[str]   = None
    billing_state:             Optional[str]   = None
    billing_zip:               Optional[str]   = None
    billing_country:           Optional[str]   = None
    set_as_default:            bool            = False


# =============================================================================
# Payment schemas (TABLE 46)
# =============================================================================

class PaymentOut(ORMBase):
    id:                        uuid.UUID
    user_id:                   uuid.UUID
    payment_method_id:         Optional[uuid.UUID]
    method_type_snapshot:      str
    card_last4_snapshot:       Optional[str]
    amount_usd:                int       # US cents
    gateway:                   str
    gateway_payment_intent_id: Optional[str]
    gateway_receipt_url:       Optional[str]
    status:                    str       # pending | processing | completed | failed | cancelled | refunded | partially_refunded
    failure_code:              Optional[str]
    failure_message:           Optional[str]
    initiated_at:              Optional[datetime]
    completed_at:              Optional[datetime]
    invoice_id:                Optional[uuid.UUID]
    description:               Optional[str]
    created_at:                datetime
    updated_at:                datetime


class PayFeeRequest(BaseModel):
    """Pay a single fee."""
    fee_id:            uuid.UUID
    payment_method_id: uuid.UUID


class PayAllFeesRequest(BaseModel):
    """Pay all outstanding fees in one transaction."""
    fee_ids:           List[uuid.UUID]
    payment_method_id: uuid.UUID

    @field_validator("fee_ids")
    @classmethod
    def must_not_be_empty(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if not v:
            raise ValueError("fee_ids must contain at least one fee")
        return v


# =============================================================================
# PaymentInvoice schemas (TABLE 47)
# =============================================================================

class PaymentInvoiceOut(ORMBase):
    id:              uuid.UUID
    invoice_number:  str
    user_id:         uuid.UUID
    application_id:  Optional[uuid.UUID]
    subtotal_usd:    int       # US cents
    tax_usd:         int
    total_usd:       int
    currency:        str
    pdf_url:         Optional[str]
    pdf_generated_at: Optional[datetime]
    status:          str       # pending | generated | sent | voided
    sent_at:         Optional[datetime]
    voided_at:       Optional[datetime]
    void_reason:     Optional[str]
    created_at:      datetime
    updated_at:      datetime


# =============================================================================
# PaymentRefund schemas (TABLE 48)
# =============================================================================

class PaymentRefundOut(ORMBase):
    id:                uuid.UUID
    payment_id:        uuid.UUID
    amount_usd:        int       # US cents
    reason:            str
    notes:             Optional[str]
    status:            str       # pending | processing | completed | failed
    gateway_refund_id: Optional[str]
    requested_at:      datetime
    completed_at:      Optional[datetime]
    requested_by:      Optional[uuid.UUID]
    approved_by:       Optional[uuid.UUID]
    created_at:        datetime
    updated_at:        datetime


class RefundCreateRequest(BaseModel):
    """HR / admin requests a refund on a completed payment."""
    payment_id: uuid.UUID
    amount_usd: int        # US cents — if less than payment.amount_usd → partial refund
    reason:     str = "other"
    notes:      Optional[str] = None


# =============================================================================
# Aggregated response — total due summary
# =============================================================================

class OutstandingFeeSummary(BaseModel):
    fees:       List[FeeOut]
    total_due:  int          # sum of all pending/overdue fee.amount_usd in cents
    urgent_count: int