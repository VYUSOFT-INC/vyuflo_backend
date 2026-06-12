// src/api/revenue.api.ts
//
// Follows the same pattern as src/api/auth.api.ts — uses the configured axios
// instance from ./axios, returns typed promises.
//
// 👉 Each section has its own endpoint. Adjust URLs in REVENUE_PATHS below
//    to match your Swagger. `getDashboard` fans them out in parallel
//    (Promise.allSettled) so one slow/broken endpoint doesn't block the rest.

import axios from '../axios';
import type {
  RevenueDashboardResponse,
  RevenueDashboardParams,
  KpiSection,
  TrendSection,
  PlanDistributionSection,
  TransactionsSection,
  TransactionsParams,
  TrialConversionsSection,
  FailingPaymentsSection,
  FailingPaymentsParams,
} from '../../types/admin/revenue.types';

// ── Endpoint paths (single source of truth — adjust to match Swagger) ────────
//
// ✅ CONFIRMED from console log: /admin/revenue/dashboard returns KPI shape.
// ⚠️ The other URLs are best guesses — verify against your Swagger and adjust.
export const REVENUE_PATHS = {
  kpi:              '/admin/revenue/dashboard',           // ← returns KPI shape
  trend:            '/admin/revenue/trend',
  planDistribution: '/admin/revenue/plan-distribution',
  transactions:     '/admin/revenue/transactions',
  trialConversions: '/admin/revenue/trial-conversions',
  failingPayments:  '/admin/revenue/failing-payments',
  exportSummary:    '/admin/revenue/export',
} as const;

// ── Revenue API ──────────────────────────────────────────────────────────────

export const revenueApi = {
  /** KPI tiles (MRR / ARR / Active Subscribers / Net Revenue Churn + failing_payments). */
  getKpi: async (
    params: RevenueDashboardParams = {},
  ): Promise<KpiSection> => {
    const res = await axios.get(REVENUE_PATHS.kpi, { params });
    return res.data;
  },

  /** Revenue trend line chart. */
  getTrend: async (
    params: RevenueDashboardParams = {},
  ): Promise<TrendSection> => {
    const res = await axios.get(REVENUE_PATHS.trend, { params });
    return res.data;
  },

  /** Plan distribution donut chart. */
  getPlanDistribution: async (
    params: RevenueDashboardParams = {},
  ): Promise<PlanDistributionSection> => {
    const res = await axios.get(REVENUE_PATHS.planDistribution, { params });
    return res.data;
  },

  /** Recent transactions (paginated). */
  getTransactions: async (
    params: TransactionsParams = {},
  ): Promise<TransactionsSection> => {
    const res = await axios.get(REVENUE_PATHS.transactions, { params });
    return res.data;
  },

  /** Trial conversions bar chart. */
  getTrialConversions: async (
    params: RevenueDashboardParams = {},
  ): Promise<TrialConversionsSection> => {
    const res = await axios.get(REVENUE_PATHS.trialConversions, { params });
    return res.data;
  },

  /** Detailed failing-payments list (paginated). */
  getFailingPayments: async (
    params: FailingPaymentsParams = {},
  ): Promise<FailingPaymentsSection> => {
    const res = await axios.get(REVENUE_PATHS.failingPayments, { params });
    return res.data;
  },

  /**
   * Fetches ALL dashboard sections in parallel and merges into the combined
   * shape the page expects. Uses Promise.allSettled — if one endpoint fails,
   * that section becomes `null` (page renders empty state for it) instead of
   * the whole dashboard going blank.
   */
  getDashboard: async (
    params: RevenueDashboardParams = {},
  ): Promise<RevenueDashboardResponse> => {
    const [kpiR, trendR, planR, txR, trialR] = await Promise.allSettled([
      revenueApi.getKpi(params),
      revenueApi.getTrend(params),
      revenueApi.getPlanDistribution(params),
      revenueApi.getTransactions({ ...params, page: 1, page_size: 5 }),
      revenueApi.getTrialConversions(params),
    ]);

    // Log failures so devs can see which endpoint(s) were rejected.
    [
      ['kpi', kpiR],
      ['trend', trendR],
      ['plan_distribution', planR],
      ['transactions', txR],
      ['trial_conversions', trialR],
    ].forEach(([name, result]) => {
      if ((result as PromiseSettledResult<unknown>).status === 'rejected') {
        // eslint-disable-next-line no-console
        console.warn(
          `[revenueApi] ${name as string} endpoint failed:`,
          (result as PromiseRejectedResult).reason,
        );
      }
    });

    return {
      kpi:               kpiR.status   === 'fulfilled' ? kpiR.value   : (null as unknown as KpiSection),
      trend:             trendR.status === 'fulfilled' ? trendR.value : (null as unknown as TrendSection),
      plan_distribution: planR.status  === 'fulfilled' ? planR.value  : (null as unknown as PlanDistributionSection),
      transactions:      txR.status    === 'fulfilled' ? txR.value    : (null as unknown as TransactionsSection),
      trial_conversions: trialR.status === 'fulfilled' ? trialR.value : (null as unknown as TrialConversionsSection),
      generated_at:      new Date().toISOString(),
    };
  },

  /**
   * Export Report — backend returns a CSV/text payload.
   * Triggers a browser download client-side.
   */
  exportReport: async (
    params: RevenueDashboardParams = {},
  ): Promise<Blob> => {
    const res = await axios.get(REVENUE_PATHS.exportSummary, {
      params,
      responseType: 'blob',
    });
    return res.data as Blob;
  },
};

/** Helper used by the Export Report button. */
export async function downloadRevenueExport(
  params: RevenueDashboardParams = {},
): Promise<void> {
  const blob = await revenueApi.exportReport(params);
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `revenue-dashboard-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}