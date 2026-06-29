// src/components/layout/SettingsSidebar.tsx
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { Avatar } from '../ui/Avatar';
import { getUiSession, type UiSession } from '../../utils/uiSession';
import { getFileUrl } from '../../utils/fileUrl';
import {
  ChevronLeft, X,
  User, Settings, Bell, Shield, CreditCard,
  Users, Plug, Activity, Download, HelpCircle, LogOut,
} from 'lucide-react';

interface NavItem {
  id:    string;
  label: string;
  icon:  React.ReactNode;
  path:  string;
}

const PERSONAL: NavItem[] = [
  { id: 'profile',  label: 'Profile',           icon: <User      size={16} />, path: '/profile'                },
  { id: 'prefs',    label: 'Authentication',     icon: <Settings  size={16} />, path: '/profile/authentication' },
  { id: 'notifs',   label: 'Multi-Factor Auth',  icon: <Bell      size={16} />, path: '/profile/mfa'            },
  { id: 'security', label: 'Security & Privacy', icon: <Shield    size={16} />, path: '/profile/security-alerts'},
];
const ACCOUNT: NavItem[] = [
  { id: 'billing',      label: 'Billing',      icon: <CreditCard size={16} />, path: '/profile/billing'      },
  { id: 'team',         label: 'Team Members', icon: <Users      size={16} />, path: '/profile/team'         },
  { id: 'integrations', label: 'Integrations', icon: <Plug       size={16} />, path: '/profile/integrations' },
];
const SYSTEM: NavItem[] = [
  { id: 'activity', label: 'Login History',    icon: <Activity   size={16} />, path: '/profile/login-history' },
  { id: 'export',   label: 'Privacy Settings', icon: <Download   size={16} />, path: '/profile/privacy'       },
  { id: 'help',     label: 'Devices',          icon: <HelpCircle size={16} />, path: '/profile/devices'       },
];

// ── Props — onClose is optional, only passed by the mobile drawer ─────────────
interface SettingsSidebarProps {
  onClose?: () => void;
}

export function SettingsSidebar({ onClose }: SettingsSidebarProps = {}) {
  const navigate = useNavigate();
  const location = useLocation();
  const { clearAuth: logout } = useAuthStore();

  const [session, setSession] = useState<UiSession | null>(null);

  useEffect(() => {
    setSession(getUiSession());
    const handler = () => setSession(getUiSession());
    window.addEventListener('ui-session-updated', handler);
    return () => window.removeEventListener('ui-session-updated', handler);
  }, []);

  const fullName  = session ? `${session.first_name} ${session.last_name}`.trim() : 'User';
  const avatarUrl = getFileUrl(session?.profile ?? null);

  const handleLogout = () => { logout(); navigate('/login'); };
  const isActive = (path: string) => location.pathname === path;

  // Navigate and optionally close the mobile drawer
  const go = (path: string) => { navigate(path); onClose?.(); };

  const renderGroup = (label: string, items: NavItem[]) => (
    <div className="mb-[8px]">
      <p className="text-[11px] font-semibold text-[#9ca3af] uppercase tracking-[0.08em] px-[12px] mb-[4px] leading-[16px]">
        {label}
      </p>
      {items.map(item => (
        <button key={item.id} onClick={() => go(item.path)}
          className={[
            'w-full flex items-center gap-[10px] px-[12px] py-[10px] rounded-[8px]',
            'text-[14px] font-medium tracking-[-0.5px] leading-[20px]',
            'transition-colors duration-150 mb-[2px]',
            isActive(item.path)
              ? 'bg-[#f0f5ff] text-[#2f35ca]'
              : 'text-[#64748b] hover:bg-[#f8fafc] hover:text-[#0f172a]',
          ].join(' ')}>
          <span className={isActive(item.path) ? 'text-[#2f35ca]' : 'text-[#94a3b8]'}>
            {item.icon}
          </span>
          {item.label}
        </button>
      ))}
    </div>
  );

  return (
    <aside className="w-[280px] sm:w-[288px] shrink-0 bg-white border-r border-[#f1f5f9]
                      flex flex-col h-screen overflow-y-auto">

      <div className="px-[24px] pt-[24px] pb-[16px] shrink-0">

        <div className="flex items-center justify-between mb-[16px]">
          <button onClick={() => go('/dashboard')}
            className="flex items-center gap-[8px] text-[#64748b] text-[13px] font-medium
                       tracking-[-0.5px] hover:text-[#0f172a] transition-colors">
            <ChevronLeft size={14} className="shrink-0" />
            Back to Dashboard
          </button>

          {/* X button — only visible inside the mobile drawer */}
          {onClose && (
            <button onClick={onClose} aria-label="Close menu"
              className="p-[6px] rounded-[8px] text-[#64748b] hover:text-[#0f172a]
                         hover:bg-[#f1f5f9] transition-colors">
              <X size={16} />
            </button>
          )}
        </div>

        <h2 className="text-[22px] sm:text-[24px] font-bold text-[#0f172a] tracking-[-0.5px] leading-[32px]">
          Settings
        </h2>

        <div className="flex items-center gap-[12px] mt-[16px] p-[12px] bg-[#f8fafc] rounded-[12px] border border-[#f1f5f9]">
          <div className="relative shrink-0">
            {avatarUrl ? (
              <img src={avatarUrl} alt={fullName}
                className="w-8 h-8 rounded-full object-cover ring-2 ring-white shadow-sm"
                onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
            ) : (
              <Avatar name={fullName} size="sm" />
            )}
          </div>
          <div className="flex flex-col min-w-0">
            <p className="text-[14px] font-semibold text-[#0f172a] tracking-[-0.5px] leading-[18px] truncate">
              {fullName}
            </p>
          </div>
        </div>
      </div>

      <div className="h-px bg-[#f1f5f9] mx-[24px] shrink-0" />

      <nav className="flex-1 px-[12px] pt-[16px] pb-[8px] overflow-y-auto">
        {renderGroup('Personal Settings', PERSONAL)}
        {renderGroup('Account', ACCOUNT)}
        {renderGroup('System', SYSTEM)}
      </nav>

      <div className="border-t border-[#f1f5f9] px-[12px] py-[12px] shrink-0">
        <button onClick={handleLogout}
          className="flex items-center gap-[8px] w-full px-[12px] py-[10px] rounded-[8px]
                     text-[14px] font-medium text-[#64748b] tracking-[-0.5px]
                     hover:bg-red-50 hover:text-red-600 transition-colors duration-150">
          <LogOut size={14} className="shrink-0" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}