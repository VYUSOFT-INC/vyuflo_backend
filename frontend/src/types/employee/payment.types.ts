// src/types/payment.types.ts
// Mirrors visamodels.py: Fee, PaymentMethod, Payment, PaymentInvoice, PaymentRefund

// ── Enums ────────────────────────────────────────────────────────────────────

export type FeeCategory =
  | "filing_fee"
  | "premium_processing"
  | "biometrics"
  | "attorney_fee"
  | "document_fee"
  | "other";

export type FeeStatus =
  | "pending"
  | "paid"
  | "overdue"
  | "waived"
  | "refunded"
  | "cancelled";

export type PaymentMethodType =
  | "credit_card"
  | "debit_card"
  | "paypal"
  | "apple_pay"
  | "google_pay"
  | "bank_transfer";

export type CardBrand = "visa" | "mastercard" | "amex" | "discover" | "other";

export type PaymentStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "refunded"
  | "partially_refunded";

export type PaymentGateway =
  | "stripe"
  | "braintree"
  | "paypal"
  | "apple_pay"
  | "manual";

export type InvoiceStatus = "pending" | "generated" | "sent" | "voided";

export type RefundStatus = "pending" | "processing" | "completed" | "failed";

export type RefundReason =
  | "duplicate_payment"
  | "application_withdrawn"
  | "fee_waived"
  | "overpayment"
  | "admin_adjustment"
  | "other";

// ── Models ───────────────────────────────────────────────────────────────────

export interface Fee {
  id: string;
  application_id: string;
  user_id: string;
  fee_template_id: string | null;
  title: string;
  category: FeeCategory;
  amount_usd: number; // US cents
  status: FeeStatus;
  is_urgent: boolean;
  due_date: string | null; // ISO datetime
  payment_id: string | null;
  paid_at: string | null;
  waived_by: string | null;
  waived_at: string | null;
  waiver_reason: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentMethod {
  id: string;
  user_id: string;
  method_type: PaymentMethodType;
  card_brand: CardBrand | null;
  card_last4: string | null;
  card_exp_month: number | null;
  card_exp_year: number | null;
  card_holder_name: string | null;
  paypal_email: string | null;
  billing_name: string | null;
  billing_city: string | null;
  billing_state: string | null;
  billing_country: string | null;
  is_default: boolean;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  user_id: string;
  payment_method_id: string | null;
  method_type_snapshot: PaymentMethodType;
  card_last4_snapshot: string | null;
  amount_usd: number; // US cents
  gateway: PaymentGateway;
  gateway_receipt_url: string | null;
  status: PaymentStatus;
  failure_code: string | null;
  failure_message: string | null;
  initiated_at: string | null;
  completed_at: string | null;
  invoice_id: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentInvoice {
  id: string;
  invoice_number: string;
  user_id: string;
  application_id: string | null;
  subtotal_usd: number; // cents
  tax_usd: number;
  total_usd: number;
  currency: string;
  pdf_url: string | null;
  status: InvoiceStatus;
  sent_at: string | null;
  created_at: string;
}

export interface PaymentRefund {
  id: string;
  payment_id: string;
  amount_usd: number; // cents
  reason: RefundReason;
  notes: string | null;
  status: RefundStatus;
  requested_at: string;
  completed_at: string | null;
}

// ── Request / Response shapes ─────────────────────────────────────────────────

export interface PayFeeRequest {
  fee_id: string;
  payment_method_id: string;
}

export interface PayAllFeesRequest {
  fee_ids: string[];
  payment_method_id: string;
}

export interface AddPaymentMethodRequest {
  method_type: PaymentMethodType;
  gateway_payment_method_id: string; // Stripe PaymentMethod ID from frontend SDK
  card_brand?: CardBrand;
  card_last4?: string;
  card_exp_month?: number;
  card_exp_year?: number;
  card_holder_name?: string;
  paypal_email?: string;
  billing_name?: string;
  billing_line1?: string;
  billing_city?: string;
  billing_state?: string;
  billing_zip?: string;
  billing_country?: string;
  set_as_default?: boolean;
}

// ── Utility helpers ───────────────────────────────────────────────────────────

/** Convert US cents integer to formatted dollar string: 280500 → "$2,805.00" */
export function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}
