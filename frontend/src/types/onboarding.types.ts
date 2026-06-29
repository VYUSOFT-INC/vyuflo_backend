// // src/types/onboarding.types.ts

// export interface OnboardingStatus {
//   current_step:         string | number;
//   onboarding_completed: boolean;
//   roles:                string[];
//   full_legal_name?:     string;
//   nationality?:         string;
//   visa_targets:         string[];
// }

// export interface OnboardingProfileRequest {
//   full_legal_name: string;
//   nationality:     string;
//   visa_targets:    string[];
// }

// export interface OnboardingRoleRequest {
//   role: string;
// }

// export interface VerifyEmailRequest {
//   otp: string;
// }



// src/types/onboarding.types.ts

// ── Existing (unchanged) ──────────────────────────────────────────────────────

export interface OnboardingStatus {
  current_step:         string | number;
  onboarding_completed: boolean;
  roles:                string[];
  full_legal_name?:     string;
  nationality?:         string;
  visa_targets:         string[];
}

export interface OnboardingRoleRequest {
  role: string;
}

export interface VerifyEmailRequest {
  otp: string;
}

// ── Employee profile request (existing endpoint POST /onboarding/profile) ─────

export interface OnboardingProfileRequest {
  full_legal_name:      string;
  nationality:          string;
  visa_targets:         string[];
  date_of_birth?:       string;       // "YYYY-MM-DD"
  gender?:              string;
  country_of_residence?: string;
  primary_visa?:        string;
  timezone?:            string;
  preferred_language?:  string;
}

// ── Attorney profile request (POST /onboarding/attorney-profile) ──────────────

export interface AttorneyProfileRequest {
  // Personal
  full_legal_name?:      string;
  date_of_birth?:        string;
  gender?:               string;
  nationality?:          string;
  country_of_residence?: string;
  timezone?:             string;
  preferred_language?:   string;
  // Professional
  bar_number?:           string;
  bar_state?:            string;      // "CA" | "NY" | …
  law_firm_name?:        string;
  years_experience?:     number;
  specialisations:       string[];    // ["H-1B", "O-1", "EB-2"]
  languages:             string[];    // ["English", "Spanish"]
  bio?:                  string;
  availability_note?:    string;      // "Mon–Fri 9am–6pm EST"
}

// ── HR / Employer profile request (POST /onboarding/hr-profile) ───────────────

export type CompanySize = "1_10" | "11_50" | "51_200" | "201_500" | "501_1000" | "1000_plus";

export interface HRProfileRequest {
  // Personal
  full_legal_name?:      string;
  date_of_birth?:        string;
  gender?:               string;
  nationality?:          string;
  country_of_residence?: string;
  timezone?:             string;
  preferred_language?:   string;
  // Company — maps to employer_profiles table
  company_name:          string;      // required
  company_size?:         CompanySize;
  industry?:             string;
  website?:              string;
  ein?:                  string;      // Employer Identification Number
  address_line1?:        string;
  address_line2?:        string;
  city?:                 string;
  state?:                string;
  zip_code?:             string;
  country?:              string;
  contact_name?:         string;
  contact_email?:        string;
  contact_phone?:        string;
}

// ── Admin profile request (POST /onboarding/admin-profile) ───────────────────

export interface AdminProfileRequest {
  full_legal_name?:      string;
  date_of_birth?:        string;
  gender?:               string;
  nationality?:          string;
  country_of_residence?: string;
  timezone?:             string;
  preferred_language?:   string;
}

// ── Shared complete response ──────────────────────────────────────────────────

export interface OnboardingCompleteResponse {
  current_step:         number;
  onboarding_completed: boolean;
  roles:                string[];
  dashboard_route:      string;   // "/dashboard" | "/lawyer/dashboard" | …
}