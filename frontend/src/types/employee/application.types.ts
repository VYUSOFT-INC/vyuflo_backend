// src/types/application.types.ts

export type ApplicationStatus =
  | "draft"
  | "in_progress"
  | "action_needed"
  | "rfe_response"
  | "submitted"
  | "approved"
  | "rejected"
  | "withdrawn";

export type ApplicationStage =
  | "profile_eligibility"
  | "documentation"
  | "lca_filing"
  | "uscis_submission";

export interface VisaType {
  id:                 string;
  name:               string;
  code:               string;
  description:        string;
  requirements:       string[];   // backend field name
  required_documents: string[];   // alias — same data, used in NewApplication
}

export interface Application {
  id:                   string;
  application_number:   string;
  user_id:              string;
  visa_type_id:         string;
  visa_type?:           VisaType;      // ← ADD THIS LINE
  sponsor_employer?:    string;
  status:               ApplicationStatus;
  current_stage?:       ApplicationStage;
  progress_percent:     number;
  start_date?:          string;
  due_date?:            string;
  submission_date?:     string;
  is_draft:             boolean;
  has_action_required:  boolean;
  action_required_note?: string;
  assigned_attorney_id?: string;
  assigned_hr_id?:       string;
  notes?:               string;
  created_at:           string;
  updated_at:           string;
}


export interface ApplicationListResponse {
  items:         Application[];
  total:         number;
  in_progress:   number;    // ← flat, matches backend exactly
  action_needed: number;
  approved:      number;
}

export interface ApplicationCreate {
  visa_type_id:      string;
  sponsor_employer?: string;
  notes?:            string;
}

export interface ApplicationUpdate {
  sponsor_employer?:    string;
  notes?:               string;
  due_date?:            string;
  assigned_attorney_id?: string;
  assigned_hr_id?:      string;
}

export interface ApplicationStatusUpdate {
  status:         ApplicationStatus;
  current_stage?: ApplicationStage;
  note?:          string;
}

// ── Status History ────────────────────────────────────────────────────────────

export interface StatusHistory {
  id:             string;
  application_id: string;
  status:         ApplicationStatus;
  stage?:         ApplicationStage;
  note?:          string;
  created_by:     string;
  created_at:     string;
}

export interface StatusHistoryCreate {
  status:  ApplicationStatus;
  stage?:  ApplicationStage;
  note?:   string;
}

// ── Tasks ─────────────────────────────────────────────────────────────────────

// export interface Task {
//   id:              string;
//   application_id:  string;
//   name:            string;
//   description?:    string;
//   sort_order:      number;
//   is_completed:    boolean;
//   completed_at?:   string;
//   completed_by?:   string;
//   created_at:      string;
//   updated_at:      string;
// }

export interface Task {
  id:                    string;
  application_id:        string;
  name:                  string;
  description?:          string;
  sort_order:            number;
  is_completed:          boolean;
  completed_at?:         string;
  completed_by?:         string;
  // ← document linked to this task (filled when user uploads)
  document_id?:          string;
  document_name?:        string;   // "passport_scan_2023.pdf"
  document_size_bytes?:  number;   // raw bytes → formatted to "2.4 MB"
  document_uploaded_at?: string;   // ISO datetime
  created_at:            string;
  updated_at:            string;
}

export interface TaskCreate {
  name:         string;
  description?: string;
  sort_order?:  number;
}

export interface TaskUpdate {
  name?:        string;
  description?: string;
  sort_order?:  number;
}

export interface TaskCompleteRequest {
  is_completed: boolean;
}
