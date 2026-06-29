// src/types/roles.types.ts

// ── Role (list item) ───────────────────────────────────────────────────────────
export interface Role {
  id:               string;
  name:             string;        // machine name e.g. "app_admin"
  display_name:     string;        // pretty name e.g. "App Admin"
  description:      string;
  is_active:        boolean;
  permission_count: number;
  user_count:       number;
  created_at:       string;
  updated_at:       string;
}

export interface RoleListResponse {
  items: Role[];
  total: number;
}

// ── Permission ─────────────────────────────────────────────────────────────────
export interface PermissionItem {
  id:             string;
  code:           string;          // e.g. "applications.create"
  module:         string;          // e.g. "applications" (used to group cards)
  description:    string;          // human-readable label shown on the card
  roles_assigned: string[];        // role names that have this permission
  created_at:     string;
  updated_at:     string;
}

export interface PermissionListResponse {
  items:       PermissionItem[];
  total:       number;
  page:        number;
  limit:       number;
  total_pages: number;
}

// ── Role detail (single role + its permissions) ────────────────────────────────
export interface RoleDetail {
  id:               string;
  name:             string;
  description:      string;
  is_active:        boolean;
  permission_count: number;
  user_count:       number;
  permissions:      PermissionItem[];
  created_at:       string;
  updated_at:       string;
}

// ── Payloads ───────────────────────────────────────────────────────────────────
export interface CreateRolePayload {
  name:        string;
  description: string;
}