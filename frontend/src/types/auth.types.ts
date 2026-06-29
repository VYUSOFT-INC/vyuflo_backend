// Single source of truth — matches users table exactly

export interface User {
  id: string;
  // ── Basic Info ───────────────────────────────────────
  first_name:   string;
  last_name:    string;
  email:        string;
  phone:        string | null;
  country_code: string | null;
  // ── Auth ─────────────────────────────────────────────
  auth_provider:    'email' | 'google' | 'microsoft' | 'apple';
  auth_provider_id: string | null;
  // ── Status ───────────────────────────────────────────
  is_active:   boolean;
  is_verified: boolean;
  // ── Consent ──────────────────────────────────────────
  terms_accepted:    boolean;
  terms_accepted_at: string | null;
  marketing_opt_in:  boolean;
  newsletter_opt_in: boolean;
  referral_source:   string | null;
  // ── Onboarding (from UserProfile) ────────────────────
  onboarding_step:      number;
  onboarding_completed: boolean;
  // ── Roles ────────────────────────────────────────────
  roles: string[];
  // ── Timestamps ───────────────────────────────────────
  last_login_at: string | null;
  created_at:    string;
  updated_at:    string;
}

export interface TokenPayload {
  access_token:  string;
  refresh_token: string;
  token_type:    string;
  roles:         string[];
  profile:         string | null;
  user:User
  onboarding_step:number
}

export interface SignupBody {
  first_name:        string;
  last_name:         string;
  email:             string;
  password:          string;
  role:              string;
  phone?:            string;
  country_code?:     string;
  terms_accepted:    boolean;
  marketing_opt_in:  boolean;
  newsletter_opt_in: boolean;
  referral_source?:  string;
}

export interface LoginBody {
  email:    string;
  password: string;
}

export interface SSOBody {
  provider:        'google' | 'microsoft' | 'apple';
  provider_token:  string;
  terms_accepted?: boolean;
}

export interface SignupResponse extends TokenPayload {
  roles:            string[];
  onboarding_step:  number;
}

export interface LoginResponse extends TokenPayload {
  roles: string[];
}

export interface ResetRequestResponse {
  message:        string;
  reset_token_id: string;
}