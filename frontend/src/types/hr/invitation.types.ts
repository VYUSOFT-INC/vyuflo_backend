// src/types/invitation.types.ts

// ── Request types ─────────────────────────────────────────────────────────────

export interface InviteByEmailRequest {
  email:            string;
  personal_message?: string;
  expires_days?:    number;  // default 7
}

export interface InviteByCodeRequest {
  max_uses?:         number;  // null = unlimited
  personal_message?: string;
}

export interface InviteByLinkRequest {
  max_uses?:         number;
  personal_message?: string;
  expires_days?:     number;
}

export interface AcceptInviteRequest {
  invite_token?: string;
  invite_code?:  string;
}

export interface UpdateEmployeeRequest {
  job_title?:  string;
  department?: string;
  work_email?: string;
  start_date?: string;  // YYYY-MM-DD
  is_active?:  boolean;
}

// ── Response types ────────────────────────────────────────────────────────────

export type InviteMethod = "email" | "link" | "code";
export type InviteStatus = "pending" | "accepted" | "expired" | "revoked";

export interface InvitationResponse {
  id:               string;
  invite_method:    InviteMethod;
  status:           InviteStatus;
  invited_email?:   string;
  invite_code?:     string;
  invite_token?:    string;
  max_uses?:        number;
  used_count:       number;
  expires_at?:      string;
  personal_message?: string;
  created_at:       string;
}

export interface ValidateTokenResponse {
  valid:         boolean;
  company_name?: string;
  hr_name?:      string;
  invite_method?: InviteMethod;
  message:       string;
}

export interface AcceptInviteResponse {
  message:      string;
  company_name: string;
  employer_id:  string;
}

export interface EmployeeResponse {
  id:                  string;
  employee_id:         string;
  full_name:           string;
  email:               string;
  profile_picture_url?: string;
  job_title?:          string;
  department?:         string;
  work_email?:         string;
  start_date?:         string;
  is_active:           boolean;
  active_applications: number;
  pending_documents:   number;
  linked_at:           string;
}

export interface InvitationListResponse {
  items: InvitationResponse[];
  total: number;
}

export interface EmployeeListResponse {
  items: EmployeeResponse[];
  total: number;
}