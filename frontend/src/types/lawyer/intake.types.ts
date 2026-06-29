// src/types/lawyer/intake.types.ts
//
// All types for Client Intake Form (Lawyer flow).
// Matches Swagger: /api/v1/intake/* + /api/v1/clients/{client_id}/profile

/* ── Dropdown options ───────────────────────────────────────────────── */
export interface VisaStatusOption {
  value: string;   // e.g. "F1"
  label: string;   // e.g. "F-1 Student"
}

export interface VisaStatusOptionsResponse {
  items: VisaStatusOption[];
}

/* ── Previous visa entry (repeatable in Step 3) ─────────────────────── */
export interface PreviousVisa {
  visa_type:       string;   // e.g. "F1"
  visa_number:     string;
  issue_date:      string;   // YYYY-MM-DD
  expiry_date:     string;   // YYYY-MM-DD
  issuing_country: string;
}

/* ── Intake data (the form fields the lawyer/client fills) ──────────── */
export interface IntakeData {
  id?:                  string;
  intake_session_id?:   string;

  // Step 1 — Personal Info
  first_name:           string;
  last_name:            string;
  date_of_birth:        string;   // YYYY-MM-DD
  gender:               string;
  nationality:          string;
  passport_number:      string;
  passport_expiry_date: string;   // YYYY-MM-DD
  email:                string;

  // Step 3 — Immigration
  current_visa_status:  string;
  visa_expiration_date: string;   // YYYY-MM-DD
  has_visa_denial:      boolean;
  visa_denial_details:  string;
  has_overstay:         boolean;
  previous_visas:       PreviousVisa[];

  created_at?:          string;
  updated_at?:          string;
}

/* ── Session (the wizard's state container on the backend) ──────────── */
export interface IntakeSession {
  id:                 string;
  application_id:     string;
  token:              string;
  token_expires_at:   string;
  current_step:       number;          // 0..5
  step_1_completed:   boolean;
  step_2_completed:   boolean;
  step_3_completed:   boolean;
  step_4_completed:   boolean;
  step_5_completed:   boolean;
  is_draft:           boolean;
  last_saved_at:      string | null;
  is_submitted:       boolean;
  submitted_at:       string | null;
  created_at:         string;
  updated_at:         string;
  intake_data:        IntakeData | null;
}

/* ── Create session payload + response ──────────────────────────────── */
export interface CreateSessionPayload {
  application_id: string;
  generate_link?: boolean;
}

/* ── Generate client link response ──────────────────────────────────── */
export interface GenerateLinkResponse {
  token:            string;
  client_url:       string;
  token_expires_at: string;
}

/* ── Save draft response ────────────────────────────────────────────── */
export interface SaveDraftResponse {
  detail:        string;
  last_saved_at: string;
  current_step:  number;
}

/* ── Submit response ────────────────────────────────────────────────── */
export interface SubmitResponse {
  detail:       string;
  submitted_at: string;
  session_id:   string;
}

/* ── PUT /data params + payload ────────────────────────────────────── */
export type StepNumber = 1 | 2 | 3 | 4 | 5;

export interface SaveIntakeDataParams {
  step_completed?: StepNumber;     // omit for auto-save & Save Draft
}

/** Partial intake data — only send changed fields. */
export type SaveIntakeDataPayload = Partial<IntakeData>;

/* ── Empty-state helper ─────────────────────────────────────────────── */
export const EMPTY_INTAKE_DATA: IntakeData = {
  first_name:           '',
  last_name:            '',
  date_of_birth:        '',
  gender:               '',
  nationality:          '',
  passport_number:      '',
  passport_expiry_date: '',
  email:                '',
  current_visa_status:  '',
  visa_expiration_date: '',
  has_visa_denial:      false,
  visa_denial_details:  '',
  has_overstay:         false,
  previous_visas:       [],
};

export const EMPTY_PREVIOUS_VISA: PreviousVisa = {
  visa_type:       '',
  visa_number:     '',
  issue_date:      '',
  expiry_date:     '',
  issuing_country: '',
};