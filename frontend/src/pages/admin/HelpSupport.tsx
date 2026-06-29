// src/pages/admin/HelpSupport.tsx
//
// Cleaned: NO lucide-react. All icons from src/assets/icons/common/

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { supportApi } from '../../api/admin/support.api';
import type {
  SupportArticle, SystemStatusResponse, CreateTicketBody,
  TicketCategory, TicketPriority,
} from '../../types/admin/support.types';

/* ── Icon imports (common only) ─────────────────────────────────────── */
import iconSearch        from '../../assets/icons/common/search.svg';
import iconChevronDown   from '../../assets/icons/common/chevron-down.svg';
import iconChevronRight  from '../../assets/icons/common/chevron-right.svg';
import iconHelpCircle    from '../../assets/icons/common/help-circle-indigo.svg';
import iconTicket        from '../../assets/icons/common/ticket-indigo.svg';
import iconMessageSquare from '../../assets/icons/common/message-square-purple.svg';
import iconBookOpen      from '../../assets/icons/common/book-open-emerald.svg';
import iconLoader        from '../../assets/icons/common/loader.svg';
import iconXClose        from '../../assets/icons/common/x-close.svg';
import iconCheckCircle   from '../../assets/icons/common/check-circle-green.svg';
import iconAlertCircle   from '../../assets/icons/common/alert-circle-red.svg';
import iconExternalLink  from '../../assets/icons/common/external-link.svg';
import iconFileText      from '../../assets/icons/common/file-text-indigo.svg';

/* ── Constants ──────────────────────────────────────────────────────── */

const CATEGORIES: { key: string | null; label: string }[] = [
  { key: null,                 label: 'All Categories'  },
  { key: 'platform-config',    label: 'Platform Config' },
  { key: 'user-management',    label: 'User Management' },
  { key: 'billing',            label: 'Billing'         },
  { key: 'integrations',       label: 'Integrations'    },
  { key: 'security',           label: 'Security'        },
];

const TICKET_CATEGORIES: { value: TicketCategory; label: string }[] = [
  { value: 'technical',   label: 'Technical Issue' },
  { value: 'billing',     label: 'Billing'         },
  { value: 'integration', label: 'Integration'     },
  { value: 'general',     label: 'General Inquiry' },
  { value: 'other',       label: 'Other'           },
];

const TICKET_PRIORITIES: { value: TicketPriority; label: string }[] = [
  { value: 'low',    label: 'Low'    },
  { value: 'medium', label: 'Medium' },
  { value: 'high',   label: 'High'   },
  { value: 'urgent', label: 'Urgent' },
];

const DOCS_URL = 'https://docs.visaflow.com';

/* ════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════ */

export default function HelpSupport() {
  const [category, setCategory]   = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [faqs, setFaqs]                 = useState<SupportArticle[]>([]);
  const [faqsLoading, setFaqsLoading]   = useState(true);
  const [faqsError, setFaqsError]       = useState<string | null>(null);

  const [popular, setPopular]               = useState<SupportArticle[]>([]);
  const [popularLoading, setPopularLoading] = useState(true);

  const [systemStatus, setSystemStatus]               = useState<SystemStatusResponse | null>(null);
  const [systemStatusLoading, setSystemStatusLoading] = useState(true);

  const [ticketModalOpen, setTicketModalOpen] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput.trim()), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const loadFaqs = useCallback(async () => {
    setFaqsLoading(true);
    setFaqsError(null);
    try {
      const res = await supportApi.listArticles({
        article_type: 'faq',
        category:     category ?? undefined,
        search:       debouncedSearch || undefined,
        limit:        10,
        page:         1,
      });
      setFaqs(res.items ?? []);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load FAQs.';
      setFaqsError(msg);
      // eslint-disable-next-line no-console
      console.error('[HelpSupport] FAQ load error:', e);
    } finally {
      setFaqsLoading(false);
    }
  }, [category, debouncedSearch]);

  useEffect(() => { loadFaqs(); }, [loadFaqs]);

  useEffect(() => {
    (async () => {
      setPopularLoading(true);
      try {
        const res = await supportApi.listArticles({ featured: true, limit: 3 });
        setPopular(res.items ?? []);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('[HelpSupport] popular articles error:', e);
      } finally {
        setPopularLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      setSystemStatusLoading(true);
      try {
        const res = await supportApi.getSystemStatus();
        setSystemStatus(res);
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('[HelpSupport] system status error:', e);
      } finally {
        setSystemStatusLoading(false);
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <main className="mx-auto max-w-[1280px] space-y-6 px-4 py-6 sm:space-y-8 sm:px-6 sm:py-8 lg:px-8 lg:py-10">

        {/* ── HERO + SEARCH ─────────────────────────────────────── */}
        <section className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 sm:h-14 sm:w-14">
            <img src={iconHelpCircle} alt="" className="h-6 w-6 sm:h-7 sm:w-7" />
          </div>
          <h1 className="mt-4 text-xl font-bold tracking-tight text-gray-900 sm:mt-5 sm:text-3xl lg:text-4xl">
            How can we help you, Admin?
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-500 sm:text-base">
            Search our knowledge base for platform configurations, user management, and technical documentation.
          </p>

          <div className="mt-5 flex w-full max-w-2xl flex-col gap-2 rounded-xl border border-gray-200 bg-white p-2 shadow-sm sm:mt-6 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <img src={iconSearch} alt="" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 opacity-60" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search for articles, guides, and FAQs..."
                className="w-full rounded-lg bg-transparent py-2 pl-9 pr-3 text-sm placeholder-gray-400 focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => setDebouncedSearch(searchInput.trim())}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"
            >
              Search
            </button>
          </div>
        </section>

        {/* ── CATEGORY TABS ─────────────────────────────────────── */}
        <section>
          <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-3">
            {CATEGORIES.map((c) => {
              const isActive = category === c.key;
              return (
                <button
                  key={c.label}
                  onClick={() => setCategory(c.key)}
                  className={`relative rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive ? 'text-indigo-700' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {c.label}
                  {isActive && <span className="absolute inset-x-2 -bottom-3 h-0.5 rounded-full bg-indigo-600" />}
                </button>
              );
            })}
          </div>
        </section>

        {/* ── MAIN GRID: FAQ + SIDEBAR ──────────────────────────── */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Card>
              <h2 className="text-lg font-semibold text-gray-900">Frequently Asked Questions</h2>
              {faqsError && (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {faqsError}{' '}
                  <button onClick={loadFaqs} className="ml-2 font-semibold underline">Retry</button>
                </div>
              )}
              <div className="mt-5 divide-y divide-gray-100">
                {faqsLoading ? Array.from({ length: 5 }).map((_, i) => <FaqSkeleton key={i} />)
                  : faqs.length === 0 ? (
                    <p className="py-10 text-center text-sm text-gray-500">
                      No FAQs found{debouncedSearch && ` for "${debouncedSearch}"`}.
                    </p>
                  ) : faqs.map((f) => <FaqItem key={f.id} faq={f} />)}
              </div>
              {!faqsLoading && faqs.length > 0 && (
                <div className="mt-6 flex justify-center">
                  <button
                    onClick={() => {
                      // eslint-disable-next-line no-console
                      console.log('[HelpSupport] View All Articles');
                    }}
                    className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    View All Articles
                    <img src={iconChevronRight} alt="" className="h-4 w-4" />
                  </button>
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-6">
            <PopularArticlesCard loading={popularLoading} items={popular} />
            <SystemStatusCard loading={systemStatusLoading} status={systemStatus} />
          </div>
        </section>

        {/* ── STILL NEED HELP? ──────────────────────────────────── */}
        <section>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Still need help?</h2>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <ContactCard
              iconSrc={iconTicket}
              iconBg="bg-indigo-100"
              title="Submit a Ticket"
              description="Create a support ticket for complex technical issues. Our engineering team responds within 2 hours."
              actionLabel="Create Ticket"
              actionGradient="from-indigo-500 to-purple-600"
              onAction={() => setTicketModalOpen(true)}
            />
            <ContactCard
              iconSrc={iconMessageSquare}
              iconBg="bg-purple-100"
              title="Live Chat"
              description="Chat directly with a Tier 2 support agent for immediate assistance with platform configurations."
              actionLabel="Start Chat"
              onAction={() => {
                // eslint-disable-next-line no-console
                console.log('[HelpSupport] Live Chat');
                alert('Live chat coming soon. For now, please submit a ticket.');
              }}
            />
            <ContactCard
              iconSrc={iconBookOpen}
              iconBg="bg-emerald-100"
              title="Documentation"
              description="Browse our comprehensive API references, admin guides, and integration tutorials."
              actionLabel="Go to Docs"
              onAction={() => window.open(DOCS_URL, '_blank', 'noopener,noreferrer')}
            />
          </div>
        </section>
      </main>

      {ticketModalOpen && <TicketModal onClose={() => setTicketModalOpen(false)} />}
    </div>
  );
}

function FaqItem({ faq }: { faq: SupportArticle }) {
  const [open, setOpen]         = useState(false);
  const [body, setBody]         = useState<string | null>(faq.body || null);
  const [loading, setLoading]   = useState(false);
  const fetchedRef              = useRef(false);

  const handleToggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && !fetchedRef.current && !body) {
      fetchedRef.current = true;
      setLoading(true);
      try {
        const full = await supportApi.getArticle(faq.id);
        setBody(full.body || full.summary || '');
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn('[HelpSupport] article body error:', e);
        setBody(faq.summary || '');
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div>
      <button onClick={handleToggle} className="flex w-full items-center justify-between gap-3 py-4 text-left">
        <span className="text-sm font-medium text-gray-900">{faq.title}</span>
        <img
          src={iconChevronDown}
          alt=""
          className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : 'rotate-0'}`}
        />
      </button>
      {open && (
        <div className="pb-5 pl-1 pr-6 text-sm text-gray-600">
          {loading ? (
            <div className="flex items-center gap-2 text-gray-400">
              <img src={iconLoader} alt="" className="h-3.5 w-3.5 animate-spin" />
              Loading…
            </div>
          ) : (
            <p className="whitespace-pre-line leading-relaxed">{body || faq.summary || 'No content available.'}</p>
          )}
        </div>
      )}
    </div>
  );
}

function FaqSkeleton() {
  return (
    <div className="animate-pulse py-4">
      <div className="flex items-center justify-between">
        <div className="h-3 w-3/5 rounded bg-gray-200" />
        <div className="h-3 w-3 rounded bg-gray-200" />
      </div>
    </div>
  );
}

function PopularArticlesCard({ loading, items }: { loading: boolean; items: SupportArticle[] }) {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-gray-900">Popular Articles</h3>
      <div className="mt-4 space-y-3">
        {loading ? Array.from({ length: 3 }).map((_, i) => <PopularSkeleton key={i} />)
          : items.length === 0 ? <p className="text-xs text-gray-500">No featured articles yet.</p>
          : items.map((a) => (
            <a
              key={a.id}
              href={`#article-${a.id}`}
              onClick={(e) => {
                e.preventDefault();
                supportApi.getArticle(a.id).catch(() => {});
              }}
              className="group flex items-start gap-2"
            >
              <img src={iconFileText} alt="" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-gray-900 group-hover:text-indigo-700">{a.title}</p>
                <p className="mt-0.5 text-[11px] text-gray-500">Updated {timeAgo(a.updated_at)}</p>
              </div>
            </a>
          ))}
      </div>
    </Card>
  );
}

function PopularSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-3 w-4/5 rounded bg-gray-200" />
      <div className="mt-2 h-2 w-1/3 rounded bg-gray-200" />
    </div>
  );
}

function SystemStatusCard({ loading, status }: { loading: boolean; status: SystemStatusResponse | null }) {
  const overallOk = useMemo(() => {
    const s = (status?.overall_status ?? '').toLowerCase();
    return s.includes('operational') || s.includes('ok');
  }, [status]);

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">System Status</h3>
        {!loading && status && (
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
            overallOk ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200' : 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${overallOk ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            {status.overall_status || 'Unknown'}
          </span>
        )}
      </div>
      <div className="mt-4 space-y-2">
        {loading ? Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex animate-pulse items-center justify-between">
            <div className="h-3 w-24 rounded bg-gray-200" />
            <div className="h-3 w-16 rounded bg-gray-200" />
          </div>
        )) : !status || status.services.length === 0 ? (
          <p className="text-xs text-gray-500">No status data yet.</p>
        ) : status.services.map((s) => (
          <div key={s.service_name} className="flex items-center justify-between text-xs">
            <span className="text-gray-700">{s.service_name}</span>
            <span className={`font-semibold ${
              s.status === 'operational' ? 'text-emerald-600'
              : s.status === 'degraded' ? 'text-amber-600' : 'text-red-600'
            }`}>
              {s.uptime_label || s.status_badge || s.status}
            </span>
          </div>
        ))}
      </div>
      {!loading && status?.view_status_page_url && (
        <a href={status.view_status_page_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700">
          View Status Page
          <img src={iconExternalLink} alt="" className="h-3 w-3" />
        </a>
      )}
    </Card>
  );
}

function ContactCard({
  iconSrc, iconBg, title, description, actionLabel, actionGradient, onAction,
}: {
  iconSrc: string; iconBg: string; title: string; description: string;
  actionLabel: string; actionGradient?: string; onAction: () => void;
}) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm">
      <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${iconBg}`}>
        <img src={iconSrc} alt="" className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-xs text-gray-600">{description}</p>
      <button
        onClick={onAction}
        className={`mt-5 w-full rounded-lg px-4 py-2 text-sm font-semibold ${
          actionGradient
            ? `bg-gradient-to-r ${actionGradient} text-white shadow-md hover:opacity-95`
            : 'border border-gray-200 text-gray-700 hover:bg-gray-50'
        }`}
      >
        {actionLabel}
      </button>
    </div>
  );
}

function TicketModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<CreateTicketBody>({
    subject: '', body: '', category: 'technical', priority: 'medium',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [success, setSuccess]       = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.subject.trim() || !form.body.trim()) {
      setError('Subject and description are required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await supportApi.createTicket(form);
      setSuccess(`Ticket ${res.ticket_number || res.id} created. Our team will respond within 2 hours.`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail
        : Array.isArray(detail) ? (detail as { msg?: string }[]).map((d) => d.msg).filter(Boolean).join('; ')
        : err.message ?? 'Failed to create ticket.';
      setError(msg);
      // eslint-disable-next-line no-console
      console.error('[HelpSupport] ticket error:', e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Submit a Support Ticket</h3>
            <p className="mt-1 text-sm text-gray-500">Describe your issue — our engineering team responds within 2 hours.</p>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-gray-400 hover:bg-gray-100">
            <img src={iconXClose} alt="" className="h-5 w-5" />
          </button>
        </div>

        {success ? (
          <div className="mt-6 flex flex-col items-center text-center">
            <img src={iconCheckCircle} alt="" className="h-12 w-12" />
            <p className="mt-3 text-base font-semibold text-gray-900">Ticket submitted</p>
            <p className="mt-1 text-sm text-gray-600">{success}</p>
            <button onClick={onClose} className="mt-5 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Done</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                <img src={iconAlertCircle} alt="" className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-700">Subject</label>
              <input type="text" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })}
                placeholder="e.g. Cannot configure USCIS integration"
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-700">Category</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none">
                  {TICKET_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700">Priority</label>
                <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none">
                  {TICKET_PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Description</label>
              <textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })}
                rows={5} placeholder="Describe what you're seeing, what you expected, and any error messages..."
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button type="button" onClick={onClose} className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
              <button type="submit" disabled={submitting}
                className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-95 disabled:opacity-60">
                {submitting && <img src={iconLoader} alt="" className="h-3.5 w-3.5 animate-spin" />}
                Submit Ticket
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}>{children}</div>;
}

function timeAgo(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const diffMs = Date.now() - d.getTime();
  const day = 24 * 60 * 60 * 1000;
  const week = 7 * day;
  const month = 30 * day;
  if (diffMs < day) return 'today';
  if (diffMs < 2 * day) return '1 day ago';
  if (diffMs < week) return `${Math.round(diffMs / day)} days ago`;
  if (diffMs < 2 * week) return '1 week ago';
  if (diffMs < month) return `${Math.round(diffMs / week)} weeks ago`;
  return `${Math.round(diffMs / month)} months ago`;
}
