// src/types/documentHub.types.ts

export type DocFileType = "pdf" | "docx" | "img" | "other";
export type DocStatus   = "verified" | "pending_review" | "uploaded" | "rejected" | "required" | "missing";

export interface HubDocument {
  id:              string;
  name:            string;
  file_type:       DocFileType;
  status:          DocStatus;
  document_type:   string;
  category:        string;
  application_name?: string;
  application_id?: string;
  file_size_bytes: number;
  uploaded_at:     string;
  verified_at?:    string;
}

export interface RequirementItem {
  id:           string;
  task_name:    string;
  status:       DocStatus;
  document_id?: string;
}

export interface HubRequirements {
  application_id: string;        // ← ADD — which app these tasks belong to
  visa_code:      string;
  done:           number;
  total:          number;
  items:          RequirementItem[];
}

// ← ADD — one tab per application the user has
export interface ApplicationTab {
  id:        string;             // application UUID
  label:     string;             // shown in tab e.g. "H-1B"
  visa_code: string;             // e.g. "H-1B"
  status:    string;             // "draft" | "in_progress" | "submitted" etc.
}

export interface ActivityItem {
  id:        string;
  text:      string;
  by:        string;
  timestamp: string;
}

export interface StorageInfo {
  used_mb:  number;
  total_mb: number;
}

export interface DocumentHubData {
  documents:       HubDocument[];
  requirements:    HubRequirements | null;
  activity:        ActivityItem[];
  storage:         StorageInfo;
  total:           number;
  applicationTabs: ApplicationTab[];   // ← ADD
}