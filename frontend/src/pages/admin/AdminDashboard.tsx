// src/pages/admin/AdminDashboard.tsx
//
// Admin Dashboard — uses SVG assets from src/assets/icons/admin-dashboard/
// for main visual icons (KPI tiles, trends, tabs) to match the project's
// existing pattern (same as Sidebar.tsx). Utility icons (Search, Plus,
// Pencil, etc.) continue using lucide-react.
//
// All data hardcoded except Resource Allocation widget (real API).

import { useEffect, useState, useMemo } from 'react';
import {
  // Utility icons (kept as lucide-react — small, action-style icons)
  Download,
  Search,
  Plus,
  Pencil,
  Eye,
  ExternalLink,
  AlertTriangle,
  RotateCcw,
  Megaphone,
  Wrench,
  Loader2,
  ChevronRight,
  Sparkles,
  Mail,
  FileText,
  ShieldAlert,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import { workspaceApi } from '../../api/admin/workspace.api';
import type { TeamMember } from '../../types/admin/workspace.types';

/* ── SVG assets — admin-dashboard icon set ──────────────────────────── */
// KPI stat icons (white stroke baked in)
import iconStatUsers      from '../../assets/icons/admin-dashboard/stat-users.svg';
import iconStatCases      from '../../assets/icons/admin-dashboard/stat-cases.svg';
import iconStatVisaTypes  from '../../assets/icons/admin-dashboard/stat-visa-types.svg';
import iconStatDocTypes   from '../../assets/icons/admin-dashboard/stat-doc-types.svg';
import iconStatAiAccuracy from '../../assets/icons/admin-dashboard/stat-ai-accuracy.svg';
import iconStatPending    from '../../assets/icons/admin-dashboard/stat-pending.svg';

// Trend indicator icons (each has its own colour baked in)
import iconTrendUp      from '../../assets/icons/admin-dashboard/trend-up.svg';
import iconTrendCheck   from '../../assets/icons/admin-dashboard/trend-check.svg';
import iconTrendDotBlue from '../../assets/icons/admin-dashboard/trend-dot-blue.svg';
import iconTrendDotRed  from '../../assets/icons/admin-dashboard/trend-dot-red.svg';

// Tab icons (gray default; CSS filter inverts to white when active)
import iconTabDashboard       from '../../assets/icons/admin-dashboard/tab-dashboard.svg';
import iconTabDocRules        from '../../assets/icons/admin-dashboard/tab-doc-rules.svg';
import iconTabDocGuides       from '../../assets/icons/admin-dashboard/tab-doc-guides.svg';
import iconTabLetterTemplates from '../../assets/icons/admin-dashboard/tab-letter-templates.svg';
import iconTabAiExtraction    from '../../assets/icons/admin-dashboard/tab-ai-extraction.svg';
import iconTabEmergency       from '../../assets/icons/admin-dashboard/tab-emergency.svg';

// CSS filter that turns any-coloured SVG into pure white (used on active tab)
const FILTER_WHITE = 'brightness(0) invert(1)';

/* ════════════════════════════════════════════════════════════════════════
   HARDCODED DATA
═══════════════════════════════════════════════════════════════════════ */

const KPI_STATS = [
  {
    icon: iconStatUsers,
    iconBg: '#2563eb',
    cardGrad: 'linear-gradient(133.94deg, #eff6ff 0%, #dbeafe 100%)',
    value: '12,458',
    label: 'Total Users',
    trend: '+12.5% this month',
    trendColor: '#16a34a',
    trendIcon: iconTrendUp,
  },
  {
    icon: iconStatCases,
    iconBg: '#9333ea',
    cardGrad: 'linear-gradient(133.94deg, #faf5ff 0%, #f3e8ff 100%)',
    value: '3,892',
    label: 'Active Cases',
    trend: '+8.3% this month',
    trendColor: '#16a34a',
    trendIcon: iconTrendUp,
  },
  {
    icon: iconStatVisaTypes,
    iconBg: '#16a34a',
    cardGrad: 'linear-gradient(133.94deg, #f0fdf4 0%, #dcfce7 100%)',
    value: '52',
    label: 'Visa Types',
    trend: 'All configured',
    trendColor: '#2563eb',
    trendIcon: iconTrendDotBlue,
  },
  {
    icon: iconStatDocTypes,
    iconBg: '#ea580c',
    cardGrad: 'linear-gradient(133.94deg, #fff7ed 0%, #ffedd5 100%)',
    value: '284',
    label: 'Document Types',
    trend: 'Managed',
    trendColor: '#4b5563',
    trendIcon: iconTrendCheck,
  },
  {
    icon: iconStatAiAccuracy,
    iconBg: '#4f46e5',
    cardGrad: 'linear-gradient(133.94deg, #eef2ff 0%, #e0e7ff 100%)',
    value: '98.7%',
    label: 'AI Accuracy',
    trend: '+2.1% improved',
    trendColor: '#16a34a',
    trendIcon: iconTrendUp,
  },
  {
    icon: iconStatPending,
    iconBg: '#dc2626',
    cardGrad: 'linear-gradient(133.94deg, #fef2f2 0%, #fee2e2 100%)',
    value: '7',
    label: 'Pending Issues',
    trend: 'Requires attention',
    trendColor: '#dc2626',
    trendIcon: iconTrendDotRed,
  },
];

const TABS = [
  { id: 'dashboard',         label: 'Dashboard',           icon: iconTabDashboard       },
  { id: 'document-rules',    label: 'Document Rules',      icon: iconTabDocRules        },
  { id: 'document-guides',   label: 'Document Guides',     icon: iconTabDocGuides       },
  { id: 'letter-templates',  label: 'Letter Templates',    icon: iconTabLetterTemplates },
  { id: 'ai-extraction',     label: 'AI Extraction Rules', icon: iconTabAiExtraction    },
  { id: 'emergency',         label: 'Emergency Controls',  icon: iconTabEmergency       },
];

const UPTIME_DATA = Array.from({ length: 30 }, (_, i) => ({
  day: `Day ${i + 1}`,
  uptime: +(99.85 + Math.random() * 0.14).toFixed(2),
}));

const CASE_VOLUME_DATA = Array.from({ length: 30 }, (_, i) => ({
  day: `Day ${i + 1}`,
  created:   80 + Math.round(Math.random() * 40),
  completed: 70 + Math.round(Math.random() * 35),
}));

const DOCUMENT_RULES = [
  { id: 'DR-001', name: 'Valid Passport',         visa: 'H-1B, L-1, O-1',  purpose: 'Essential travel document',                       type: 'Mandatory'   as const, provider: 'Applicant',          when: 'Always'         },
  { id: 'DR-002', name: 'Employment Letter',      visa: 'H-1B',             purpose: 'Confirms employment details and compensation',    type: 'Mandatory'   as const, provider: 'Employer',           when: 'At submission'  },
  { id: 'DR-003', name: 'STEM OPT Training Plan', visa: 'OPT',              purpose: 'Training plan between student and employer',      type: 'Conditional' as const, provider: 'Employer + DSO',     when: 'If STEM OPT'    },
  { id: 'DR-004', name: 'Degree Certificate',     visa: 'H-1B, L-1, O-1',  purpose: 'Proves educational qualifications',               type: 'Mandatory'   as const, provider: 'Institution',        when: 'At submission'  },
  { id: 'DR-005', name: 'Marriage Certificate',   visa: 'F-2, H-4, L-2',   purpose: 'Proof of spousal relationship',                   type: 'Conditional' as const, provider: 'Applicant',          when: 'If spouse dep.' },
  { id: 'DR-006', name: 'Translation Required',   visa: 'All',              purpose: 'Certified English translation of foreign docs',   type: 'Conditional' as const, provider: 'Cert. Translator',   when: 'If not English' },
];

const DOCUMENT_GUIDES = [
  { id: 'guide-i129',     title: 'Form I-129',         subtitle: 'Petition for Nonimmigrant Worker', description: 'Official USCIS petition form for H-1B and other work visas', color: '#2563eb', updated: '2 days ago', fields: '12 fields', types: '8 Types',  downloadUrl: 'https://www.uscis.gov/i-129' },
  { id: 'guide-i983',     title: 'Form I-983',         subtitle: 'STEM OPT Training Plan',           description: 'Training plan agreement between student, employer, and university', color: '#9333ea', updated: '5 days ago', fields: '15 fields', types: '4 Types',  downloadUrl: '#' },
  { id: 'guide-degree',   title: 'Degree Certificate', subtitle: 'Educational Qualification',         description: 'Educational qualification proof, must be translated if not English', color: '#16a34a', updated: '1 week ago', fields: '9 fields',  types: '12 Types', downloadUrl: '#' },
  { id: 'guide-passport', title: 'Passport',           subtitle: 'Travel Document',                   description: 'Official identification for international travel and visa applications', color: '#ea580c', updated: '3 days ago', fields: '28 fields', types: '18 Types', downloadUrl: '#' },
];

const LETTER_TEMPLATES = [
  { id: 'template-employment', name: 'Employment Verification Letter', desc: 'Standard letter confirming employment, salary, and responsibilities', generated: 1567, badge: 'Active',       color: '#2563eb' },
  { id: 'template-support',    name: 'Support Letter',                 desc: 'Employer letter supporting visa application with justification',     generated: 892,  badge: 'Active',       color: '#9333ea' },
  { id: 'template-offer',      name: 'Job Offer Letter',               desc: 'Formal employment offer with position details and compensation',     generated: 1245, badge: 'MOST POPULAR', color: '#16a34a' },
  { id: 'template-lca',        name: 'LCA Public Notice',              desc: 'Required public access file notice for H-1B Labor Conditions',       generated: 678,  badge: 'Active',       color: '#0891b2' },
  { id: 'template-itinerary',  name: 'Travel Itinerary Letter',        desc: 'Business travel justification with detailed schedule and purpose',   generated: 456,  badge: 'Active',       color: '#ea580c' },
  { id: 'template-extension',  name: 'Extension Request Letter',       desc: 'Letter supporting visa extension with continued employment details', generated: 2134, badge: 'Active',       color: '#4f46e5' },
];

const AI_PERFORMANCE_DATA = Array.from({ length: 4 }, (_, i) => ({
  week: `Week ${i + 1}`,
  accuracy: +(95 + Math.random() * 4).toFixed(1),
}));

const AI_DOC_TYPES = [
  { name: 'Employment Letters', value: 32.3, color: '#2563eb' },
  { name: 'Degree Certificates', value: 22.5, color: '#9333ea' },
  { name: 'I-129 Forms',         value: 23.8, color: '#16a34a' },
  { name: 'Passports',           value: 13.2, color: '#ea580c' },
  { name: 'Others',              value: 8.19, color: '#6b7280' },
];

const AI_EXTRACTION_RULES = [
  { id: 'rule-employment', title: 'Employment Letter Parser',        desc: 'Extracts job title, salary, start date, employer details, and responsibilities', accuracy: '95%', fields: '15 fields', status: 'Active' as const, lastUsed: '2 minutes ago' },
  { id: 'rule-degree',     title: 'Degree Certificate Analysis',     desc: 'Extracts institution name, degree type, major, graduation date, and GPA',         accuracy: '97%', fields: '12 fields', status: 'Active' as const, lastUsed: '15 minutes ago' },
  { id: 'rule-i129',       title: 'I-129 Form Data Extraction',      desc: 'Extracts petition details, beneficiary info, and employer data from I-129',       accuracy: '98%', fields: '28 fields', status: 'Active' as const, lastUsed: '1 hour ago' },
  { id: 'rule-passport',   title: 'Passport Information Extraction', desc: 'Extracts passport number, expiry date, nationality, and personal details',        accuracy: '99%', fields: '9 fields',  status: 'Active' as const, lastUsed: '3 hours ago' },
];

const EMERGENCY_CONTROLS = [
  { id: 'emergency-bypass',       title: 'Mandatory Field Bypass', desc: 'Temporarily allow case submission without mandatory documents in emergency situations', actionLabel: 'Activate Bypass',     actionColor: '#dc2626', bgColor: '#fef2f2', borderColor: '#fecaca', icon: AlertTriangle, iconColor: '#dc2626', lastUsed: '7 days ago',           severity: 'Use with Caution'  },
  { id: 'emergency-maintenance',  title: 'Maintenance Mode',       desc: 'Put system in maintenance mode, blocking all user access except admins',                  actionLabel: 'Enable Maintenance',  actionColor: '#ea580c', bgColor: '#fff7ed', borderColor: '#fed7aa', icon: Wrench,        iconColor: '#ea580c', lastUsed: '15 days ago (2 hours)', severity: 'Last Maintenance'   },
  { id: 'emergency-rollback',     title: 'Configuration Rollback', desc: 'Restore system configuration to previous stable state',                                    actionLabel: 'View Backups',         actionColor: '#2563eb', bgColor: '#eff6ff', borderColor: '#bfdbfe', icon: RotateCcw,     iconColor: '#2563eb', lastUsed: 'Today at 3:00 AM',      severity: 'Latest Backup'      },
  { id: 'emergency-notification', title: 'System-Wide Broadcast',  desc: 'Send urgent notification to all active users and administrators',                          actionLabel: 'Send Broadcast',       actionColor: '#9333ea', bgColor: '#faf5ff', borderColor: '#e9d5ff', icon: Megaphone,     iconColor: '#9333ea', lastUsed: 'Never',                 severity: 'Last Broadcast'      },
];

/* ════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════ */

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  const handleTabClick = (id: string) => {
    setActiveTab(id);
    const el = document.getElementById(`section-${id}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* ── HERO — compact on all screens ───────────────────────── */}
      <section
        className="px-4 py-5 sm:px-8 sm:py-6 lg:py-7"
        style={{ backgroundImage: 'linear-gradient(90deg, #2563eb 0%, #9333ea 50%, #4f46e5 100%)' }}
      >
        <div className="mx-auto max-w-[1280px]">
          <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl lg:text-[26px]">
            Admin Console
          </h1>
          <p className="mt-1 text-sm text-white/90 sm:text-[15px]">
            Complete system control and configuration management
          </p>
        </div>
      </section>

      <main className="mx-auto max-w-[1280px] space-y-8 px-8 py-8">
        {/* ── KPI STATS ─────────────────────────────────────────── */}
        <section id="section-dashboard">
          <div className="grid grid-cols-2 gap-5 md:grid-cols-3 lg:grid-cols-6">
            {KPI_STATS.map((s) => (
              <KpiCard key={s.label} {...s} />
            ))}
          </div>
        </section>

        {/* ── TAB NAV ───────────────────────────────────────────── */}
        <section className="-mt-2">
          <div className="flex flex-wrap gap-2">
            {TABS.map((t) => {
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => handleTabClick(t.id)}
                  className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-transparent bg-blue-600 text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <img
                    src={t.icon}
                    alt=""
                    aria-hidden="true"
                    className="h-4 w-4"
                    style={{ filter: isActive ? FILTER_WHITE : 'none' }}
                  />
                  {t.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* ── SYSTEM HEALTH CHARTS ──────────────────────────────── */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="System Uptime (Last 30 Days)"
              subtitle="Real-time monitoring and availability"
              right={
                <span className="rounded-md bg-emerald-100 px-3 py-1.5 text-sm font-semibold text-emerald-700">
                  99.98%
                </span>
              }
            />
            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={UPTIME_DATA}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
                  <YAxis domain={[99.85, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} formatter={(v) => `${v}%`} />
                  <Line type="monotone" dataKey="uptime" stroke="#16a34a" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Case Processing Volume"
              subtitle="Daily case creation and completion"
              right={
                <button className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700">
                  <Download className="h-3.5 w-3.5" />
                  Export
                </button>
              }
            />
            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={CASE_VOLUME_DATA} barCategoryGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} />
                  <Bar dataKey="created"   fill="#2563eb" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="completed" fill="#16a34a" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </section>

        {/* ── DOCUMENT RULES ENGINE ─────────────────────────────── */}
        <section id="section-document-rules">
          <Card>
            <CardHeader
              title="Document Rules Engine"
              subtitle="Define mandatory, conditional, and optional document requirements"
              right={
                <button className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  <Plus className="h-4 w-4" />
                  Create New Rule
                </button>
              }
            />
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search rules..."
                  className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
              </div>
              <select className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <option>All Visa Types</option><option>H-1B</option><option>L-1</option><option>OPT</option>
              </select>
              <select className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700">
                <option>All Rule Types</option><option>Mandatory</option><option>Conditional</option><option>Optional</option>
              </select>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-gray-50">
                  <tr className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    <th className="px-4 py-3">Rule ID</th>
                    <th className="px-4 py-3">Document</th>
                    <th className="px-4 py-3">Visa Type</th>
                    <th className="px-4 py-3">Purpose</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Provider</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {DOCUMENT_RULES.map((r) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-xs font-mono text-gray-600">{r.id}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.name}</td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.visa}</td>
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate" title={r.purpose}>{r.purpose}</td>
                      <td className="px-4 py-3"><RequirementPill type={r.type} /></td>
                      <td className="px-4 py-3 text-xs text-gray-600">{r.provider}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <IconButton icon={Pencil} label="Edit" />
                          <IconButton icon={Eye}    label="View" />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-gray-500">Showing 6 of 284 rules</p>
          </Card>
        </section>

        {/* ── DOCUMENT GUIDES ───────────────────────────────────── */}
        <section id="section-document-guides">
          <Card>
            <CardHeader
              title="Document Guides & Download Links"
              subtitle="Manage preparation guides and official form downloads for each document type"
              right={
                <button className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  <Plus className="h-4 w-4" />
                  Add Document Guide
                </button>
              }
            />
            <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
              {DOCUMENT_GUIDES.map((g) => (
                <div key={g.id} className="rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
                        style={{ backgroundColor: `${g.color}1a` }}
                      >
                        <FileText className="h-5 w-5" style={{ color: g.color }} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{g.title}</p>
                        <p className="text-xs font-medium text-gray-500">{g.subtitle}</p>
                      </div>
                    </div>
                    <span className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-200">
                      Ready
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-gray-600">{g.description}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    <span>{g.fields}</span>
                    <span>•</span>
                    <span>{g.types}</span>
                    <span>•</span>
                    <span>Last updated: {g.updated}</span>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <a
                      href={g.downloadUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Download Link
                    </a>
                    <button className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">
                      <Pencil className="h-3 w-3" />
                      Edit Guide
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>

        {/* ── LETTER TEMPLATES MANAGER ──────────────────────────── */}
        <section id="section-letter-templates">
          <Card>
            <CardHeader
              title="Letter Templates Manager"
              subtitle="Configure automated letter generation templates for different visa types"
              right={
                <button className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  <Plus className="h-4 w-4" />
                  Create Template
                </button>
              }
            />
            <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
              {LETTER_TEMPLATES.map((t) => (
                <div key={t.id} className="rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ backgroundColor: `${t.color}1a` }}>
                      <Mail className="h-5 w-5" style={{ color: t.color }} />
                    </div>
                    {t.badge === 'MOST POPULAR' ? (
                      <span className="rounded-full bg-gradient-to-r from-amber-400 to-orange-500 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white">
                        {t.badge}
                      </span>
                    ) : (
                      <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-200">
                        {t.badge}
                      </span>
                    )}
                  </div>
                  <p className="mt-3 text-sm font-semibold text-gray-900">{t.name}</p>
                  <p className="mt-1 text-xs text-gray-600">{t.desc}</p>
                  <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3">
                    <span className="text-xs font-medium text-gray-500">{t.generated.toLocaleString()} letters generated</span>
                    <button className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
                      Configure
                      <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>

        {/* ── AI EXTRACTION RULES CONFIGURATION ─────────────────── */}
        <section id="section-ai-extraction">
          <Card>
            <CardHeader
              title="AI Extraction Rules Configuration"
              subtitle="Define how AI extracts and classifies data from uploaded documents"
              right={
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
                    <Sparkles className="h-3 w-3" />
                    98.7% Accuracy
                  </span>
                  <button className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                    <Plus className="h-4 w-4" />
                    Add Extraction Rule
                  </button>
                </div>
              }
            />

            <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-900">AI Extraction Performance</h4>
                <div className="mt-3 h-44">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={AI_PERFORMANCE_DATA}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                      <XAxis dataKey="week" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[90, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
                      <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} formatter={(v) => `${v}%`} />
                      <Line type="monotone" dataKey="accuracy" stroke="#4f46e5" strokeWidth={2.5} dot={{ r: 4, fill: '#4f46e5' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 p-4">
                <h4 className="text-sm font-semibold text-gray-900">Documents Processed by Type</h4>
                <div className="mt-3 flex h-44 items-center">
                  <ResponsiveContainer width="50%" height="100%">
                    <PieChart>
                      <Pie data={AI_DOC_TYPES} dataKey="value" innerRadius={40} outerRadius={70} stroke="none">
                        {AI_DOC_TYPES.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12 }} formatter={(v) => `${v}%`} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-1.5">
                    {AI_DOC_TYPES.map((d) => (
                      <div key={d.name} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                          <span className="truncate text-gray-700">{d.name}</span>
                        </div>
                        <span className="font-semibold text-gray-900">{d.value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h4 className="mb-3 text-sm font-semibold text-gray-900">Active Extraction Rules</h4>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {AI_EXTRACTION_RULES.map((r) => (
                  <div key={r.id} className="rounded-xl border border-gray-200 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50">
                          <Sparkles className="h-4 w-4 text-indigo-600" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{r.title}</p>
                          <p className="mt-0.5 text-xs text-gray-600">{r.desc}</p>
                        </div>
                      </div>
                      <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-200">
                        {r.status}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
                      <span className="font-semibold text-indigo-600">{r.accuracy} accuracy</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600">{r.fields}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-500">Last used: {r.lastUsed}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </section>

        {/* ── EMERGENCY CONTROLS ────────────────────────────────── */}
        <section id="section-emergency">
          <Card>
            <CardHeader
              title="Emergency Controls & Overrides"
              subtitle="Critical system controls for emergency situations and override capabilities"
              right={
                <span className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 ring-1 ring-red-200">
                  <ShieldAlert className="h-3 w-3" />
                  Use with Caution
                </span>
              }
            />
            <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
              {EMERGENCY_CONTROLS.map((c) => {
                const Icon = c.icon;
                return (
                  <div
                    key={c.id}
                    className="rounded-xl border p-5"
                    style={{ borderColor: c.borderColor, backgroundColor: c.bgColor }}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white">
                        <Icon className="h-5 w-5" style={{ color: c.iconColor }} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-gray-900">{c.title}</p>
                        <p className="mt-1 text-xs text-gray-700">{c.desc}</p>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          <span className="text-[11px] text-gray-500">
                            {c.severity}: <span className="font-medium text-gray-700">{c.lastUsed}</span>
                          </span>
                          <button
                            className="rounded-lg px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:opacity-90"
                            style={{ backgroundColor: c.actionColor }}
                          >
                            {c.actionLabel}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </section>

        {/* ── RESOURCE ALLOCATION (REAL API) ────────────────────── */}
        <ResourceAllocationWidget />
      </main>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════
   RESOURCE ALLOCATION WIDGET — Real API: /api/v1/workspace/team
═══════════════════════════════════════════════════════════════════════ */

function ResourceAllocationWidget() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workspaceApi.getTeam();
      setMembers(res.items ?? []);
      setTotal(res.total ?? 0);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load team workload.';
      setError(msg);
      // eslint-disable-next-line no-console
      console.error('[ResourceAllocation] error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const sorted = useMemo(
    () =>
      [...members].sort((a, b) => {
        const aPct = a.max_active_cases > 0 ? a.active_case_count / a.max_active_cases : 0;
        const bPct = b.max_active_cases > 0 ? b.active_case_count / b.max_active_cases : 0;
        return bPct - aPct;
      }),
    [members],
  );

  return (
    <section id="section-resource-allocation">
      <Card>
        <CardHeader
          title="Resource Allocation"
          subtitle="Current workload of attorneys and HR staff across active cases"
          right={
            <div className="flex items-center gap-3">
              {!loading && (
                <span className="text-xs text-gray-500">
                  {total} team member{total === 1 ? '' : 's'}
                </span>
              )}
              <button
                onClick={load}
                disabled={loading}
                className="rounded-md border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Refresh'}
              </button>
            </div>
          }
        />

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}{' '}
            <button onClick={load} className="ml-2 font-semibold underline">Retry</button>
          </div>
        )}

        <div className="mt-5 space-y-3">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <RowSkeleton key={i} />)
            : sorted.length === 0
            ? <p className="py-8 text-center text-sm text-gray-500">No team members found.</p>
            : sorted.map((m) => <MemberRow key={m.id} member={m} />)
          }
        </div>
      </Card>
    </section>
  );
}

function MemberRow({ member }: { member: TeamMember }) {
  const fullName = `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim() || 'Unknown';
  const initials =
    (member.first_name?.[0] ?? '?') + (member.last_name?.[0] ?? '');
  const max = member.max_active_cases || 0;
  const cur = member.active_case_count || 0;
  const pct = max > 0 ? Math.min(100, Math.round((cur / max) * 100)) : 0;

  const { barColor, statusLabel, statusColor } = workloadStatus(pct, member.is_accepting_cases);

  return (
    <div className="rounded-xl border border-gray-100 p-4">
      <div className="flex items-center gap-3">
        <div className="relative shrink-0">
          {member.profile_picture_url ? (
            <img src={member.profile_picture_url} alt={fullName} className="h-10 w-10 rounded-full object-cover" />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
              {initials.toUpperCase()}
            </div>
          )}
          {member.is_online && (
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <p className="truncate text-sm font-semibold text-gray-900">{fullName}</p>
            <p className="text-xs text-gray-500">{prettyRole(member.role)}</p>
            {member.law_firm_name && (
              <>
                <span className="text-gray-300">•</span>
                <p className="truncate text-xs text-gray-500">{member.law_firm_name}</p>
              </>
            )}
          </div>
          <p className="mt-0.5 text-xs text-gray-500 truncate">{member.email}</p>
        </div>

        <div className="hidden md:flex items-center gap-4 text-xs">
          <Stat label="Cases"   value={`${cur} / ${max || '∞'}`} />
          <Stat label="Tasks"   value={member.pending_task_count} />
          <Stat label="Overdue" value={member.overdue_deadline_count} highlight={member.overdue_deadline_count > 0} />
        </div>

        <span
          className="shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
          style={{ backgroundColor: `${statusColor}1a`, color: statusColor }}
        >
          {statusLabel}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${pct}%`, backgroundColor: barColor }}
          />
        </div>
        <span className="w-10 shrink-0 text-right text-xs font-semibold" style={{ color: barColor }}>
          {pct}%
        </span>
      </div>
    </div>
  );
}

function workloadStatus(pct: number, isAccepting: boolean) {
  if (!isAccepting) return { barColor: '#6b7280', statusLabel: 'Not Accepting', statusColor: '#6b7280' };
  if (pct >= 90)    return { barColor: '#dc2626', statusLabel: 'At Capacity',   statusColor: '#dc2626' };
  if (pct >= 70)    return { barColor: '#ea580c', statusLabel: 'Heavy Load',    statusColor: '#ea580c' };
  if (pct >= 40)    return { barColor: '#2563eb', statusLabel: 'Active',        statusColor: '#2563eb' };
  return            { barColor: '#16a34a', statusLabel: 'Available',     statusColor: '#16a34a' };
}

function prettyRole(role: string): string {
  if (!role) return '';
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

function Stat({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className="text-center">
      <p className={`text-sm font-semibold ${highlight ? 'text-red-600' : 'text-gray-900'}`}>{value}</p>
      <p className="text-[10px] uppercase tracking-wide text-gray-400">{label}</p>
    </div>
  );
}

function RowSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-100 p-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-gray-200" />
        <div className="flex-1">
          <div className="h-3 w-32 rounded bg-gray-200" />
          <div className="mt-2 h-3 w-48 rounded bg-gray-200" />
        </div>
        <div className="h-5 w-16 rounded-full bg-gray-200" />
      </div>
      <div className="mt-3 h-2 rounded-full bg-gray-200" />
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════════
   SHARED PRIMITIVES
═══════════════════════════════════════════════════════════════════════ */

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 className="text-base font-semibold text-gray-900 sm:text-lg">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

function KpiCard({
  icon,
  iconBg,
  cardGrad,
  value,
  label,
  trend,
  trendColor,
  trendIcon,
}: {
  icon: string;
  iconBg: string;
  cardGrad: string;
  value: string;
  label: string;
  trend: string;
  trendColor: string;
  trendIcon: string;
}) {
  return (
    <div className="rounded-xl p-5" style={{ backgroundImage: cardGrad }}>
      <div
        className="flex h-12 w-12 items-center justify-center rounded-lg"
        style={{ backgroundColor: iconBg }}
      >
        <img src={icon} alt="" aria-hidden="true" className="h-5 w-5" />
      </div>
      <p className="mt-3 text-2xl font-bold tracking-tight text-gray-900">{value}</p>
      <p className="text-sm text-gray-600">{label}</p>
      <div className="mt-2 flex items-center gap-1 text-xs" style={{ color: trendColor }}>
        <img src={trendIcon} alt="" aria-hidden="true" className="h-3 w-3" />
        <span className="font-medium">{trend}</span>
      </div>
    </div>
  );
}

function RequirementPill({ type }: { type: 'Mandatory' | 'Conditional' | 'Optional' }) {
  const styles: Record<typeof type, string> = {
    Mandatory:   'bg-red-50 text-red-700 ring-red-200',
    Conditional: 'bg-amber-50 text-amber-700 ring-amber-200',
    Optional:    'bg-gray-50 text-gray-700 ring-gray-200',
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ${styles[type]}`}>
      {type}
    </span>
  );
}

function IconButton({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <button title={label} className="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-50 hover:text-gray-900">
      <Icon className="h-3.5 w-3.5" />
    </button>
  );
}
