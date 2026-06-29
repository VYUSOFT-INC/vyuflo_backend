// src/types/selectAttorney.types.ts

// =============================================================================
// Raw backend shapes (exact field names from attorney_schemas.py)
// =============================================================================

export interface AttorneyUserBrief {
  id:         string;
  first_name: string;
  last_name:  string;
  email:      string;
  phone:      string | null;
}

/**
 * Raw shape returned by:
 *   GET  /api/v1/attorneys       → AttorneyListResponse.attorneys[]
 *   GET  /api/v1/attorneys/:id   → AttorneyListItem
 *
 * Computed fields (rating, success_rate, etc.) are injected by the
 * backend service layer (attorney_service.py) — they are always present.
 */
export interface AttorneyProfile {
  // ── DB columns ─────────────────────────────────────────────────────────────
  id:                 string;
  user_id:            string;
  bar_number:         string | null;
  bar_state:          string | null;
  years_experience:   number | null;
  law_firm_name:      string | null;
  specialisations:    string | null;   // JSON-encoded: '["H-1B","O-1","EB-2"]'
  languages:          string | null;   // JSON-encoded: '["English","Spanish"]'
  availability_note:  string | null;
  max_active_cases:   number | null;
  bio:                string | null;
  profile_photo_url:  string | null;
  is_accepting_cases: boolean;
  is_verified:        boolean;
  is_active:          boolean;
  created_at:         string;
  updated_at:         string;
  user:               AttorneyUserBrief | null;

  // ── Computed by backend service (attorney_service.py → enrich_attorney) ───
  rating:                 number;    // 0.0–5.0
  review_count:           number;
  success_rate:           number;    // 0–100
  total_cases:            number;
  consultation_fee_cents: number;    // US cents, cheapest appt type
  is_available:           boolean;   // has unbooked slot in next 7 days
  distance_miles:         number | null;
  badges:                 AttorneyBadge[];
  location_display:       string;    // "Los Angeles, CA · 2.3 miles away"
  languages_list:         string[];  // parsed from JSON
  visa_types_list:        string[];  // parsed from JSON (specialisations)
}

/** Paginated wrapper — returned by GET /api/v1/attorneys */
export interface AttorneyListResponse {
  attorneys:  AttorneyProfile[];
  total:      number;
  page:       number;
  page_size:  number;
}

// =============================================================================
// UI types
// =============================================================================

export type AttorneyBadge = "Top Rated" | "Verified" | "Fast Response";

export type AttorneySortBy =
  | "rating"
  | "fee_asc"
  | "fee_desc"
  | "experience";

export type AttorneyAvailability =
  | "All"
  | "Available Now"
  | "Within 24h"
  | "Within 48h";

export interface AttorneyFilters {
  zipCode:       string;
  radius:        number;
  visaTypes:     string[];
  languages:     string[];
  minRating:     number;
  maxFeeDollars: number | null;
  availability:  AttorneyAvailability;
  sortBy:        AttorneySortBy;
}

export const DEFAULT_FILTERS: AttorneyFilters = {
  zipCode:       "",
  radius:        25,
  visaTypes:     [],
  languages:     [],
  minRating:     0,
  maxFeeDollars: null,
  availability:  "All",
  sortBy:        "rating",
};

// =============================================================================
// Hook return type
// =============================================================================

export interface UseAttorneysReturn {
  attorneys: AttorneyProfile[];
  loading:   boolean;
  error:     string | null;
  total:     number;
  refetch:   () => void;
}

// =============================================================================
// API query params
// =============================================================================

export interface FetchAttorneysParams {
  zip_code?:      string;
  radius_miles?:  number;
  visa_types?:    string[];
  languages?:     string[];
  min_rating?:    number;
  max_fee_cents?: number;
  availability?:  string;
  sort_by?:       string;
  page?:          number;
  page_size?:     number;
}

// =============================================================================
// Helpers
// =============================================================================

/** Format US cents to display string  e.g. 15000 → "$150" */
export function formatFee(cents: number): string {
  if (cents === 0) return "—";
  return `$${Math.round(cents / 100)}`;
}

/** Deterministic avatar color from UUID */
const AVATAR_COLORS = [
  "#4F46E5", "#0891B2", "#7C3AED", "#DB2777",
  "#059669", "#D97706", "#DC2626", "#2563EB",
];
export function getAvatarColor(id: string): string {
  const index = id.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}