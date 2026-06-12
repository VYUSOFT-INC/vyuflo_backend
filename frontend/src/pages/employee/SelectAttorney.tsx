// src/pages/employee/SelectAttorney.tsx

import { useNavigate } from "react-router-dom";
import { useAttorneys, useAttorneyFilters } from "../../hooks/employee/useSelectAttorney";
import { formatFee, getAvatarColor } from "../../types/employee/selectAttorney.types";
import type { AttorneyProfile, AttorneyFilters } from "../../types/employee/selectAttorney.types";

const BADGE_STYLES: Record<string, string> = {
  "Top Rated":    "bg-[#FEF3C7] text-[#92400E]",
  "Verified":     "bg-[#D1FAE5] text-[#065F46]",
  "Fast Response":"bg-[#DBEAFE] text-[#1E40AF]",
};

const VISA_TYPE_OPTIONS   = ["H-1B","L-1","O-1","EB-1","EB-2","EB-3","EB-5","K-1","Asylum"];
const LANGUAGE_OPTIONS    = ["English","Spanish","Mandarin","Korean","French","Portuguese"];
const AVAILABILITY_OPTIONS = ["All","Available Now","Within 24h","Within 48h"] as const;

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M6 1l1.39 2.82L10.5 4.27l-2.25 2.19.53 3.09L6 8.02l-2.78 1.53.53-3.09L1.5 4.27l3.11-.45L6 1z"
        fill={filled ? "#FBBF24" : "#E5E7EB"} />
    </svg>
  );
}

function RatingStars({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-[2px]">
      {[1,2,3,4,5].map(i => <StarIcon key={i} filled={i <= Math.round(rating)} />)}
    </div>
  );
}

function AttorneyCard({ attorney, onSelect }: { attorney: AttorneyProfile; onSelect: (id: string) => void }) {
  const firstName   = attorney.user?.first_name ?? "";
  const lastName    = attorney.user?.last_name  ?? "";
  const initials    = `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || "?";
  const avatarColor = getAvatarColor(attorney.id);
  const badges      = attorney.badges ?? [];

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-[20px] flex flex-col gap-[16px] hover:shadow-[0_4px_16px_rgba(0,0,0,0.08)] transition-shadow duration-200">
      <div className="flex items-start gap-[16px]">
        {attorney.profile_photo_url ? (
          <img src={attorney.profile_photo_url} alt={firstName}
            className="w-[64px] h-[64px] rounded-full object-cover flex-shrink-0" />
        ) : (
          <div className="w-[64px] h-[64px] rounded-full flex items-center justify-center flex-shrink-0 text-white text-[18px] font-semibold"
            style={{ backgroundColor: avatarColor }}>
            {initials}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-[8px]">
            <div>
              <h3 className="text-[15px] font-semibold text-[#111827] leading-tight">
                {firstName} {lastName}, Esq.
              </h3>
              <p className="text-[12px] text-[#6B7280] mt-[2px]">
                {attorney.visa_types_list[0] ?? attorney.law_firm_name ?? "Immigration Attorney"}
              </p>
            </div>
            <div className="flex-shrink-0 text-right">
              <p className="text-[10px] text-[#9CA3AF] uppercase tracking-wide">Fee/hr</p>
              <p className="text-[18px] font-bold text-[#111827] leading-tight">
                {formatFee(attorney.consultation_fee_cents)}
              </p>
            </div>
          </div>
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-[6px] mt-[8px]">
              {badges.map(badge => (
                <span key={badge}
                  className={`text-[10px] font-medium px-[8px] py-[3px] rounded-full ${BADGE_STYLES[badge] ?? "bg-[#F3F4F6] text-[#374151]"}`}>
                  {badge}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-[8px] bg-[#F9FAFB] rounded-[8px] p-[12px]">
        <div className="text-center">
          <p className="text-[13px] font-semibold text-[#111827]">{attorney.success_rate}%</p>
          <p className="text-[10px] text-[#9CA3AF] mt-[1px]">Success Rate</p>
        </div>
        <div className="text-center border-x border-[#E5E7EB]">
          <p className="text-[13px] font-semibold text-[#111827]">{attorney.years_experience ?? "—"} Yrs</p>
          <p className="text-[10px] text-[#9CA3AF] mt-[1px]">Experience</p>
        </div>
        <div className="text-center">
          <p className="text-[13px] font-semibold text-[#111827]">
            {attorney.total_cases >= 1000 ? `${(attorney.total_cases/1000).toFixed(1)}k+` : `${attorney.total_cases}+`}
          </p>
          <p className="text-[10px] text-[#9CA3AF] mt-[1px]">Cases</p>
        </div>
      </div>

      <div className="flex flex-col gap-[6px]">
        <div className="flex items-center gap-[6px]">
          <RatingStars rating={attorney.rating} />
          <span className="text-[12px] font-semibold text-[#111827]">{attorney.rating.toFixed(1)}</span>
          <span className="text-[12px] text-[#6B7280]">({attorney.review_count} reviews)</span>
        </div>
        {attorney.location_display && (
          <div className="flex items-center gap-[6px]">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <path d="M8 1.5C5.515 1.5 3.5 3.515 3.5 6c0 3.75 4.5 8.5 4.5 8.5S12.5 9.75 12.5 6c0-2.485-2.015-4.5-4.5-4.5zm0 6.1a1.6 1.6 0 110-3.2 1.6 1.6 0 010 3.2z" fill="#9CA3AF"/>
            </svg>
            <span className="text-[12px] text-[#6B7280]">{attorney.location_display}</span>
          </div>
        )}
        {attorney.languages_list.length > 0 && (
          <div className="flex items-center gap-[6px]">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="#9CA3AF" strokeWidth="1.5"/>
              <path d="M8 2c0 0-2 3-2 6s2 6 2 6M8 2c0 0 2 3 2 6s-2 6-2 6M2 8h12" stroke="#9CA3AF" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
            <span className="text-[12px] text-[#6B7280]">{attorney.languages_list.join(", ")}</span>
          </div>
        )}
        {attorney.visa_types_list.length > 0 && (
          <div className="flex flex-wrap gap-[4px] mt-[2px]">
            {attorney.visa_types_list.map(vt => (
              <span key={vt} className="text-[10px] bg-[#EEF2FF] text-[#4338CA] px-[7px] py-[2px] rounded-[4px] font-medium">
                {vt}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-[10px] pt-[4px] border-t border-[#F3F4F6]">
        <button type="button"
          className="flex-1 text-[13px] font-medium text-[#4F46E5] border border-[#4F46E5] rounded-[8px] py-[8px] hover:bg-[#EEF2FF] transition-colors">
          View Details
        </button>
        <button type="button" onClick={() => onSelect(attorney.id)} disabled={!attorney.is_available}
          className="flex-1 text-[13px] font-semibold text-white bg-[#4F46E5] rounded-[8px] py-[8px] hover:bg-[#4338CA] transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          {attorney.is_available ? "Send Consultation" : "Unavailable"}
        </button>
      </div>
    </div>
  );
}

function FilterSidebar({ filters, onChange, onReset }: {
  filters: AttorneyFilters;
  onChange: (f: Partial<AttorneyFilters>) => void;
  onReset: () => void;
}) {
  const toggle = (arr: string[], val: string) =>
    arr.includes(val) ? arr.filter(x => x !== val) : [...arr, val];

  const sectionCls = "bg-white border border-[#E5E7EB] rounded-[12px] p-[16px] flex flex-col gap-[8px]";
  const titleCls   = "text-[11px] font-semibold text-[#6B7280] uppercase tracking-wider mb-[4px]";
  const labelCls   = "flex items-center gap-[8px] cursor-pointer group";
  const checkboxCls = "w-[14px] h-[14px] rounded-[3px] border-[1.5px] border-[#D1D5DB] accent-[#4F46E5] cursor-pointer flex-shrink-0";

  return (
    <aside className="w-[232px] flex flex-col gap-[12px]">

      {/* Search */}
      <div className={sectionCls}>
        <p className={titleCls}>Search & Filters</p>
        <div className="flex flex-col gap-[4px]">
          <label className="text-[11px] font-medium text-[#6B7280]">ZIP Code</label>
          <input type="text" maxLength={5} value={filters.zipCode}
            onChange={e => onChange({ zipCode: e.target.value })}
            placeholder="e.g. 90001"
            className="border border-[#E5E7EB] rounded-[8px] px-[10px] py-[7px] text-[13px] text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#4F46E5] focus:border-transparent" />
        </div>
        <div className="flex flex-col gap-[4px] mt-[4px]">
          <label className="text-[11px] font-medium text-[#6B7280]">
            Radius: <span className="text-[#111827] font-semibold">{filters.radius} miles</span>
          </label>
          <input type="range" min={5} max={100} step={5} value={filters.radius}
            onChange={e => onChange({ radius: Number(e.target.value) })}
            className="w-full accent-[#4F46E5] h-[4px] cursor-pointer" />
          <div className="flex justify-between text-[10px] text-[#9CA3AF]">
            <span>5 mi</span><span>100 mi</span>
          </div>
        </div>
      </div>

      {/* Visa Type */}
      <div className={sectionCls}>
        <p className={titleCls}>Visa Type</p>
        {VISA_TYPE_OPTIONS.map(v => (
          <label key={v} className={labelCls}>
            <input type="checkbox" checked={filters.visaTypes.includes(v)}
              onChange={() => onChange({ visaTypes: toggle(filters.visaTypes, v) })}
              className={checkboxCls} />
            <span className="text-[12px] text-[#374151] group-hover:text-[#111827]">{v}</span>
          </label>
        ))}
      </div>

      {/* Language */}
      <div className={sectionCls}>
        <p className={titleCls}>Language</p>
        {LANGUAGE_OPTIONS.map(l => (
          <label key={l} className={labelCls}>
            <input type="checkbox" checked={filters.languages.includes(l)}
              onChange={() => onChange({ languages: toggle(filters.languages, l) })}
              className={checkboxCls} />
            <span className="text-[12px] text-[#374151] group-hover:text-[#111827]">{l}</span>
          </label>
        ))}
      </div>

      {/* Min Rating */}
      <div className={sectionCls}>
        <p className={titleCls}>Minimum Rating</p>
        {[4.5, 4.0, 3.5, 0].map(r => (
          <label key={r} className={labelCls}>
            <input type="radio" name="minRating" checked={filters.minRating === r}
              onChange={() => onChange({ minRating: r })}
              className="w-[14px] h-[14px] accent-[#4F46E5] cursor-pointer flex-shrink-0" />
            <span className="text-[12px] text-[#374151] group-hover:text-[#111827]">
              {r === 0 ? "Any" : `${r}+ Stars`}
            </span>
          </label>
        ))}
      </div>

      {/* Availability */}
      <div className={sectionCls}>
        <p className={titleCls}>Availability</p>
        {AVAILABILITY_OPTIONS.map(a => (
          <label key={a} className={labelCls}>
            <input type="radio" name="availability" checked={filters.availability === a}
              onChange={() => onChange({ availability: a })}
              className="w-[14px] h-[14px] accent-[#4F46E5] cursor-pointer flex-shrink-0" />
            <span className="text-[12px] text-[#374151] group-hover:text-[#111827]">{a}</span>
          </label>
        ))}
      </div>

      {/* Price Range */}
      <div className={sectionCls}>
        <p className={titleCls}>Price Range</p>
        <div className="flex items-center gap-[6px]">
          <input type="number" placeholder="Min"
            className="w-full border border-[#E5E7EB] rounded-[6px] px-[8px] py-[6px] text-[12px] text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]" />
          <span className="text-[11px] text-[#9CA3AF] flex-shrink-0">—</span>
          <input type="number" placeholder="Max"
            value={filters.maxFeeDollars ?? ""}
            onChange={e => onChange({ maxFeeDollars: e.target.value ? Number(e.target.value) : null })}
            className="w-full border border-[#E5E7EB] rounded-[6px] px-[8px] py-[6px] text-[12px] text-[#111827] placeholder-[#9CA3AF] focus:outline-none focus:ring-1 focus:ring-[#4F46E5]" />
        </div>
        <button type="button" onClick={onReset}
          className="text-[12px] text-[#4F46E5] font-medium hover:text-[#4338CA] hover:underline text-left mt-[4px] transition-colors">
          Reset All Filters
        </button>
      </div>
    </aside>
  );
}

export default function SelectAttorney() {
  const navigate = useNavigate();
  const { filters, updateFilters, resetFilters } = useAttorneyFilters();
  const { attorneys = [], loading, error, total = 0 } = useAttorneys(filters);

  const handleSelect = (id: string) => navigate(`/consultations/book/${id}`);

  return (
    <div className="flex flex-col gap-[24px] px-[24px] sm:px-[32px] pt-[12px] pb-[48px]">

      {/* ── Page heading ── */}
      <div>
        <h1 className="text-[24px] font-bold text-[#111827]">Find Your Immigration Attorney</h1>
        <p className="text-[14px] text-[#6B7280] mt-[4px]">
          Search by ZIP code to find qualified immigration attorneys near you
        </p>
      </div>

      {/* ── Body: sidebar + list ── */}
      <div className="flex gap-[24px] items-start">

        {/* Filter sidebar — sticky, scrolls independently, no visible scrollbar divider */}
        <div className="hidden lg:block flex-shrink-0 sticky top-[12px] self-start
                        max-h-[calc(100vh-100px)] overflow-y-auto
                        scrollbar-thin pr-[4px]">
          <FilterSidebar filters={filters} onChange={updateFilters} onReset={resetFilters} />
        </div>

        {/* Attorney list */}
        <div className="flex-1 flex flex-col gap-[20px] min-w-0">

          {/* Toolbar */}
          <div className="flex items-center justify-between flex-wrap gap-[12px]">
            <div>
              <p className="text-[14px] font-semibold text-[#111827]">
                {total} Attorney{total !== 1 ? "s" : ""} Found
              </p>
              {filters.zipCode && (
                <p className="text-[12px] text-[#6B7280] mt-[2px]">
                  Near ZIP {filters.zipCode} within {filters.radius} miles
                </p>
              )}
            </div>
            <div className="flex items-center gap-[8px]">
              <span className="text-[12px] text-[#6B7280]">Sort by:</span>
              <select value={filters.sortBy}
                onChange={e => updateFilters({ sortBy: e.target.value as AttorneyFilters["sortBy"] })}
                className="border border-[#E5E7EB] rounded-[8px] px-[10px] py-[6px] text-[12px] text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#4F46E5] bg-white">
                <option value="rating">Highest Rated</option>
                <option value="fee_asc">Lowest Fee</option>
                <option value="fee_desc">Highest Fee</option>
                <option value="experience">Most Experience</option>
              </select>
            </div>
          </div>

          {/* Mobile quick-filter chips */}
          <div className="flex lg:hidden gap-[8px] overflow-x-auto pb-[4px]">
            {["H-1B","L-1","O-1","EB-2","Available Now","Top Rated"].map(tag => (
              <button key={tag} type="button"
                className="flex-shrink-0 text-[11px] border border-[#E5E7EB] rounded-full px-[12px] py-[6px] text-[#374151] hover:border-[#4F46E5] hover:text-[#4F46E5] transition-colors">
                {tag}
              </button>
            ))}
          </div>

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-[64px]">
              <div className="w-[32px] h-[32px] border-2 border-[#E5E7EB] border-t-[#4F46E5] rounded-full animate-spin" />
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="flex items-center justify-center py-[64px]">
              <p className="text-[14px] text-[#DC2626]">{error}</p>
            </div>
          )}

          {/* Empty */}
          {!loading && !error && attorneys.length === 0 && (
            <div className="flex items-center justify-center py-[64px]">
              <div className="text-center">
                <div className="w-[48px] h-[48px] bg-[#F3F4F6] rounded-full flex items-center justify-center mx-auto mb-[16px]">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M10 17a7 7 0 100-14 7 7 0 000 14zm7-1l4 4" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <p className="text-[15px] font-medium text-[#374151]">No attorneys found</p>
                <p className="text-[13px] text-[#9CA3AF] mt-[4px]">Try adjusting your filters or expanding the radius</p>
              </div>
            </div>
          )}

          {/* Cards grid */}
          {!loading && !error && attorneys.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-[16px]">
              {attorneys.map(attorney => (
                <AttorneyCard key={attorney.id} attorney={attorney} onSelect={handleSelect} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}