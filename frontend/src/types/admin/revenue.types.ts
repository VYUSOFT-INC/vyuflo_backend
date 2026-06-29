// src/types/revenue.types.ts
//
// Types matching the Postman responses from the Revenue Dashboard endpoints.
// Backend sends both _cents (number) and _display (pre-formatted string) for
// money — the frontend should prefer the _display strings and use _cents only
// when raw numbers are needed for chart axis scaling / sorting.

/* ───── Shared primitives ───────────────────────────────────────────── */

export type KpiKey =
  | 'mrr'
  | 'arr'
  | 'active_subscribers'
  | 'net_revenue_churn';

export interface KpiMetric {
  value_cents:    number | null;   // numeric (for charts/sorting); null for non-money KPIs
  value_display:  string;          // pre-formatted, ready to render
  delta_display:  string | null;   // e.g. "12.5%" or null when not available
  delta_label:    string;          // e.g. "vs last month"
  delta_positive: boolean;
}

export interface FailingPaymentsSummary {
  count:                    number;
  mrr_at_risk_cents:        number;
  mrr_at_risk_display:      string;
}

/* ───── KPI section ─────────────────────────────────────────────────── */

export interface KpiSection {
  mrr:                KpiMetric;
  arr:                KpiMetric;
  active_subscribers: KpiMetric;
  net_revenue_churn:  KpiMetric;
  failing_payments:   FailingPaymentsSummary | null;
  data_as_of:         string;   // ISO date
  is_live:            boolean;
}

/* ───── Revenue trend (line chart) ──────────────────────────────────── */

export interface TrendDataPoint {
  month_label:        string;          // "Jul"
  month_date:         string;          // "2025-07"
  mrr_cents:          number;
  mrr_display:        string;          // "$0"
  target_mrr_cents:   number | null;
  target_mrr_display: string | null;
}

export interface TrendSection {
  data_points:       TrendDataPoint[];
  period_months:     number;
  y_axis_max_cents:  number;
  y_axis_step_cents: number;
}

/* ───── Plan distribution (donut chart) ─────────────────────────────── */

export interface PlanSlice {
  plan_id?:      string;
  plan_name:     string;          // "Enterprise" | "Professional" | "Starter" | ...
  mrr_cents:     number;
  mrr_display:   string;
  percentage:    number;          // 0–100
  color?:        string | null;   // optional hex from backend
}

export interface PlanDistributionSection {
  slices:            PlanSlice[];
  total_mrr_cents:   number;
  total_mrr_display: string;
}

/* ───── Recent transactions (table) ─────────────────────────────────── */

export type TransactionStatus = 'success' | 'failed' | 'pending';
export type PlanTier          = 'enterprise' | 'professional' | 'starter' | string;

export interface TransactionItem {
  id:              string;
  customer_name:   string;
  customer_email:  string;
  amount_cents:    number;
  amount_display:  string;        // "$899.00"
  plan:            PlanTier;
  plan_display?:   string;        // "Enterprise"
  date:            string;        // ISO; backend may also send "Oct 24, 2026" in date_display
  date_display?:   string;
  status:          TransactionStatus;
}

export interface TransactionsSection {
  items:       TransactionItem[];
  total:       number;
  page:        number;
  page_size:   number;
  total_pages: number;
}

/* ───── Trial conversions (bar chart) ───────────────────────────────── */

export interface TrialConversionDataPoint {
  month_label:         string;
  month_date:          string;
  new_trials:          number;
  converted_trials:    number;
  churned_trials:      number;
  conversion_rate_pct: number;
}

export interface TrialConversionsSection {
  data_points:             TrialConversionDataPoint[];
  period_months:           number;
  total_new_trials:        number;
  total_converted:         number;
  total_churned:           number;
  avg_conversion_rate_pct: number;
}

/* ───── Failing payments (detailed list) ────────────────────────────── */

export interface FailingPaymentItem {
  id:                  string;
  customer_name:       string;
  customer_email:      string;
  amount_cents:        number;
  amount_display:      string;
  plan:                PlanTier;
  plan_display?:       string;
  failed_at:           string;
  failed_at_display?:  string;
  reason?:             string;
}

export interface FailingPaymentsSection {
  items:                     FailingPaymentItem[];
  total:                     number;
  total_mrr_at_risk_cents:   number;
  total_mrr_at_risk_display: string;
  page:                      number;
  page_size:                 number;
  total_pages:               number;
}

/* ───── Combined dashboard response ─────────────────────────────────── */

export interface RevenueDashboardResponse {
  kpi:               KpiSection;
  trend:             TrendSection;
  plan_distribution: PlanDistributionSection;
  transactions:      TransactionsSection;
  trial_conversions: TrialConversionsSection;
  generated_at:      string;
}

/* ───── Request params ──────────────────────────────────────────────── */

export type DateRangeKey =
  | 'this_month'
  | 'q1_2026'
  | 'last_12_months'
  | 'custom';

export interface RevenueDashboardParams {
  range?: DateRangeKey;
  from?:  string;   // YYYY-MM-DD (custom)
  to?:    string;   // YYYY-MM-DD (custom)
}

export interface TransactionsParams extends RevenueDashboardParams {
  page?:      number;
  page_size?: number;
}

export interface FailingPaymentsParams extends RevenueDashboardParams {
  page?:      number;
  page_size?: number;
}