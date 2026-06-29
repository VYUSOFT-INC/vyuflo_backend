// src/components/layout/PageHeader.tsx
import { useNavigate } from 'react-router-dom';
import { Search, Bell } from 'lucide-react';
import { useState } from 'react';

interface PageHeaderProps {
  title:              string;
  subtitle?:          string;
  actions?:           React.ReactNode;
  showSearch?:        boolean;
  searchValue?:       string;
  searchPlaceholder?: string;
  onSearchChange?:    (value: string) => void;
  showBell?:          boolean;
  bellDot?:           boolean;
}

export function PageHeader({
  title,
  subtitle,
  actions,
  showSearch        = false,
  searchValue       = '',
  searchPlaceholder = 'Search...',
  onSearchChange,
  showBell          = true,
  bellDot           = true,
}: PageHeaderProps) {
  const navigate = useNavigate();
  const [localSearch, setLocalSearch] = useState('');

  const searchVal   = onSearchChange ? searchValue : localSearch;
  const handleSearch = (v: string) => {
    if (onSearchChange) onSearchChange(v);
    else setLocalSearch(v);
  };

  return (
    <header className={[
      'bg-[rgba(255,255,255,0.9)] border-b border-[#f1f5f9] backdrop-blur-sm',
      'shrink-0 sticky top-0 z-10',
      // On mobile DashboardLayout already shows a top bar — so PageHeader
      // sits BELOW it. On desktop (lg+) DashboardLayout bar is hidden.
      'flex flex-wrap items-center gap-[12px]',
      'min-h-[56px] lg:min-h-[72px]',
      'px-[16px] sm:px-[24px] lg:px-[32px]',
      'py-[10px] lg:py-[0px]',
    ].join(' ')}>

      {/* ── Left: title + subtitle ── */}
      <div className="flex flex-col gap-[2px] flex-1 min-w-0">
        <p className="font-bold text-[#0f172a] text-[16px] sm:text-[18px] lg:text-[20px]
                      leading-[22px] lg:leading-[28px] tracking-[-0.5px] truncate">
          {title}
        </p>
        {subtitle && (
          <p className="font-normal text-[#64748b] text-[11px] sm:text-[12px]
                        leading-[16px] tracking-[-0.5px] truncate">
            {subtitle}
          </p>
        )}
      </div>

      {/* ── Right: search + bell + actions ── */}
      <div className="flex items-center gap-[8px] sm:gap-[12px] lg:gap-[16px] flex-shrink-0">

        {/* Search — hidden on mobile */}
        {showSearch && (
          <div className="relative h-[34px] sm:h-[38px] hidden sm:block
                          w-[160px] md:w-[200px] lg:w-[256px]">
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchVal}
              onChange={e => handleSearch(e.target.value)}
              className="bg-[#f8fafc] border border-[#e2e8f0] font-normal h-full
                         pl-[30px] sm:pl-[36px] pr-[12px] rounded-[10px] sm:rounded-[12px]
                         text-[#1e293b] text-[13px] sm:text-[14px] tracking-[-0.5px] w-full
                         focus:outline-none focus:ring-2 focus:ring-[#5269f2]
                         focus:border-transparent placeholder:text-[#94a3b8] transition-colors"
            />
            <Search
              size={13}
              className="absolute left-[10px] sm:left-[12px] top-1/2 -translate-y-1/2
                         text-[#94a3b8] pointer-events-none"
            />
          </div>
        )}

        {/* Bell */}
        {showBell && (
          <button
            type="button"
            onClick={() => navigate('/notifications')}
            aria-label="Notifications"
            className="bg-white border border-[#e2e8f0] drop-shadow-[0px_1px_1px_rgba(0,0,0,0.05)]
                       flex items-center justify-center relative rounded-[10px] sm:rounded-[12px]
                       size-[34px] sm:size-[38px] lg:size-[40px]
                       hover:bg-[#f8fafc] transition-colors shrink-0"
          >
            <Bell size={14} className="text-[#64748b]" />
            {bellDot && (
              <span className="absolute bg-[#5269f2] border border-white
                               h-[6px] w-[6px] sm:h-[8px] sm:w-[8px]
                               rounded-full top-[6px] right-[7px]
                               sm:top-[8px] sm:right-[9px]" />
            )}
          </button>
        )}

        {/* Actions slot */}
        {actions}
      </div>

    </header>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PageContent
// ─────────────────────────────────────────────────────────────────────────────

interface PageContentProps {
  children:     React.ReactNode;
  noPadding?:   boolean;
  extraBottom?: number;
  className?:   string;
}

export function PageContent({
  children,
  noPadding   = false,
  extraBottom = 0,
  className   = '',
}: PageContentProps) {
  return (
    <main
      className={[
        'flex-1 overflow-y-auto',
        noPadding
          ? ''
          : 'px-[16px] sm:px-[24px] lg:px-[32px] pt-[16px] sm:pt-[24px] lg:pt-[32px]',
        className,
      ].join(' ')}
      style={{ paddingBottom: `${Math.max(48, extraBottom)}px` }}
    >
      {children}
    </main>
  );
}