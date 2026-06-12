// src/types/settings.types.ts

export type SettingValueType = "string" | "boolean" | "integer" | "json" | "url";

export interface SettingItem {
  id:            string;
  key:           string;
  value:         string;          // always stored as string
  value_type:    SettingValueType;
  setting_group: string;          // "general" | "security" | "notifications" | "features" | "maintenance" ...
  label:         string;
  description:   string | null;
  is_public:     boolean;
  is_readonly:   boolean;
  display_order: number;
  created_at:    string;
  updated_at:    string;
}

export interface SettingListResponse {
  items:   SettingItem[];
  total:   number;
  grouped: Record<string, SettingItem[]> | null;
}

export interface SettingPatch {
  key:   string;
  value: string;
}

export interface SettingBulkUpdatePayload {
  updates: SettingPatch[];
}