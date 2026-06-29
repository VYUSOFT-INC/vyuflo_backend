// src/types/visaTypes.types.ts

export interface VisaTypeStats {
  total_visa_types:   number;
  active_visa_types:  number;
  pending_review:     number;
  active_cases:       number;
  total_pct_change:   number;
  active_pct_change:  number;
  pending_pct_change: number;
  cases_pct_change:   number;
}

export interface VisaTypeItem {
  id:                        string;
  code:                      string;
  name:                      string;
  short_label:               string | null;
  description:               string | null;
  category:                  string;   // employment | student | visitor | permanent_resident | exchange
  is_active:                 boolean;
  status:                    string;   // active | inactive | pending_review
  requires_employer_sponsor: boolean;
  required_documents:        string[];
  required_documents_count:  number;
  typical_processing_days:   number;
  processing_time_label:     string | null;
  government_fee_usd:        number;
  uscis_url:                 string | null;
  success_rate:              number;
  active_cases_count:        number;
  display_order:             number;
  created_at:                string;
  updated_at:                string;
  modified_by_name:          string | null;
}

export interface VisaTypeListResponse {
  stats:       VisaTypeStats;
  items:       VisaTypeItem[];
  total:       number;
  page:        number;
  page_size:   number;
  total_pages: number;
}

export interface VisaTypeListParams {
  search?:     string;
  category?:   string;     // backend enum
  status?:     string;     // backend enum
  sort_by?:    string;     // name | code | display_order | created_at | updated_at
  sort_order?: "asc" | "desc";
  page?:       number;
  page_size?:  number;
}

// Payload for POST /admin/visa-types.
// IMPORTANT: required_documents is a JSON array STRING, e.g. '["Passport Copy"]'.
export interface CreateVisaTypePayload {
  code:                       string;
  name:                       string;
  short_label?:               string;
  description?:               string;
  category:                   string;   // backend enum
  requires_employer_sponsor:  boolean;
  required_documents:         string;   // JSON array string
  typical_processing_days:    number;
  government_fee_usd:         number;
  uscis_url?:                 string;
  display_order:              number;
  is_active:                  boolean;
  status:                     string;   // active | inactive | pending_review
  success_rate:               number;
}