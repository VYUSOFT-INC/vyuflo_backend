// src/pages/admin/SystemAuditLogs.tsx
//
// Cleaned: NO lucide-react. Icons from src/assets/icons/common/ and audit-logs/

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Area, AreaChart,
} from 'recharts';

import { auditApi, downloadAuditExport } from '../../api/admin/audit-logs.api';
import type {
  AuditDashboardResponse, AuditKpiMetric, AuditPeriod,
  EventTypeSlice, SecurityEventSlice, TimelineDataPoint, TopUser,
  AuditLogItem, AuditLogsListSection,
} from '../../types/admin/audit-logs.types';

/* ── Icon imports ─────────────────────────────────────────────────── */
// Page-specific KPI icons
import iconKpiTotalEvents from '../../assets/icons/audit-logs/kpi-total-events.svg';
import iconKpiUserActions from '../../assets/icons/audit-logs/kpi-user-actions.svg';
import iconKpiSecurity    from '../../assets/icons/audit-logs/kpi-security.svg';
import iconKpiFailedLogins from '../../assets/icons/audit-logs/kpi-failed-logins.svg';
import iconKpiUptime      from '../../assets/icons/audit-logs/kpi-uptime.svg';
import iconEmptyUsers     from '../../assets/icons/audit-logs/empty-users.svg';

// Common utility icons
import iconDownloadWhite  from '../../assets/icons/common/download-white.svg';
import iconFilter         from '../../assets/icons/common/filter.svg';
import iconLoader         from '../../assets/icons/common/loader.svg';
import iconInbox          from '../../assets/icons/common/inbox.svg';
import iconChevronLeft    from '../../assets/icons/common/chevron-left.svg';
import iconChevronRight   from '../../assets/icons/common/chevron-right.svg';
import iconCheckCircle    from '../../assets/icons/common/check-circle-green.svg';
import iconAlertCircle    from '../../assets/icons/common/alert-circle-red.svg';

/* ── Period options ─────────────────────────────────────────────────── */

const PERIODS: { key: AuditPeriod; label: string }[] = [
  { key: '24h',     label: 'Last 24 Hours' },
  { key: '7days',   label: 'Last 7 Days'   },
  { key: '30days',  label: 'Last 30 Days'  },
  { key: '90days',  label: 'Last 90 Days'  },
];

const SLICE_FALLBACK_COLORS = [
  '#4f46e5', '#818cf8', '#a78bfa', '#c4b5fd', '#7c3aed', '#5b21b6',
  '#06b6d4', '#22c55e', '#f59e0b', '#ef4444',
];

const LOGS_PAGE_SIZE = 10;

/* ── Page ───────────────────────────────────────────────────────────── */

export default function SystemAuditLogs() {
  const [period, setPeriod] = useState<AuditPeriod>('7days');
  const [data, setData]     = useState<AuditDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const [logsPage, setLogsPage]       = useState(1);
  const [logs, setLogs]               = useState<AuditLogsListSection | null>(null);
  const [logsLoading, setLogsLoading] = useState(true);

  const loadDashboard = useCallback(async (p: AuditPeriod) => {
    setLoading(true);
    setError(null);
    try {
      let res: AuditDashboardResponse;
      try {
        res = await auditApi.getDashboard({ period: p });
      } catch {
        // eslint-disable-next-line no-console
        console.info('[SystemAuditLogs] /dashboard endpoint unavailable — falling back to parallel fetch');
        res = await auditApi.getAllParallel({ period: p });
      }
      // eslint-disable-next-line no-console
      console.log('[SystemAuditLogs] dashboard response:', res);
      setData(res);
    } catch (e: unknown) {
      // eslint-disable-next-line no-console
      console.error('[SystemAuditLogs] dashboard error:', e);
      const msg = e instanceof Error ? e.message : 'Failed to load audit dashboard. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLogs = useCallback(async (p: AuditPeriod, page: number) => {
    setLogsLoading(true);
    try {
      const res = await auditApi.getLogs({ period: p, page, page_size: LOGS_PAGE_SIZE });
      setLogs(res);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('[SystemAuditLogs] logs error:', e);
      setLogs(null);
    } finally {
      setLogsLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(period); }, [period, loadDashboard]);
  useEffect(() => { loadLogs(period, logsPage); }, [period, logsPage, loadLogs]);

  const handlePeriodChange = (p: AuditPeriod) => { setLogsPage(1); setPeriod(p); };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadAuditExport({ period });
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: unknown }; message?: string };
      // eslint-disable-next-line no-console
      console.error('[SystemAuditLogs] export error:', err.response?.status, err.response?.data, err);
      const detail = (err.response?.data as { detail?: unknown })?.detail;
      const detailMsg = Array.isArray(detail)
        ? detail.map((d: { loc?: string[]; msg?: string }) => `${(d.loc ?? []).join('.')}: ${d.msg ?? ''}`).join('; ')
        : typeof detail === 'string' ? detail : null;
      setError(detailMsg ? `Export failed (${err.response?.status ?? ''}): ${detailMsg}` : err.message ?? 'Export failed.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 sm:px-8 sm:py-8">

        {/* ── Page header + actions ───────────────────────────────── */}
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-gray-900">System Audit Logs</h1>
            <p className="mt-1 text-xs sm:text-sm text-gray-500">Monitor all system activities for compliance and security.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <PeriodToggle value={period} onChange={handlePeriodChange} />
            <button
              type="button"
              className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
            >
              <img src={iconFilter} alt="" className="h-4 w-4" />
              <span className="hidden sm:inline">Advanced</span> Filters
            </button>
            <button
              onClick={handleExport}
              disabled={exporting || loading}
              className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-[#667eea] to-[#764ba2] px-3 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-500/30 transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <img
                src={exporting ? iconLoader : iconDownloadWhite}
                alt=""
                className={`h-4 w-4 ${exporting ? 'animate-spin' : ''}`}
              />
              Export <span className="hidden sm:inline">Logs</span>
            </button>
          </div>
        </div>

        {/* ── Inline error ────────────────────────────────────────── */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}{' '}
            <button onClick={() => loadDashboard(period)} className="ml-2 font-semibold underline hover:text-red-900">Retry</button>
          </div>
        )}

        <KpiRow loading={loading} kpi={data?.kpi} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <TimelineCard loading={loading} dataPoints={data?.timeline?.data_points ?? []} yMax={data?.timeline?.y_axis_max ?? null} />
          <EventTypesCard loading={loading} slices={data?.event_types?.slices ?? []} totalEvents={data?.event_types?.total_events ?? 0} />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <TopUsersCard loading={loading} users={data?.top_users?.users ?? []} />
          <SecurityEventsCard loading={loading} slices={data?.security?.slices ?? []} total={data?.security?.total_count ?? 0} />
          <SystemHealthCard
            loading={loading}
            uptime={data?.kpi?.system_uptime}
            allSystemsOk={data?.kpi?.all_systems_ok ?? false}
            hasKpiData={!!data?.kpi}
          />
        </div>

        <AuditLogsTable
          loading={logsLoading}
          items={logs?.items ?? []}
          total={logs?.total ?? 0}
          page={logs?.page ?? logsPage}
          pageSize={logs?.page_size ?? LOGS_PAGE_SIZE}
          totalPages={logs?.total_pages ?? 1}
          onPageChange={setLogsPage}
        />

        {data?.generated_at && (
          <p className="text-xs text-gray-400">
            Generated {new Date(data.generated_at).toLocaleString()}
            {data.kpi?.all_systems_ok && (
              <span className="ml-2 inline-flex items-center gap-1 text-emerald-600">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                All systems operational
              </span>
            )}
          </p>
        )}
      </main>
    </div>
  );
}

function PeriodToggle({ value, onChange }: { value: AuditPeriod; onChange: (v: AuditPeriod) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
      {PERIODS.map((opt) => (
        <button
          key={opt.key}
          onClick={() => onChange(opt.key)}
          className={`rounded-md px-2.5 py-1.5 text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
            value === opt.key ? 'bg-indigo-600 text-white shadow' : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function KpiRow({ loading, kpi }: { loading: boolean; kpi: AuditDashboardResponse['kpi'] | undefined | null }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => <KpiSkeleton key={i} />)}
      </div>
    );
  }

  const fallback: AuditKpiMetric = { value_display: '—', delta_display: '', delta_positive: true, period_label: '' };
  const k = (kpi ?? {}) as Partial<NonNullable<typeof kpi>>;

  const tiles: { icon: string; iconBg: string; label: string; metric: AuditKpiMetric }[] = [
    { icon: iconKpiTotalEvents,  iconBg: 'bg-indigo-50',  label: 'Total Events',    metric: k.total_events    ?? fallback },
    { icon: iconKpiUserActions,  iconBg: 'bg-purple-50',  label: 'User Actions',    metric: k.user_actions    ?? fallback },
    { icon: iconKpiSecurity,     iconBg: 'bg-amber-50',   label: 'Security Events', metric: k.security_events ?? fallback },
    { icon: iconKpiFailedLogins, iconBg: 'bg-red-50',     label: 'Failed Logins',   metric: k.failed_logins   ?? fallback },
    { icon: iconKpiUptime,       iconBg: 'bg-emerald-50', label: 'System Uptime',   metric: k.system_uptime   ?? fallback },
  ];

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
      {tiles.map((t) => <KpiCard key={t.label} {...t} />)}
    </div>
  );
}

function KpiCard({ icon, iconBg, label, metric }: { icon: string; iconBg: string; label: string; metric: AuditKpiMetric }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconBg}`}>
          <img src={icon} alt="" className="h-5 w-5" />
        </div>
        {metric.delta_display && (
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
            metric.delta_positive ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
          }`}>
            {metric.delta_display}
          </span>
        )}
      </div>
      <p className="mt-4 text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold tracking-tight text-gray-900">{metric.value_display}</p>
      {metric.period_label && <p className="mt-1 text-xs text-gray-500">vs previous {metric.period_label}</p>}
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
      <div className="mt-4 h-3 w-28 rounded bg-gray-200" />
      <div className="mt-2 h-6 w-20 rounded bg-gray-200" />
    </div>
  );
}

function TimelineCard({ loading, dataPoints, yMax }: { loading: boolean; dataPoints: TimelineDataPoint[]; yMax: number | null }) {
  const chartData = useMemo(() => dataPoints.map((p) => ({ x: p.label, y: p.event_count })), [dataPoints]);
  return (
    <Card className="lg:col-span-2">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Activity Timeline</h3>
          <p className="text-sm text-gray-500">Event count over selected period</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs text-gray-600">
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-600" /> Events
        </span>
      </div>
      <div className="mt-6 h-64">
        {loading ? <ChartSkeleton /> : chartData.length === 0 ? <EmptyState title="No timeline data yet" /> : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="timelineFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#667eea" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#667eea" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="timelineStroke" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%"   stopColor="#667eea" />
                  <stop offset="100%" stopColor="#764ba2" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="x" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis domain={yMax != null && yMax > 0 ? [0, yMax] : ['auto', 'auto']} tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} />
              <Area type="monotone" dataKey="y" stroke="url(#timelineStroke)" strokeWidth={3} fill="url(#timelineFill)" dot={false} activeDot={{ r: 5, fill: '#4f46e5' }} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function EventTypesCard({ loading, slices, totalEvents }: { loading: boolean; slices: EventTypeSlice[]; totalEvents: number }) {
  const data = useMemo(
    () => slices.map((s, i) => ({
      name: s.label, value: s.count, percentage: s.percentage,
      color: s.color || SLICE_FALLBACK_COLORS[i % SLICE_FALLBACK_COLORS.length],
    })),
    [slices],
  );
  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">Event Types Distribution</h3>
      <p className="text-sm text-gray-500">Breakdown by event category</p>
      <div className="relative mt-4 flex h-44 items-center justify-center">
        {loading ? <ChartSkeleton /> : data.length === 0 ? (
          <EmptyDonut centerLabel="Total Events" centerValue={totalEvents.toLocaleString()} />
        ) : (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" innerRadius={55} outerRadius={80} startAngle={90} endAngle={-270} stroke="none">
                  {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                  formatter={(value, _name, item) => `${value} (${(item?.payload as { percentage?: number })?.percentage ?? 0}%)`}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xs text-gray-500">Total Events</span>
              <span className="text-xl font-bold text-gray-900">{totalEvents.toLocaleString()}</span>
            </div>
          </>
        )}
      </div>
      <div className="mt-4 max-h-32 space-y-2 overflow-y-auto">
        {loading ? Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex animate-pulse items-center justify-between">
            <div className="h-3 w-24 rounded bg-gray-200" />
            <div className="h-3 w-10 rounded bg-gray-200" />
          </div>
        )) : data.map((p) => (
          <div key={p.name} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 truncate">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: p.color }} />
              <span className="truncate text-gray-700">{p.name}</span>
            </div>
            <span className="font-semibold text-gray-900">{p.percentage}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TopUsersCard({ loading, users }: { loading: boolean; users: TopUser[] }) {
  const chartData = useMemo(
    () => users.slice(0, 6).map((u) => ({
      name: u.avatar_initials || initialsFromName(u.user_name),
      full: u.user_name,
      count: u.action_count,
    })),
    [users],
  );
  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">Top User Activities</h3>
      <p className="text-sm text-gray-500">Most active users in selected period</p>
      <div className="mt-6 h-44">
        {loading ? <ChartSkeleton /> : chartData.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
            <img src={iconEmptyUsers} alt="" className="mb-2 h-8 w-8 opacity-60" />
            <p className="text-sm font-medium text-gray-600">No user activity yet</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barCategoryGap={16}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }}
                labelFormatter={(label, payload) => {
                  const p = payload?.[0]?.payload as { full?: string };
                  return p?.full ?? label;
                }}
              />
              <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </Card>
  );
}

function SecurityEventsCard({ loading, slices, total }: { loading: boolean; slices: SecurityEventSlice[]; total: number }) {
  const data = useMemo(
    () => slices.map((s, i) => ({
      name: s.label, value: s.count, percentage: s.percentage,
      color: s.color || SLICE_FALLBACK_COLORS[i % SLICE_FALLBACK_COLORS.length],
    })),
    [slices],
  );
  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">Security Events by Type</h3>
      <p className="text-sm text-gray-500">Security incident breakdown</p>
      <div className="relative mt-4 flex h-44 items-center justify-center">
        {loading ? <ChartSkeleton /> : data.length === 0 ? (
          <EmptyDonut centerLabel="Security Events" centerValue={total.toLocaleString()} />
        ) : (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" innerRadius={55} outerRadius={80} startAngle={90} endAngle={-270} stroke="none">
                  {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-xs text-gray-500">Total</span>
              <span className="text-xl font-bold text-gray-900">{total.toLocaleString()}</span>
            </div>
          </>
        )}
      </div>
      <div className="mt-4 max-h-20 space-y-1.5 overflow-y-auto">
        {!loading && data.map((p) => (
          <div key={p.name} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 truncate">
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: p.color }} />
              <span className="truncate text-gray-700">{p.name}</span>
            </div>
            <span className="font-semibold text-gray-900">{p.percentage}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function SystemHealthCard({
  loading, uptime, allSystemsOk, hasKpiData,
}: {
  loading: boolean; uptime: AuditKpiMetric | undefined; allSystemsOk: boolean; hasKpiData: boolean;
}) {
  const status: 'loading' | 'unavailable' | 'ok' | 'degraded' =
    loading ? 'loading' : !hasKpiData ? 'unavailable' : allSystemsOk ? 'ok' : 'degraded';

  return (
    <Card>
      <h3 className="text-base font-semibold text-gray-900">System Health</h3>
      <p className="text-sm text-gray-500">Overall platform status</p>
      <div className="mt-6 flex flex-col items-center justify-center">
        {status === 'loading' && (
          <>
            <div className="h-20 w-20 animate-pulse rounded-full bg-gray-200" />
            <div className="mt-4 h-4 w-24 animate-pulse rounded bg-gray-200" />
          </>
        )}
        {status === 'unavailable' && (
          <>
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gray-100">
              <img src={iconAlertCircle} alt="" className="h-10 w-10 opacity-60" />
            </div>
            <p className="mt-4 text-2xl font-bold text-gray-400">—</p>
            <p className="mt-1 text-sm font-medium text-gray-500">Status unavailable</p>
            <p className="mt-2 text-xs text-gray-400">Unable to fetch system status</p>
          </>
        )}
        {(status === 'ok' || status === 'degraded') && (
          <>
            <div className={`flex h-20 w-20 items-center justify-center rounded-full ${status === 'ok' ? 'bg-emerald-50' : 'bg-amber-50'}`}>
              <img src={status === 'ok' ? iconCheckCircle : iconAlertCircle} alt="" className="h-10 w-10" />
            </div>
            <p className="mt-4 text-2xl font-bold text-gray-900">{uptime?.value_display ?? '—'}</p>
            <p className="mt-1 text-sm font-medium text-gray-600">
              {status === 'ok' ? 'All Systems Operational' : 'Degraded Performance'}
            </p>
            {uptime?.delta_display && (
              <p className={`mt-2 text-xs font-semibold ${uptime.delta_positive ? 'text-emerald-600' : 'text-red-600'}`}>
                {uptime.delta_display} vs previous {uptime.period_label}
              </p>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

function AuditLogsTable({
  loading, items, total, page, pageSize, totalPages, onPageChange,
}: {
  loading: boolean; items: AuditLogItem[]; total: number; page: number; pageSize: number; totalPages: number; onPageChange: (p: number) => void;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-6 py-4">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Audit Logs</h3>
          <p className="text-sm text-gray-500">{loading ? 'Loading…' : `${total.toLocaleString()} events recorded`}</p>
        </div>
        {!loading && total > 0 && (
          <p className="text-xs text-gray-500">
            Showing <span className="font-semibold text-gray-700">{(page - 1) * pageSize + 1}–{(page - 1) * pageSize + items.length}</span> of <span className="font-semibold text-gray-700">{total.toLocaleString()}</span>
          </p>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-gray-50">
            <tr className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              <th className="px-6 py-3">Timestamp</th>
              <th className="px-6 py-3">User</th>
              <th className="px-6 py-3">Action</th>
              <th className="px-6 py-3">Resource</th>
              <th className="px-6 py-3">IP Address</th>
              <th className="px-6 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? Array.from({ length: 5 }).map((_, i) => <LogRowSkeleton key={i} />)
              : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16">
                    <EmptyState title="No audit logs yet" subtitle="Activity from your team will appear here." />
                  </td>
                </tr>
              ) : (
                items.map((log) => <LogRow key={log.id} log={log} />)
              )}
          </tbody>
        </table>
      </div>
      {!loading && items.length > 0 && totalPages > 1 && (
        <LogsPagination page={page} totalPages={totalPages} onChange={onPageChange} />
      )}
    </div>
  );
}

function LogRow({ log }: { log: AuditLogItem }) {
  const role = log.actor_role || log.actor_type || '—';
  const actionLabel = log.action_label || log.action || '—';
  const eventTypeLabel = log.event_type_label || log.event_type || '';
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-6 py-4 text-xs text-gray-600 font-mono whitespace-nowrap">{formatTimestamp(log.created_at)}</td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${avatarColors(log.actor_name)}`}>
            {initialsFromName(log.actor_name)}
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">{log.actor_name || 'Unknown User'}</p>
            <p className="text-xs text-gray-500">{log.actor_email || `Role: ${role}`}</p>
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <p className="text-sm font-medium text-gray-900">{actionLabel}</p>
        {eventTypeLabel && eventTypeLabel !== actionLabel && <p className="text-xs text-gray-500">{eventTypeLabel}</p>}
      </td>
      <td className="px-6 py-4 text-sm text-gray-600 font-mono">{log.resource || '—'}</td>
      <td className="px-6 py-4 text-xs text-gray-600 font-mono">{log.ip_address || '—'}</td>
      <td className="px-6 py-4"><SecurityPill securityEventType={log.security_event_type} /></td>
    </tr>
  );
}

function LogRowSkeleton() {
  return (
    <tr className="animate-pulse">
      <td className="px-6 py-4"><div className="h-3 w-32 rounded bg-gray-200" /></td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-gray-200" />
          <div>
            <div className="h-3 w-24 rounded bg-gray-200" />
            <div className="mt-1 h-3 w-32 rounded bg-gray-200" />
          </div>
        </div>
      </td>
      <td className="px-6 py-4"><div className="h-3 w-28 rounded bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-3 w-24 rounded bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-3 w-20 rounded bg-gray-200" /></td>
      <td className="px-6 py-4"><div className="h-5 w-16 rounded-full bg-gray-200" /></td>
    </tr>
  );
}

function SecurityPill({ securityEventType }: { securityEventType: string | null }) {
  if (!securityEventType) {
    return <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">Info</span>;
  }
  const t = securityEventType.toLowerCase();
  const isCritical = t.includes('critical') || t.includes('breach') || t.includes('attack');
  const isWarning = t.includes('warn') || t.includes('failed') || t.includes('unusual') || t.includes('suspicious');
  if (isCritical) return <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700 ring-1 ring-red-200">Critical</span>;
  if (isWarning) return <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-amber-200">Warning</span>;
  return <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-indigo-200">{securityEventType}</span>;
}

function LogsPagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (p: number) => void }) {
  const pageNumbers = getPageNumbers(page, totalPages);
  return (
    <div className="flex items-center justify-between border-t border-gray-100 px-6 py-3">
      <button onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1} className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40">
        <img src={iconChevronLeft} alt="" className="h-4 w-4" />
        Previous
      </button>
      <div className="flex items-center gap-1">
        {pageNumbers.map((p, i) =>
          p === '…' ? <span key={`gap-${i}`} className="px-2 text-sm text-gray-400">…</span> : (
            <button key={p} onClick={() => onChange(p as number)} className={`h-8 min-w-[2rem] rounded-md px-2 text-sm font-medium transition-colors ${p === page ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>
              {p}
            </button>
          ),
        )}
      </div>
      <button onClick={() => onChange(Math.min(totalPages, page + 1))} disabled={page >= totalPages} className="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40">
        Next
        <img src={iconChevronRight} alt="" className="h-4 w-4" />
      </button>
    </div>
  );
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}>{children}</div>;
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

function EmptyDonut({ centerLabel, centerValue }: { centerLabel: string; centerValue: string }) {
  return (
    <div className="relative flex h-full w-full items-center justify-center">
      <div className="h-[160px] w-[160px] rounded-full border-[25px] border-gray-100" />
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xs text-gray-500">{centerLabel}</span>
        <span className="text-xl font-bold text-gray-900">{centerValue}</span>
        <span className="mt-1 text-[10px] text-gray-400">No data yet</span>
      </div>
    </div>
  );
}

function initialsFromName(name: string): string {
  if (!name) return '—';
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('');
}

function avatarColors(seed: string): string {
  const palette = [
    'bg-indigo-100 text-indigo-700', 'bg-purple-100 text-purple-700', 'bg-emerald-100 text-emerald-700',
    'bg-orange-100 text-orange-700', 'bg-pink-100 text-pink-700', 'bg-sky-100 text-sky-700',
  ];
  let hash = 0;
  const s = seed || 'anon';
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  return palette[hash % palette.length];
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function getPageNumbers(current: number, total: number): (number | '…')[] {
  const pages: (number | '…')[] = [];
  const window = 1;
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - window && i <= current + window)) pages.push(i);
    else if (pages[pages.length - 1] !== '…') pages.push('…');
  }
  return pages;
}
