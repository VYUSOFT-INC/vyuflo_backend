// src/components/layout/Sidebar.tsx
import { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, X, ChevronLeft } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { Avatar } from '../ui/Avatar';
import { getUiSession, type UiSession } from '../../utils/uiSession';
import { getFileUrl } from '../../utils/fileUrl';
import imgLogoIcon from '../../assets/icons/plane-icon.svg';

// ── Figma icon assets ───────────────────────────────────────────────────────
import iconDashboard     from '../../assets/icons/nav-dashboard.svg';
import iconApplications  from '../../assets/icons/icon-applications.svg';
import iconMessages      from '../../assets/icons/icon-messages.svg';
import iconDocuments     from '../../assets/icons/icon-documents.svg';
import iconSettings      from '../../assets/icons/icon-settings.svg';
import iconPayments      from '../../assets/icons/icon-payments.svg';
import iconConsultations from '../../assets/icons/icon-consultations.svg';
import iconNotification  from '../../assets/icons/dashboard-bell.svg';

// ─────────────────────────────────────────────────────────────────────────────
// Nav config
// ─────────────────────────────────────────────────────────────────────────────

const employeeNavItems = [
  { to: '/dashboard',         src: iconDashboard,     label: 'Application Dashboard' },
  { to: '/applications/list', src: iconApplications,  label: 'Applications'          },
  { to: '/messages',          src: iconMessages,      label: 'Messages'              },
  { to: '/documents',         src: iconDocuments,     label: 'Documents'             },
  { to: '/payments',          src: iconPayments,      label: 'Payments & Billing'    },
  { to: '/consultations',     src: iconConsultations, label: 'Book Consultation'     },
  { to: '/profile',           src: iconSettings,      label: 'Settings'              },
  { to: '/notifications',     src: iconNotification,  label: 'Notifications'         },
];

const adminNavItems = [
  { to: '/admin/dashboard',              src: iconDashboard,    label: 'Admin Dashboard'        },
  { to: '/admin/users',                  src: iconApplications, label: 'User Management'        },
  { to: '/admin/revenue-dashboard',      src: iconDashboard,    label: 'Revenue Dashboard'      },
  { to: '/admin/roles-permissions',      src: iconSettings,     label: 'Roles & Permissions'    },
  { to: '/admin/settings',               src: iconSettings,     label: 'System Settings'        },
  { to: '/admin/notification-templates', src: iconMessages,     label: 'Notification Templates' },
  { to: '/admin/visa-types',             src: iconDocuments,    label: 'Visa Types Manager'     },
  { to: '/admin/system-audit-logs',      src: iconSettings,     label: 'System Audit Logs'      },
  { to: '/admin/subscription-pricing',   src: iconDashboard,    label: 'Subscription & Pricing' },
  { to: '/admin/help-support',           src: iconMessages,     label: 'Help & Support'         },
];

// Lawyer (attorney) nav
const lawyerNavItems = [
  { to: '/lawyer/intake', src: iconDocuments, label: 'Client Intake' },
];

// System Settings sub-sections (hash-routed, shown on /admin/settings)
const settingsNavItems = [
  { hash: '#general',       src: iconSettings,     label: 'General Settings'  },
  { hash: '#security',      src: iconSettings,     label: 'Security & Access' },
  { hash: '#integrations',  src: iconApplications, label: 'Integrations'      },
  { hash: '#notifications', src: iconMessages,     label: 'Notifications'     },
  { hash: '#feature-flags', src: iconDashboard,    label: 'Feature Flags'     },
  { hash: '#maintenance',   src: iconDocuments,    label: 'Maintenance'       },
];

// Display-only sub-sections (no nav, just visual context)
const visaTypesNavItems     = [{ src: iconDocuments, label: 'Visa Types Manager'      }];
const subscriptionNavItems  = [{ src: iconDashboard, label: 'Subscription & Pricing'  }];

// CSS filter: default #64748b SVG fill → active indigo #3a46e5
const ACTIVE_FILTER =
  'brightness(0) saturate(100%) invert(20%) sepia(96%) saturate(1500%) hue-rotate(222deg) brightness(95%) contrast(98%)';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatRole(role?: string): string {
  if (!role) return '';
  return role
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sidebar
// ─────────────────────────────────────────────────────────────────────────────

export function Sidebar({ open, onClose, collapsed, onToggleCollapse }: SidebarProps) {
  const { clearAuth: logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // ── Read ui_session cookie — re-reads on profile update event ──────────
  const [session, setSession] = useState<UiSession | null>(null);

  useEffect(() => {
    setSession(getUiSession());
    const handler = () => setSession(getUiSession());
    window.addEventListener('ui-session-updated', handler);
    return () => window.removeEventListener('ui-session-updated', handler);
  }, []);

  // ── Derived display values ─────────────────────────────────────────────
  const fullName  = session
    ? `${session.first_name} ${session.last_name}`.trim() || 'User'
    : 'User';
  const avatarUrl = getFileUrl(session?.profile ?? null);
  const roleLabel = formatRole(session?.roles?.[0]);
  const isAdmin   = (session?.roles ?? []).includes('app_admin');
  const isLawyer  = (session?.roles ?? []).includes('attorney');

  // ── Page context flags (drive which nav block renders) ─────────────────
  const isSettingsPage            = location.pathname.startsWith('/admin/settings');
  const isVisaTypesPage           = location.pathname.startsWith('/admin/visa-types');
  const isSubscriptionPricingPage = location.pathname.startsWith('/admin/subscription-pricing');
  const isAdminSubPage            = isSettingsPage || isVisaTypesPage || isSubscriptionPricingPage;
  const activeHash                = location.hash || '#general';

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // ── Reusable nav link renderer ─────────────────────────────────────────
  const renderNavLink = (to: string, src: string, label: string) => (
    <NavLink
      key={to}
      to={to}
      onClick={onClose}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 rounded-[12px] text-[14px] font-medium tracking-[-0.5px] transition-colors duration-150',
          collapsed
            ? 'lg:justify-center lg:px-0 lg:py-[10px] px-3 py-[10px]'
            : 'px-3 py-[10px]',
          isActive
            ? 'bg-[#f0f5ff] text-[#2f35ca]'
            : 'text-[#64748b] hover:bg-gray-50 hover:text-gray-900',
        ].join(' ')
      }
    >
      {({ isActive }) => (
        <>
          <img
            src={src}
            alt=""
            aria-hidden="true"
            className="shrink-0"
            style={{
              width: 20,
              height: 20,
              display: 'block',
              filter: isActive ? ACTIVE_FILTER : 'none',
            }}
          />
          <span
            className={[
              'whitespace-nowrap overflow-hidden transition-all duration-300',
              collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
            ].join(' ')}
          >
            {label}
          </span>
        </>
      )}
    </NavLink>
  );

  const renderSectionHeader = (text: string) => (
    <div
      className={[
        'mt-4 mb-1 px-3 transition-all duration-300 overflow-hidden',
        collapsed ? 'lg:opacity-0 lg:h-0' : 'opacity-100',
      ].join(' ')}
    >
      <p className="text-[11px] font-semibold text-[#94a3b8] tracking-[0.6px] uppercase">
        {text}
      </p>
    </div>
  );

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={[
          'fixed inset-y-0 left-0 z-30 bg-white border-r border-[#f1f5f9] flex flex-col',
          'transform transition-all duration-300 ease-in-out',
          'lg:static lg:translate-x-0 lg:z-auto',
          collapsed ? 'lg:w-16' : 'lg:w-[260px]',
          'w-[260px]',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        ].join(' ')}
      >

        {/* ── Logo ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 h-[72px] border-b border-[#f1f5f9] shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <div
              className="w-9 h-9 rounded-[10px] flex items-center justify-center shrink-0 shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1),0px_2px_4px_-2px_rgba(0,0,0,0.1)]"
              style={{ backgroundImage: 'linear-gradient(135deg, rgb(37,99,235) 0%, rgb(147,51,234) 100%)' }}>
              <img src={imgLogoIcon} alt="VisaFlow" className="w-[15px] h-[18px] object-contain" />
            </div>
            <span
              className={[
                'text-[20px] font-bold tracking-[-0.7px] leading-[28px] text-[#3a46e5] whitespace-nowrap transition-all duration-300 overflow-hidden',
                collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
              ].join(' ')}
            >
              VisaFlow
            </span>
          </div>

          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-lg hover:bg-gray-100 text-gray-500 shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Profile ──────────────────────────────────────────────────── */}
        <div className="px-6 py-6 border-b border-[#f1f5f9] shrink-0">
          <div className={['flex items-center gap-3', collapsed ? 'lg:justify-center' : ''].join(' ')}>

            <div className="relative shrink-0">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={fullName}
                  className="w-10 h-10 rounded-full object-cover ring-2 ring-white shadow-sm"
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = 'none';
                  }}
                />
              ) : (
                <Avatar name={fullName} size="lg" />
              )}
              <span className="absolute bottom-0.5 right-0.5 w-2.5 h-2.5 bg-green-400 border-2 border-white rounded-full" />
            </div>

            <div
              className={[
                'flex flex-col transition-all duration-300 overflow-hidden',
                collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
              ].join(' ')}
            >
              <p className="text-[18px] font-semibold text-[#0f172a] tracking-[-0.5px] whitespace-nowrap leading-[18px]">
                {fullName}
              </p>
              {roleLabel && (
                <p className="text-[12px] text-[#64748b] tracking-[-0.5px] whitespace-nowrap leading-[16px] mt-0.5">
                  {roleLabel}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── Nav ──────────────────────────────────────────────────────── */}
        <nav className="flex-1 px-4 py-6 flex flex-col gap-1 overflow-y-auto">

          {/* Employee nav (non-admin, non-lawyer users) */}
          {!isAdmin && !isLawyer && !isAdminSubPage &&
            employeeNavItems.map(({ to, src, label }) => renderNavLink(to, src, label))}

          {/* Admin Console (admin users only, hidden on admin sub-pages) */}
          {isAdmin && !isAdminSubPage && (
            <>
              {renderSectionHeader('Admin Console')}
              {adminNavItems.map(({ to, src, label }) => renderNavLink(to, src, label))}
            </>
          )}

          {/* Attorney Console (lawyer users only) */}
          {isLawyer && (
            <>
              {renderSectionHeader('Attorney Console')}
              {lawyerNavItems.map(({ to, src, label }) => renderNavLink(to, src, label))}
            </>
          )}

          {/* System Settings sub-sections — only on /admin/settings */}
          {isSettingsPage && (
            <>
              {renderSectionHeader('System Configuration')}
              {settingsNavItems.map(({ hash, src, label }) => {
                const active = activeHash === hash;
                return (
                  <NavLink
                    key={hash}
                    to={`/admin/settings${hash}`}
                    onClick={onClose}
                    title={collapsed ? label : undefined}
                    className={[
                      'flex items-center gap-3 rounded-[12px] text-[14px] font-medium tracking-[-0.5px] transition-colors duration-150',
                      collapsed
                        ? 'lg:justify-center lg:px-0 lg:py-[10px] px-3 py-[10px]'
                        : 'px-3 py-[10px]',
                      active
                        ? 'bg-[#f0f5ff] text-[#2f35ca]'
                        : 'text-[#64748b] hover:bg-gray-50 hover:text-gray-900',
                    ].join(' ')}
                  >
                    <img
                      src={src}
                      alt=""
                      aria-hidden="true"
                      className="shrink-0"
                      style={{
                        width: 20,
                        height: 20,
                        display: 'block',
                        filter: active ? ACTIVE_FILTER : 'none',
                      }}
                    />
                    <span
                      className={[
                        'whitespace-nowrap overflow-hidden transition-all duration-300',
                        collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
                      ].join(' ')}
                    >
                      {label}
                    </span>
                  </NavLink>
                );
              })}
            </>
          )}

          {/* Visa Types sub-section — display only, on /admin/visa-types */}
          {isVisaTypesPage && (
            <>
              {renderSectionHeader('Admin Console')}
              {visaTypesNavItems.map(({ src, label }) => (
                <div
                  key={label}
                  title={collapsed ? label : undefined}
                  className={[
                    'flex items-center gap-3 rounded-[12px] text-[14px] font-medium tracking-[-0.5px] cursor-pointer transition-colors duration-150',
                    collapsed
                      ? 'lg:justify-center lg:px-0 lg:py-[10px] px-3 py-[10px]'
                      : 'px-3 py-[10px]',
                    'bg-[#f0f5ff] text-[#2f35ca]',
                  ].join(' ')}
                >
                  <img
                    src={src}
                    alt=""
                    aria-hidden="true"
                    className="shrink-0"
                    style={{ width: 20, height: 20, display: 'block', filter: ACTIVE_FILTER }}
                  />
                  <span
                    className={[
                      'whitespace-nowrap overflow-hidden transition-all duration-300',
                      collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
                    ].join(' ')}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </>
          )}

          {/* Subscription & Pricing sub-section — display only */}
          {isSubscriptionPricingPage && (
            <>
              {renderSectionHeader('Admin Console')}
              {subscriptionNavItems.map(({ src, label }) => (
                <div
                  key={label}
                  title={collapsed ? label : undefined}
                  className={[
                    'flex items-center gap-3 rounded-[12px] text-[14px] font-medium tracking-[-0.5px] cursor-pointer transition-colors duration-150',
                    collapsed
                      ? 'lg:justify-center lg:px-0 lg:py-[10px] px-3 py-[10px]'
                      : 'px-3 py-[10px]',
                    'bg-[#f0f5ff] text-[#2f35ca]',
                  ].join(' ')}
                >
                  <img
                    src={src}
                    alt=""
                    aria-hidden="true"
                    className="shrink-0"
                    style={{ width: 20, height: 20, display: 'block', filter: ACTIVE_FILTER }}
                  />
                  <span
                    className={[
                      'whitespace-nowrap overflow-hidden transition-all duration-300',
                      collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
                    ].join(' ')}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </>
          )}
        </nav>

        {/* ── Sign out ─────────────────────────────────────────────────── */}
        <div className="px-4 py-4 border-t border-[#f1f5f9] shrink-0">
          <button
            onClick={handleLogout}
            title={collapsed ? 'Sign out' : undefined}
            className={[
              'flex items-center gap-2 w-full rounded-[12px] text-[14px] font-medium text-[#64748b] tracking-[-0.5px]',
              'hover:bg-red-50 hover:text-red-600 transition-colors duration-150',
              collapsed
                ? 'lg:justify-center lg:px-0 lg:py-[10px] px-3 py-[10px]'
                : 'px-3 py-[10px]',
            ].join(' ')}
          >
            <LogOut size={14} className="shrink-0" />
            <span
              className={[
                'whitespace-nowrap overflow-hidden transition-all duration-300',
                collapsed ? 'lg:w-0 lg:opacity-0' : 'lg:w-auto lg:opacity-100',
              ].join(' ')}
            >
              Sign out
            </span>
          </button>
        </div>

        {/* ── Desktop collapse toggle ───────────────────────────────────── */}
        <button
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={[
            'hidden lg:flex items-center justify-center',
            'absolute -right-3 top-[72px]',
            'w-6 h-6 bg-white border border-gray-200 rounded-full shadow-sm',
            'hover:bg-indigo-50 hover:border-indigo-300 transition-colors duration-150 z-10',
          ].join(' ')}
        >
          <ChevronLeft
            size={12}
            className={[
              'text-gray-500 transition-transform duration-300',
              collapsed ? 'rotate-180' : 'rotate-0',
            ].join(' ')}
          />
        </button>

      </aside>
    </>
  );
}
