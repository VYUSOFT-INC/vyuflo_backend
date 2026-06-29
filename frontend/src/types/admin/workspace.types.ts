// src/types/workspace.types.ts
//
// Types for the Workspace Dashboard endpoints.
// Currently only the /team endpoint is consumed (by Admin Dashboard's
// Resource Allocation widget). Other endpoints listed for future use.

/* ───── Team workload (used by Resource Allocation widget) ──────────── */

export interface TeamMember {
  id:                     string;
  first_name:             string;
  last_name:              string;
  email:                  string;
  role:                   string;          // "attorney" | "hr" | "app_admin" | etc.
  profile_picture_url:    string | null;
  law_firm_name:          string | null;
  is_accepting_cases:     boolean;
  max_active_cases:       number;          // capacity
  active_case_count:      number;          // current load
  pending_task_count:     number;
  overdue_deadline_count: number;
  last_login_at:          string;          // ISO timestamp
  is_online:              boolean;
}

export interface TeamWorkloadResponse {
  items: TeamMember[];
  total: number;
}