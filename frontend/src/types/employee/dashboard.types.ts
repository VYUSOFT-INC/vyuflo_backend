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