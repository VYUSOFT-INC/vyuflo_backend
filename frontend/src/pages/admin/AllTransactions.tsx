// src/pages/admin/AllTransactions.tsx
//
// Cleaned: NO lucide-react. All icons from src/assets/icons/common/

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { revenueApi } from '../../api/admin/revenue.api';
import type {
  TransactionItem,
  TransactionsSection,
  DateRangeKey,
} from '../../types/admin/revenue.types';

/* ── Icon imports (common only — no page-specific icons) ────────────── */
import iconArrowLeft     from '../../assets/icons/common/arrow-left.svg';
import iconCalendar      from '../../assets/icons/common/calendar.svg';
import iconChevronLeft   from '../../assets/icons/common/chevron-left.svg';
import iconChevronRight  from '../../assets/icons/common/chevron-right.svg';
import iconInbox         from '../../assets/icons/common/inbox.svg';

/* ── Date filter options ─────────────────────────────────────────────── */

const DATE_RANGES: { key: DateRangeKey; label: string }[] = [
  { key: 'this_month',     label: 'This Month' },
  { key: 'q1_2026',        label: 'Q1 2026' },
  { key: 'last_12_months', label: 'Last 12 Months' },
  { key: 'custom',         label: 'Custom' },
];

const PAGE_SIZE = 20;

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function AllTransactions() {
  const [range, setRange]   = useState<DateRangeKey>('last_12_months');
  const [page, setPage]     = useState(1);
  const [data, setData]     = useState<TransactionsSection | null>(null);
  const [loading, setLoad]  = useState(true);
  const [error, setError]   = useState<string | null>(null);

  const load = useCallback(
    async (r: DateRangeKey, p: number) => {
      setLoad(true);
      setError(null);
      try {
        const res = await revenueApi.getTransactions({
          range: r,
          page: p,
          page_size: PAGE_SIZE,
        });
        setData(res);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : 'Failed to load transactions. Please try again.';
        setError(msg);
      } finally {
        setLoad(false);
      }
    },
    [],
  );

  useEffect(() => { load(range, page); }, [range, page, load]);

  const handleRangeChange = (r: DateRangeKey) => {
    setPage(1);
    setRange(r);
  };

  const items       = data?.items ?? [];
  const total       = data?.total ?? 0;
  const totalPages  = data?.total_pages ?? 1;

  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">

        {/* ── Page header ─────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-start lg:justify-between">
          <div>
            <Link
              to="/admin/revenue-dashboard"
              className="mb-2 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              <img src={iconArrowLeft} alt="" className="h-4 w-4" />
              Back to Revenue Dashboard
            </Link>
            <h1 className="text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">All Transactions</h1>
            <p className="mt-1 text-sm text-gray-500">
              Complete list of billing events across all plans.
            </p>
          </div>

          <DateRangeToggle value={range} onChange={handleRangeChange} />
        </div>

        {/* ── Inline error ────────────────────────────────────────── */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}{' '}
            <button onClick={() => load(range, page)} className="ml-2 font-semibold underline hover:text-red-900">
              Retry
            </button>
          </div>
        )}

        {/* ── Summary line ────────────────────────────────────────── */}
        {!loading && !error && (
          <p className="text-sm text-gray-500">
            Showing{' '}
            <span className="font-semibold text-gray-700">
              {items.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1}
              {items.length > 0 && `–${(page - 1) * PAGE_SIZE + items.length}`}
            </span>{' '}
            of <span className="font-semibold text-gray-700">{total}</span> transactions
          </p>
        )}

        {/* ── Table ───────────────────────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <thead className="border-b border-gray-100">
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
                  Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-16">
                      <EmptyState />
                    </td>
                  </tr>
                ) : (
                  items.map((tx) => <Row key={tx.id} tx={tx} />)
                )}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ────────────────────────────────────────── */}
          {!loading && items.length > 0 && (
            <Pagination page={page} totalPages={totalPages} onChange={setPage} />
          )}
        </div>
      </main>
    </div>
  );
}

/* ── Date range toggle ────────────────────────────────────────────────── */

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

/* ── Table row ────────────────────────────────────────────────────────── */

function Row({ tx }: { tx: TransactionItem }) {
  const initials    = getInitials(tx.customer_name);
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

function SkeletonRow() {
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

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center text-center text-gray-400">
      <img src={iconInbox} alt="" className="mb-2 h-10 w-10 opacity-60" />
      <p className="text-sm font-medium text-gray-600">No transactions yet</p>
      <p className="mt-1 text-xs">Billing events for this period will appear here.</p>
    </div>
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

/* ── Pagination ───────────────────────────────────────────────────────── */

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  const pageNumbers = getPageNumbers(page, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 px-4 py-3 sm:px-6">
      <button
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page <= 1}
        className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <img src={iconChevronLeft} alt="" className="h-4 w-4" />
        Previous
      </button>

      <div className="flex items-center gap-1">
        {pageNumbers.map((p, i) =>
          p === '…' ? (
            <span key={`gap-${i}`} className="px-2 text-sm text-gray-400">…</span>
          ) : (
            <button
              key={p}
              onClick={() => onChange(p as number)}
              className={`h-8 min-w-[2rem] rounded-md px-2 text-sm font-medium transition-colors ${
                p === page ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              {p}
            </button>
          ),
        )}
      </div>

      <button
        onClick={() => onChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Next
        <img src={iconChevronRight} alt="" className="h-4 w-4" />
      </button>
    </div>
  );
}

function getPageNumbers(current: number, total: number): (number | '…')[] {
  const pages: (number | '…')[] = [];
  const window = 1;
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - window && i <= current + window)) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== '…') {
      pages.push('…');
    }
  }
  return pages;
}

/* ── Helpers ──────────────────────────────────────────────────────────── */

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
