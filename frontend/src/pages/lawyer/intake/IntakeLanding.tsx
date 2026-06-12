// src/pages/lawyer/intake/IntakeLanding.tsx
//
// Lawyer's Client Intake landing page.
//
// Shows a list of applications ASSIGNED to the logged-in lawyer
// (forwarded by HR after employee submitted them).
//
// Lawyer clicks "Start Intake" on a card → POST /intake/sessions
// auto-creates a session for that application_id → wizard opens at Step 3.
//
// ─────────────────────────────────────────────────────────────────────
// IMPORTANT: This page currently uses MOCK DATA for the assigned list.
// When backend ships GET /lawyer/applications (or similar), replace
// `fetchAssignedApplications()` below with the real API call.
// ─────────────────────────────────────────────────────────────────────

import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { intakeApi } from '../../../api/lawyer/intake.api';

/* ── Types ──────────────────────────────────────────────────────────── */
type IntakeStatus = 'pending_intake' | 'intake_in_progress' | 'intake_completed';

interface AssignedApplication {
  application_id:    string;
  client_name:       string;
  client_email:      string;
  visa_type:         string;          // "H1B"
  visa_type_label:   string;          // "H-1B Specialty Occupation"
  status:            IntakeStatus;
  intake_session_id: string | null;   // null = not started yet
  intake_step:       number | null;   // last step completed (1..5)
  assigned_at:       string;          // ISO date
  hr_reviewed_by:    string;
}

/* ── MOCK DATA — replace with API when backend ready ────────────────── */
const MOCK_ASSIGNED: AssignedApplication[] = [
  {
    application_id:    '3fa85f64-5717-4562-b3fc-2c963f66afa6',
    client_name:       'John Doe',
    client_email:      'john.doe@example.com',
    visa_type:         'H1B',
    visa_type_label:   'H-1B Specialty Occupation',
    status:            'pending_intake',
    intake_session_id: null,
    intake_step:       null,
    assigned_at:       '2026-06-10T09:30:00Z',
    hr_reviewed_by:    'Sarah Williams (HR)',
  },
  {
    application_id:    'a1b2c3d4-1111-2222-3333-444455556666',
    client_name:       'Jane Smith',
    client_email:      'jane.smith@example.com',
    visa_type:         'L1',
    visa_type_label:   'L-1 Intracompany Transfer',
    status:            'intake_in_progress',
    intake_session_id: 'sess-aaaa-bbbb-cccc-dddd',
    intake_step:       3,
    assigned_at:       '2026-06-08T14:15:00Z',
    hr_reviewed_by:    'Mark Johnson (HR)',
  },
  {
    application_id:    'b2c3d4e5-2222-3333-4444-555566667777',
    client_name:       'Carlos Rodriguez',
    client_email:      'carlos.r@example.com',
    visa_type:         'O1',
    visa_type_label:   'O-1 Extraordinary Ability',
    status:            'pending_intake',
    intake_session_id: null,
    intake_step:       null,
    assigned_at:       '2026-06-11T11:00:00Z',
    hr_reviewed_by:    'Sarah Williams (HR)',
  },
  {
    application_id:    'c3d4e5f6-3333-4444-5555-666677778888',
    client_name:       'Priya Patel',
    client_email:      'priya.patel@example.com',
    visa_type:         'F1',
    visa_type_label:   'F-1 Student (OPT)',
    status:            'intake_completed',
    intake_session_id: 'sess-eeee-ffff-gggg-hhhh',
    intake_step:       5,
    assigned_at:       '2026-06-05T08:45:00Z',
    hr_reviewed_by:    'Mark Johnson (HR)',
  },
  {
    application_id:    'd4e5f6a7-4444-5555-6666-777788889999',
    client_name:       'Wei Chen',
    client_email:      'wei.chen@example.com',
    visa_type:         'TN',
    visa_type_label:   'TN NAFTA Professional',
    status:            'pending_intake',
    intake_session_id: null,
    intake_step:       null,
    assigned_at:       '2026-06-12T07:20:00Z',
    hr_reviewed_by:    'Sarah Williams (HR)',
  },
];

/** TODO: Replace with real API call when backend ready.
 *  e.g. const res = await axios.get('/lawyer/applications'); return res.data.items;
 */
async function fetchAssignedApplications(): Promise<AssignedApplication[]> {
  // Simulate 300ms network delay
  await new Promise((r) => setTimeout(r, 300));
  return MOCK_ASSIGNED;
}

/* ── Helpers ────────────────────────────────────────────────────────── */
const statusConfig: Record<IntakeStatus, { label: string; bg: string; text: string; action: string }> = {
  pending_intake:      { label: 'Pending Intake',      bg: 'bg-amber-50',    text: 'text-amber-700',    action: 'Start Intake'     },
  intake_in_progress:  { label: 'In Progress',         bg: 'bg-blue-50',     text: 'text-blue-700',     action: 'Continue Intake'  },
  intake_completed:    { label: 'Completed',           bg: 'bg-emerald-50',  text: 'text-emerald-700',  action: 'View Submission'  },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function initials(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

/* ════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════ */
export default function IntakeLanding() {
  const navigate = useNavigate();
  const [apps, setApps] = useState<AssignedApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | IntakeStatus>('all');
  const [startingId, setStartingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchAssignedApplications();
        if (!cancelled) setApps(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load assigned applications.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  /* ── Filter + search ─────────────────────────────────────────────── */
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return apps.filter((a) => {
      if (filter !== 'all' && a.status !== filter) return false;
      if (!q) return true;
      return (
        a.client_name.toLowerCase().includes(q) ||
        a.client_email.toLowerCase().includes(q) ||
        a.visa_type.toLowerCase().includes(q) ||
        a.visa_type_label.toLowerCase().includes(q)
      );
    });
  }, [apps, search, filter]);

  /* ── Counts for filter pills ─────────────────────────────────────── */
  const counts = useMemo(() => ({
    all:                 apps.length,
    pending_intake:      apps.filter((a) => a.status === 'pending_intake').length,
    intake_in_progress:  apps.filter((a) => a.status === 'intake_in_progress').length,
    intake_completed:    apps.filter((a) => a.status === 'intake_completed').length,
  }), [apps]);

  /* ── Action handler — start OR continue intake ───────────────────── */
  const handleAction = async (app: AssignedApplication) => {
    // If session already exists → just navigate
    if (app.intake_session_id) {
      const step = app.status === 'intake_completed' ? 5 : (app.intake_step ?? 3);
      navigate(`/lawyer/intake/${app.intake_session_id}?step=${step}`);
      return;
    }

    // Else create new session
    setStartingId(app.application_id);
    try {
      const session = await intakeApi.createIntakeSession({
        application_id: app.application_id,
        generate_link:  false,
      });
      navigate(`/lawyer/intake/${session.id}?step=3`);
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const ax = e as any;
      const status = ax?.response?.status;
      let msg = 'Could not start intake.';
      if (status === 404) msg = `Application "${app.application_id.slice(0, 8)}…" not found in backend. (Mock data — UUID must exist in DB.)`;
      else if (status === 409) msg = 'A session already exists. Try refreshing the page.';
      else if (status === 500) msg = 'Backend error 500 — application UUID likely missing from DB. Wait for backend to add real data.';
      else if (e instanceof Error) msg = e.message;
      alert(msg);
    } finally {
      setStartingId(null);
    }
  };

  /* ── Render ──────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-[1240px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8 lg:py-10">

        {/* ── Header ─────────────────────────────────────────────── */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-gray-900 sm:text-2xl">Client Intake</h1>
            <p className="mt-1 text-sm text-gray-500">
              Applications assigned to you by HR. Click <span className="font-semibold text-indigo-600">Start Intake</span> to begin the 5-step intake process.
            </p>
          </div>
        </div>

        {/* ── Mock data banner ──────────────────────────────────── */}
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
          ℹ️ <span className="font-semibold">Mock data</span> — these applications are placeholder data. Backend endpoint
          {' '}<code className="rounded bg-white px-1.5 py-0.5 font-mono">GET /lawyer/applications</code>{' '}
          will replace this list when ready.
        </div>

        {/* ── Filter + search bar ───────────────────────────────── */}
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <FilterPill label="All"          count={counts.all}                 active={filter === 'all'}                 onClick={() => setFilter('all')} />
            <FilterPill label="Pending"      count={counts.pending_intake}      active={filter === 'pending_intake'}      onClick={() => setFilter('pending_intake')} />
            <FilterPill label="In Progress"  count={counts.intake_in_progress}  active={filter === 'intake_in_progress'}  onClick={() => setFilter('intake_in_progress')} />
            <FilterPill label="Completed"    count={counts.intake_completed}    active={filter === 'intake_completed'}    onClick={() => setFilter('intake_completed')} />
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or visa type…"
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm placeholder-gray-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 sm:w-72"
          />
        </div>

        {/* ── List ───────────────────────────────────────────────── */}
        <div className="mt-6">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">{error}</div>
          ) : filtered.length === 0 ? (
            <EmptyState hasFilter={filter !== 'all' || search.length > 0} />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {filtered.map((app) => (
                <ApplicationCard
                  key={app.application_id}
                  app={app}
                  starting={startingId === app.application_id}
                  onAction={() => handleAction(app)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

/* ── Application card ───────────────────────────────────────────────── */
function ApplicationCard({
  app,
  starting,
  onAction,
}: {
  app: AssignedApplication;
  starting: boolean;
  onAction: () => void;
}) {
  const cfg = statusConfig[app.status];

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md sm:flex-row sm:items-start">
      {/* Avatar */}
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 text-sm font-semibold text-indigo-700">
        {initials(app.client_name)}
      </div>

      {/* Body */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-base font-semibold text-gray-900">{app.client_name}</p>
            <p className="truncate text-xs text-gray-500">{app.client_email}</p>
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cfg.bg} ${cfg.text}`}>
            {cfg.label}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
          <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-mono font-semibold text-indigo-700">{app.visa_type}</span>
          <span className="text-gray-600">{app.visa_type_label}</span>
        </div>

        <div className="mt-2 text-[11px] text-gray-400">
          Assigned {formatDate(app.assigned_at)} · by {app.hr_reviewed_by}
        </div>
        <div className="mt-1 text-[11px] font-mono text-gray-300">App: {app.application_id.slice(0, 18)}…</div>

        {app.status === 'intake_in_progress' && app.intake_step && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-[11px] font-medium">
              <span className="text-gray-600">Step {app.intake_step} of 5</span>
              <span className="text-indigo-600">{Math.round((app.intake_step / 5) * 100)}%</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
              <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(app.intake_step / 5) * 100}%` }} />
            </div>
          </div>
        )}

        <button
          onClick={onAction}
          disabled={starting}
          className={`mt-4 flex w-full items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition-opacity sm:w-auto ${
            app.status === 'intake_completed'
              ? 'bg-emerald-600 hover:bg-emerald-700'
              : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:opacity-90'
          } disabled:cursor-not-allowed disabled:opacity-60`}
        >
          {starting ? 'Starting…' : cfg.action}
          {!starting && <span>→</span>}
        </button>
      </div>
    </div>
  );
}

/* ── Filter pill ────────────────────────────────────────────────────── */
function FilterPill({ label, count, active, onClick }: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
        active ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-gray-50'
      }`}
    >
      {label}
      <span className={`rounded-full px-1.5 text-[10px] ${active ? 'bg-white/20' : 'bg-gray-100 text-gray-600'}`}>
        {count}
      </span>
    </button>
  );
}

/* ── Skeleton ───────────────────────────────────────────────────────── */
function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex gap-4">
        <div className="h-12 w-12 rounded-full bg-gray-200" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-1/3 rounded bg-gray-200" />
          <div className="h-3 w-1/2 rounded bg-gray-200" />
          <div className="h-3 w-2/3 rounded bg-gray-200" />
        </div>
      </div>
    </div>
  );
}

/* ── Empty state ────────────────────────────────────────────────────── */
function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-12 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
        <span className="text-2xl">📋</span>
      </div>
      <h2 className="text-base font-semibold text-gray-900">
        {hasFilter ? 'No matching applications' : 'No applications assigned yet'}
      </h2>
      <p className="mt-1 text-sm text-gray-500">
        {hasFilter
          ? 'Try adjusting filters or clearing the search.'
          : 'HR will forward applications to you here. Check back soon.'}
      </p>
    </div>
  );
}
