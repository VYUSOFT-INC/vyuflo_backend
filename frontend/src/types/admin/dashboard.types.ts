// src/types/dashboard.types.ts

export interface DashboardStats {
  active_applications:  number;
  documents_verified:   number;
  documents_total:      number;
  documents_action_required: number;
  processing_days:      number;
  processing_type:      string;    // "Standard Processing" | "Premium Processing"
  sponsor_name:         string;
  sponsor_stage:        string;    // "LCA Filed" | "I-129 Submitted" etc.
  sponsor_verified:     boolean;
  profile_readiness:    number;    // 0–100 percentage
}

export interface ActivityItem {
  id:          string;
  title:       string;
  description: string;
  timestamp:   string;     // ISO string
  color:       string;     // "#5269f2" | "#10b981" | "#cbd5e1"
}

export interface GuidanceItem {
  id:          string;
  tag:         string;     // "Required" | "Optional" | "Tip" | "Info"
  tag_color:   string;     // "blue" | "purple" | "gray"
  title:       string;
  description: string;
  icon_type:   string;
}

export interface DashboardResponse {
  stats:      DashboardStats;
  activity:   ActivityItem[];
  guidance:   GuidanceItem[];
}

export interface ProfileReadiness {
  percentage: number;
  items: {
    label:    string;
    done:     boolean;
  }[];
}

// Add this alongside your existing interfaces
export interface DashboardCounts {
  total_users: number;
  total_active_users: number;
}

// ── NEW: Recent logins list ───────────────────────────────────────
// GET /api/v1/dashboard/recent-logins?limit=20&offset=0
// Response: { "items": [ { full_name, email, role_name, status, last_login } ] }
 
export interface RecentLoginUser {
  full_name:   string;
  email:       string;
  role_name:   string;
  status:      string | null;
  last_login?: string | null;
}
 
export interface RecentLoginsResponse {
  items:  RecentLoginUser[];
  total?: number;             // may or may not be returned by the API
}