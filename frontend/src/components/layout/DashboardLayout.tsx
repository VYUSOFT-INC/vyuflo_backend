// src/components/layout/DashboardLayout.tsx
import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { SettingsSidebar } from './SettingsSidebar';

function VisaFlowLogo({ size = 18 }: { size?: number }) {
  return (
    <svg width={size * (21 / 24)} height={size} viewBox="0 0 21 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <g clipPath="url(#vf-dash-clip)">
        <path d="M0 3C0 1.34531 1.34531 0 3 0H18C19.6547 0 21 1.34531 21 3V21C21 22.6547 19.6547 24 18 24H3C1.34531 24 0 22.6547 0 21V3ZM8.57812 13.0687C7.27031 12.45 6.30938 11.2219 6.06094 9.75H7.89375C7.96875 11.175 8.25469 12.2719 8.57812 13.0687ZM10.5141 13.5H10.5H10.4859C10.3734 13.3359 10.2188 13.0828 10.0594 12.7266C9.77813 12.0891 9.47812 11.1188 9.39375 9.75H11.6016C11.5172 11.1188 11.2219 12.0891 10.9359 12.7266C10.7766 13.0828 10.6219 13.3359 10.5094 13.5H10.5141ZM12.4219 13.0687C12.7406 12.2672 13.0266 11.175 13.1063 9.75H14.9391C14.6906 11.2219 13.7297 12.45 12.4219 13.0687ZM13.1063 8.25C13.0313 6.825 12.7453 5.72812 12.4219 4.93125C13.7297 5.55 14.6906 6.77813 14.9391 8.25H13.1063ZM10.4859 4.5H10.5H10.5141C10.6266 4.66406 10.7812 4.91719 10.9406 5.27344C11.2219 5.91094 11.5219 6.88125 11.6063 8.25H9.39844C9.48281 6.88125 9.77812 5.91094 10.0641 5.27344C10.2234 4.91719 10.3781 4.66406 10.4906 4.5H10.4859ZM8.57812 4.93125C8.25937 5.73281 7.97344 6.825 7.89375 8.25H6.06094C6.30938 6.77813 7.27031 5.55 8.57812 4.93125ZM16.5 9C16.5 7.4087 15.8679 5.88258 14.7426 4.75736C13.6174 3.63214 12.0913 3 10.5 3C8.9087 3 7.38258 3.63214 6.25736 4.75736C5.13214 5.88258 4.5 7.4087 4.5 9C4.5 10.5913 5.13214 12.1174 6.25736 13.2426C7.38258 14.3679 8.9087 15 10.5 15C12.0913 15 13.6174 14.3679 14.7426 13.2426C15.8679 12.1174 16.5 10.5913 16.5 9ZM5.25 18C4.8375 18 4.5 18.3375 4.5 18.75C4.5 19.1625 4.8375 19.5 5.25 19.5H15.75C16.1625 19.5 16.5 19.1625 16.5 18.75C16.5 18.3375 16.1625 18 15.75 18H5.25Z" fill="white"/>
      </g>
      <defs>
        <clipPath id="vf-dash-clip"><path d="M0 0H21V24H0V0Z" fill="white"/></clipPath>
      </defs>
    </svg>
  );
}

function HamburgerButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} aria-label="Open menu"
      className="flex flex-col justify-center gap-[5px] w-[36px] h-[36px]
                 rounded-[10px] border border-[#e2e8f0] bg-white items-center
                 hover:bg-[#f8fafc] transition-colors shrink-0">
      <span className="w-[16px] h-[1.5px] bg-[#64748b] rounded-full" />
      <span className="w-[16px] h-[1.5px] bg-[#64748b] rounded-full" />
      <span className="w-[12px] h-[1.5px] bg-[#64748b] rounded-full self-start ml-[10px]" />
    </button>
  );
}

function LogoMark() {
  return (
    <div className="flex items-center gap-[8px]">
      <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center shrink-0
                      shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1),0px_2px_4px_-2px_rgba(0,0,0,0.1)]"
        style={{ backgroundImage: 'linear-gradient(135deg, rgb(79,70,229) 0%, rgb(124,58,237) 100%)' }}>
        <VisaFlowLogo size={17} />
      </div>
      <span className="text-[18px] font-bold tracking-[-0.7px] text-[#4f46e5]">VisaFlow</span>
    </div>
  );
}

function MobileTopBar({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <div className="lg:hidden flex items-center gap-[12px] px-[16px] h-[56px]
                    bg-white border-b border-[#f1f5f9] shrink-0 sticky top-0 z-20">
      <HamburgerButton onClick={onMenuClick} />
      <LogoMark />
    </div>
  );
}

// ── Mobile settings drawer with backdrop ──────────────────────────────────────
function SettingsDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} />
      )}
      <div className={[
        'fixed top-0 left-0 h-full z-40 lg:hidden',
        'transition-transform duration-300 ease-in-out',
        open ? 'translate-x-0' : '-translate-x-full',
      ].join(' ')}>
        <SettingsSidebar onClose={onClose} />
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
export function DashboardLayout() {
  const [sidebarOpen,  setSidebarOpen]  = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [collapsed,    setCollapsed]    = useState(false);
  const location = useLocation();

  const isSettingsPage = location.pathname.startsWith('/profile') ||
                         location.pathname.startsWith('/settings');

  const isNoSidebarPage = /^\/applications\/[^/]+\/documents/.test(location.pathname) ||
                          /^\/applications\/[^/]+\/review/.test(location.pathname);

  // Admin pages need a scrollable outlet wrapper
  const isAdminPage = location.pathname.startsWith('/admin');

  return (
    <div className="flex h-screen bg-[#f7f9fc] overflow-hidden">

      {/* ── Desktop sidebars ── */}
      {isNoSidebarPage ? null : isSettingsPage ? (
        <div className="hidden lg:block">
          <SettingsSidebar />
        </div>
      ) : (
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(c => !c)}
        />
      )}

      {/* ── Mobile settings drawer ── */}
      {isSettingsPage && !isNoSidebarPage && (
        <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      )}

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* ── Mobile top bar — shown on all pages except isNoSidebarPage ── */}
        {!isNoSidebarPage && (
          <MobileTopBar
            onMenuClick={() => {
              if (isSettingsPage) setSettingsOpen(true);
              else setSidebarOpen(true);
            }}
          />
        )}

        {/* ⬇️ Admin pages → scrollable wrapper. Employee pages → unchanged. */}
        {isAdminPage ? (
          <div className="flex-1 overflow-y-auto">
            <Outlet />
          </div>
        ) : (
          <Outlet />
        )}
      </div>
    </div>
  );
}