// src/pages/admin/RevenueDashboard.tsx
//
// Cleaned: NO lucide-react. All icons are local SVG files from
// src/assets/icons/common/  and  src/assets/icons/revenue-dashboard/

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts';

import { revenueApi, downloadRevenueExport } from '../../api/admin/revenue.api';
import type {
  RevenueDashboardResponse,
  KpiMetric,
  PlanSlice,
  TransactionItem,
  TrendDataPoint,
  TrialConversionDataPoint,
  DateRangeKey,
} from '../../types/admin/revenue.types';

/* ── Icon imports (local SVG files) ─────────────────────────────────── */
// KPI tile icons (page-specific colors)
import iconKpiMrr         from '../../assets/icons/revenue-dashboard/kpi-mrr.svg';
import iconKpiArr         from '../../assets/icons/revenue-dashboard/kpi-arr.svg';
import iconKpiSubscribers from '../../assets/icons/revenue-dashboard/kpi-subscribers.svg';
import iconKpiChurn       from '../../assets/icons/revenue-dashboard/kpi-churn.svg';

// Common utility icons
import iconTrendUp        from '../../assets/icons/common/trend-up-green.svg';
import iconTrendDown      from '../../assets/icons/common/trend-down-red.svg';
import iconAlertTriangle  from '../../assets/icons/common/alert-triangle-red.svg';
import iconDownloadWhite  from '../../assets/icons/common/download-white.svg';
import iconCalendar       from '../../assets/icons/common/calendar.svg';
import iconChevronRight   from '../../assets/icons/common/chevron-right.svg';
import iconLoader         from '../../assets/icons/common/loader.svg';
import iconInbox          from '../../assets/icons/common/inbox.svg';

/* ── Date filter options ────────────────────────────────────────────── */

const DATE_RANGES: { key: DateRangeKey; label: string }[] = [
  { key: 'this_month',     label: 'This Month' },
  { key: 'q1_2026',        label: 'Q1 2026' },
  { key: 'last_12_months', label: 'Last 12 Months' },
  { key: 'custom',         label: 'Custom' },
];

const SLICE_FALLBACK_COLORS = ['#4f46e5', '#818cf8', '#c7d2fe', '#a78bfa', '#7c3aed', '#5b21b6'];

/* ── Page ───────────────────────────────────────────────────────────── */

export default function RevenueDashboard() {
  const [range, setRange] = useState<DateRangeKey>('last_12_months');
  const [data, setData]   = useState<RevenueDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async (r: DateRangeKey) => {
    setLoading(true);
    setError(null);
    try {
      const res = await revenueApi.getDashboard({ range: r });
      // eslint-disable-next-line no-console
      console.log('[RevenueDashboard] API response:', res);
      setData(res);
    } catch (e: unknown) {
      // eslint-disable-next-line no-console
      console.error('[RevenueDashboard] API error:', e);
      const msg = e instanceof Error ? e.message : 'Failed to load revenue dashboard. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(range); }, [range, load]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadRevenueExport({ range });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Export failed.';
      setError(msg);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">

        {/* ── Page header + actions ───────────────────────────────── */}
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-start lg:justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">Revenue Dashboard</h1>
            <p className="mt-1 text-sm text-gray-500">
              Overview of your billing, subscriptions, and financial health.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <DateRangeToggle value={range} onChange={setRange} />
            <button
              onClick={handleExport}
              disabled={exporting || loading}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-[#667eea] to-[#764ba2] px-3 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-500/30 transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-60 sm:px-4"
            >
              <img
                src={exporting ? iconLoader : iconDownloadWhite}
                alt=""
                className={`h-4 w-4 ${exporting ? 'animate-spin' : ''}`}
              />
              <span className="hidden sm:inline">Export Report</span>
              <span className="sm:hidden">Export</span>
            </button>
          </div>
        </div>

        {/* ── Inline error banner ─────────────────────────────────── */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}{' '}
            <button onClick={() => load(range)} className="ml-2 font-semibold underline hover:text-red-900">
              Retry
            </button>
          </div>
        )}

        {/* ── Failing-payments alert ──────────────────────────────── */}
        {data?.kpi?.failing_payments && data.kpi.failing_payments.count > 0 && (
          <FailingPaymentsAlert
            count={data.kpi.failing_payments.count}
            amountAtRisk={data.kpi.failing_payments.mrr_at_risk_display}
          />
        )}

        {/* ── KPI row ─────────────────────────────────────────────── */}
        <KpiRow loading={loading} kpi={data?.kpi} />

        {/* ── Trend + Plan Distribution ───────────────────────────── */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <RevenueTrendCard
            loading={loading}
            dataPoints={data?.trend?.data_points ?? []}
            yMaxCents={data?.trend?.y_axis_max_cents ?? null}
          />
          <PlanDistributionCard
            loading={loading}
            slices={data?.plan_distribution?.slices ?? []}
            totalDisplay={data?.plan_distribution?.total_mrr_display ?? '—'}
          />
        </div>

        {/* ── Recent transactions + Trial conversions ─────────────── */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <RecentTransactionsCard
            loading={loading}
            items={data?.transactions?.items ?? []}
          />
          <TrialConversionsCard
            loading={loading}
            dataPoints={data?.trial_conversions?.data_points ?? []}
          />
        </div>

        {/* ── Footer: data freshness ──────────────────────────────── */}
        {data && (
          <p className="text-xs text-gray-400">
            {data.kpi?.data_as_of && (
              <>Data as of {new Date(data.kpi.data_as_of).toLocaleDateString()} · </>
            )}
            {data.generated_at && (
              <>Generated {new Date(data.generated_at).toLocaleString()}</>
            )}
            {data.kpi?.is_live && (
              <span className="ml-2 inline-flex items-center gap-1 text-emerald-600">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                Live
              </span>
            )}
          </p>
        )}
      </main>
    </div>
  );
}

/* ── Date range toggle ──────────────────────────────────────────────── */

function DateRangeToggle({
  value,
  onChange,
}: {
  value: DateRangeKey;
  onChange: (v: DateRangeKey) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
      {DATE_RANGES.map((opt) => (
        <button
          key={opt.key}
          onClick={() => onChange(opt.key)}
          className={`rounded-md px-2 py-1.5 text-xs font-medium transition-colors sm:px-3 sm:text-sm ${
            value === opt.key
              ? 'bg-indigo-600 text-white shadow'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          {opt.key === 'custom' ? (
            <span className="flex items-center gap-1">
              <img src={iconCalendar} alt="" className="h-3.5 w-3.5" />
              {opt.label}
            </span>
          ) : (
            opt.label
          )}
        </button>
      ))}
    </div>
  );
}

/* ── Failing payments alert ─────────────────────────────────────────── */

function FailingPaymentsAlert({
  count,
  amountAtRisk,
}: {
  count: number;
  amountAtRisk: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-5 py-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-red-100">
          <img src={iconAlertTriangle} alt="" className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-red-900">
            {count} Failing Payment{count === 1 ? '' : 's'} Detected
          </p>
          <p className="text-sm text-red-700">
            Action required: {amountAtRisk} in recurring revenue is at risk due to expired cards or insufficient funds.
          </p>
        </div>
      </div>
      <button className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-red-700">
        Review Failing Payments
      </button>
    </div>
  );
}

/* ── KPI row ────────────────────────────────────────────────────────── */

function KpiRow({
  loading,
  kpi,
}: {
  loading: boolean;
  kpi: RevenueDashboardResponse['kpi'] | undefined;
}) {
  if (loading || !kpi) {
    return (
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)}
      </div>
    );
  }

  const fallbackMetric: KpiMetric = {
    value_cents:    null,
    value_display:  '—',
    delta_display:  null,
    delta_label:    '',
    delta_positive: true,
  };

  const tiles: {
    icon: string;
    iconBg: string;
    label: string;
    metric: KpiMetric;
  }[] = [
    { icon: iconKpiMrr,         iconBg: 'bg-indigo-50',   label: 'Monthly Recurring Revenue', metric: kpi.mrr               ?? fallbackMetric },
    { icon: iconKpiArr,         iconBg: 'bg-purple-50',   label: 'Annual Run Rate',           metric: kpi.arr               ?? fallbackMetric },
    { icon: iconKpiSubscribers, iconBg: 'bg-emerald-50',  label: 'Active Subscribers',        metric: kpi.active_subscribers ?? fallbackMetric },
    { icon: iconKpiChurn,       iconBg: 'bg-orange-50',   label: 'Net Revenue Churn',         metric: kpi.net_revenue_churn  ?? fallbackMetric },
  ];

  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
      {tiles.map((t) => <KpiCard key={t.label} {...t} />)}
    </div>
  );
}

function KpiCard({
  icon,
  iconBg,
  label,
  metric,
}: {
  icon: string;
  iconBg: string;
  label: string;
  metric: KpiMetric;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconBg}`}>
          <img src={icon} alt="" className="h-5 w-5" />
        </div>

        {metric.delta_display && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
              metric.delta_positive
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-red-50 text-red-700'
            }`}
          >
            <img
              src={metric.delta_positive ? iconTrendUp : iconTrendDown}
              alt=""
              className="h-3 w-3"
            />
            {metric.delta_display}
          </span>
        )}
      </div>
      <p className="mt-4 text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-3xl font-bold tracking-tight text-gray-900">{metric.value_display}</p>
      <p className="mt-1 text-xs text-gray-500">{metric.delta_label}</p>
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="h-10 w-10 rounded-lg bg-gray-200" />
        <div className="h-5 w-12 rounded-full bg-gray-200" />
      </div>
      <div className="mt-4 h-3 w-32 rounded bg-gray-200" />
      <div className="mt-2 h-7 w-24 rounded bg-gray-200" />
      <div className="mt-2 h-3 w-20 rounded bg-gray-200" />
    </div>
  );
}

/* ── Revenue trend ──────────────────────────────────────────────────── */

function RevenueTrendCard({
  loading,
  dataPoints,
  yMaxCents,
}: {
  loading: boolean;
  dataPoints: TrendDataPoint[];
  yMaxCents: number | null;
}) {
  const chartData = useMemo(
    () =>
      dataPoints.map((p) => ({
        month: p.month_label,
        mrr: p.mrr_cents / 100,
        target: p.target_mrr_cents != null ? p.target_mrr_cents / 100 : null,
      })),
    [dataPoints],
  );

  const yMaxDollars = yMaxCents != null ? yMaxCents / 100 : undefined;

  return (
    <Card className="lg:col-span-2">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Revenue Trend</h3>
          <p className="text-sm text-gray-500">Monthly recurring revenue growth over time</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="h-2.5 w-2.5 rounded-full bg-indigo-600" /> MRR
          </span>
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="h-2.5 w-2.5 rounded-full bg-gray-300" /> Target
          </span>
        </div>
      </div>

      <div className="mt-6 h-64">
        {loading ? (
          <ChartSkeleton />
        ) : chartData.length === 0 ? (
          <EmptyState title="No revenue data yet" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <defs>
                <linearGradient id="mrrGradient" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%"   stopColor="#667eea" />
                  <stop offset="100%" stopColor="#764ba2" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis
                domain={yMaxDollars ? [0, yMaxDollars] : ['auto', 'auto']}
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickFormatter={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`)}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                formatter={(value) => {
                  const v = typeof value === 'number' ? value : Number(value);
                  if (Number.isNaN(v)) return String(value);
                  return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;
                }}
              />
              <Line type="monotone" dataKey="mrr"    stroke="url(#mrrGradient)" strokeWidth={3} dot={false} activeDot={{ r: 5, fill: '#4f46e5' }} />
              <Line type="monotone" dataKey="target" stroke="#d1d5db" strokeWidth={2} strokeDasharray="4 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

/* ── Plan distribution ──────────────────────────────────────────────── */

function PlanDistributionCard({
  loading,
  slices,
  totalDisplay,
}: {
  loading: boolean;
  slices: PlanSlice[];
  totalDisplay: string;
}) {
  const data = useMemo(
    () =>
      slices.map((s, i) => ({
        name: s.plan_name,
        value: s.percentage,
        color: s.color ?? SLICE_FALLBACK_COLORS[i % SLICE_FALLBACK_COLORS.length],
      })),
    [slices],
  );

  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">Plan Distribution</h3>
      <p className="text-sm text-gray-500">Revenue breakdown by tier</p>

      <div className="relative mt-4 flex h-44 items-center justify-center">
        {loading ? (
          <ChartSkeleton />
        ) : data.length === 0 ? (
          <EmptyDonut totalDisplay={totalDisplay} />
        ) : (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" innerRadius={55} outerRadius={80} startAngle={90} endAngle={-270} stroke="none">
                  {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                  formatter={(value) => `${value}%`}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xs text-gray-500">Total MRR</span>
              <span className="text-xl font-bold text-gray-900">{totalDisplay}</span>
            </div>
          </>
        )}
      </div>

      <div className="mt-4 space-y-2">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex animate-pulse items-center justify-between">
                <div className="h-3 w-24 rounded bg-gray-200" />
                <div className="h-3 w-8 rounded bg-gray-200" />
              </div>
            ))
          : data.map((p) => (
              <div key={p.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                  <span className="text-gray-700">{p.name}</span>
                </div>
                <span className="font-semibold text-gray-900">{p.value}%</span>
              </div>
            ))}
      </div>
    </Card>
  );
}

function EmptyDonut({ totalDisplay }: { totalDisplay: string }) {
  return (
    <div className="relative flex h-full w-full items-center justify-center">
      <div className="h-[160px] w-[160px] rounded-full border-[25px] border-gray-100" />
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xs text-gray-500">Total MRR</span>
        <span className="text-xl font-bold text-gray-900">{totalDisplay}</span>
        <span className="mt-1 text-[10px] text-gray-400">No subscriptions yet</span>
      </div>
    </div>
  );
}

/* ── Recent transactions ────────────────────────────────────────────── */

function RecentTransactionsCard({
  loading,
  items,
}: {
  loading: boolean;
  items: TransactionItem[];
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm lg:col-span-2">
      <div className="flex items-center justify-between border-b border-gray-100 p-6">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Recent Transactions</h3>
          <p className="text-sm text-gray-500">Latest billing events across all plans</p>
        </div>
        <Link
          to="/admin/revenue-dashboard/transactions"
          className="flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700"
        >
          View All
          <img src={iconChevronRight} alt="" className="h-4 w-4" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              <th className="px-6 py-3">Customer</th>
              <th className="px-6 py-3">Amount</th>
              <th className="px-6 py-3">Plan</th>
              <th className="px-6 py-3">Date</th>
              <th className="px-6 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => <TransactionRowSkeleton key={i} />)
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12">
                  <EmptyState title="No transactions yet" subtitle="Recent billing events will appear here." />
                </td>
              </tr>
            ) : (
              items.map((tx) => <TransactionRow key={tx.id} tx={tx} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TransactionRow({ tx }: { tx: TransactionItem }) {
  const initials = getInitials(tx.customer_name);
  const dateDisplay = tx.date_display ?? formatDate(tx.date);
  const planLabel   = tx.plan_display ?? capitalize(tx.plan);

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold ${avatarColors(tx.customer_name)}`}>
            {initials}
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">{tx.customer_name}</p>
            <p className="text-xs text-gray-500">{tx.customer_email}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 text-sm font-semibold text-gray-900">{tx.amount_display}</td>
      <td className="px-6 py-4"><PlanPill plan={planLabel} /></td>
      <td className="px-6 py-4 text-sm text-gray-600">{dateDisplay}</td>
      <td className="px-6 py-4"><StatusPill status={tx.status} /></td>
    </tr>
  );
}

function TransactionRowSkeleton() {
  return (
    <tr className="animate-pulse">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-gray-200" />
          <div>
            <div className="h-3 w-28 rounded bg-gray-200" />
            <div className="mt-2 h-3 w-36 rounded bg-gray-200" />
          </div>
        </div>
      </td>
      <td className="px-6 py-4"><div className="h-3 w-16 rounded bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-5 w-20 rounded-full bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-3 w-24 rounded bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-5 w-16 rounded-full bg-gray-200" /></td>
    </tr>
  );
}

function StatusPill({ status }: { status: TransactionItem['status'] }) {
  const styles: Record<TransactionItem['status'], string> = {
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    failed:  'bg-red-50 text-red-700 ring-red-200',
    pending: 'bg-amber-50 text-amber-700 ring-amber-200',
  };
  const cls = styles[status] ?? 'bg-gray-50 text-gray-700 ring-gray-200';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${cls}`}>
      {capitalize(status)}
    </span>
  );
}

function PlanPill({ plan }: { plan: string }) {
  const key = plan.toLowerCase();
  const styles: Record<string, string> = {
    enterprise:   'bg-indigo-50 text-indigo-700',
    professional: 'bg-purple-50 text-purple-700',
    starter:      'bg-gray-100 text-gray-700',
  };
  const cls = styles[key] ?? 'bg-gray-100 text-gray-700';
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${cls}`}>
      {plan}
    </span>
  );
}

/* ── Trial conversions ──────────────────────────────────────────────── */

function TrialConversionsCard({
  loading,
  dataPoints,
}: {
  loading: boolean;
  dataPoints: TrialConversionDataPoint[];
}) {
  const data = useMemo(
    () =>
      dataPoints.map((p) => ({
        month: p.month_label,
        Conversion: p.converted_trials,
        Churn: p.churned_trials,
      })),
    [dataPoints],
  );

  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">Trial Conversions</h3>
      <p className="text-sm text-gray-500">Conversion vs Churn over {dataPoints.length || 6} months</p>

      <div className="mt-6 h-56">
        {loading ? (
          <ChartSkeleton />
        ) : data.length === 0 ? (
          <EmptyState title="No trial data yet" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barCategoryGap={16}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
              <Bar dataKey="Conversion" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Churn"      fill="#c7d2fe" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

/* ── Shared building blocks ─────────────────────────────────────────── */

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="flex h-full w-full animate-pulse items-end justify-around gap-2 px-4">
      {[60, 80, 55, 75, 90, 65, 85, 70].map((h, i) => (
        <div key={i} className="w-full rounded-t bg-gray-200" style={{ height: `${h}%` }} />
      ))}
    </div>
  );
}

function EmptyState({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
      <img src={iconInbox} alt="" className="mb-2 h-8 w-8 opacity-60" />
      <p className="text-sm font-medium text-gray-600">{title}</p>
      {subtitle && <p className="mt-1 text-xs">{subtitle}</p>}
    </div>
  );
}

/* ── Small helpers ──────────────────────────────────────────────────── */

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

function avatarColors(seed: string): string {
  const palette = [
    'bg-indigo-100 text-indigo-700',
    'bg-purple-100 text-purple-700',
    'bg-emerald-100 text-emerald-700',
    'bg-orange-100 text-orange-700',
    'bg-pink-100 text-pink-700',
    'bg-sky-100 text-sky-700',
  ];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return palette[hash % palette.length];
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
