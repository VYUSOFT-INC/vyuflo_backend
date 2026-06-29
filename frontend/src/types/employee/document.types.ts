// src/types/document.types.ts
// Single source of truth — imported by both api/documents.api.ts and hooks/useDocuments.ts

export type DocumentStatus =
  | "pending_review"
  | "verified"
  | "rejected"
  | "uploaded"
  | "required"
  | "missing";

export interface Document {
  id:              string;
  application_id:  string | null;   // FIX — can be null for personal docs
  user_id:         string;
  name:            string;          // file_name from backend
  file_type:       string;          // file_format from backend e.g. "pdf" | "jpg"
  file_size_bytes: number;          // file_size_kb * 1024 from backend
  status:          DocumentStatus;
  document_type:   string;          // DocumentType.name e.g. "passport"
  category:        string;          // "identity" | "employment" | "education"
  note?:           string;          // e.g. "Awaiting manager approval"
  uploaded_at?:    string;          // created_at from backend (ISO datetime)
  verified_at?:    string;
  rejection_reason?: string;
  total_pages?:    number;
  ocr_status?:     string;
  version?:        number;
  created_at:      string;
  updated_at:      string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}