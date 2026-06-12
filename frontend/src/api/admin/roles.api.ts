// src/api/roles.api.ts
import axios from "../axios";
import type {
  Role,
  RoleListResponse,
  RoleDetail,
  PermissionListResponse,
  CreateRolePayload,
} from "../../types/admin/roles.types";

// NOTE on paths ────────────────────────────────────────────────────────────────
// The working endpoint is  <ngrok>/api/v1/roles  and  <ngrok>/api/v1/permissions
// So these relative paths assume your axios baseURL ends with  /api
// 👉 Open src/api/axios.ts and check baseURL:
//    • baseURL = ".../api"      → keep "/v1/roles"   (as below)
//    • baseURL = ".../api/v1"   → change all to "/roles", "/permissions", ...
// (Your applications.api uses "/applications", so double-check which one is right.)

// ── Reads ───────────────────────────────────────────────────────────────────────

/** GET /v1/roles — list all roles */
export const fetchRoles = async (): Promise<RoleListResponse> => {
  const res = await axios.get("/roles");
  return res.data;
};

/** GET /v1/roles/:roleId — single role with its permissions */
export const fetchRoleById = async (roleId: string): Promise<RoleDetail> => {
  const res = await axios.get(`/roles/${roleId}`);
  return res.data;
};

/** GET /v1/permissions — full permission master list */
export const fetchAllPermissions = async (): Promise<PermissionListResponse> => {
  const res = await axios.get("/permissions");
  return res.data;
};

// ── Mutations ─────────────────────────────────────────────────────────────────

/** POST /v1/roles — create a custom role */
export const createRole = async (
  payload: CreateRolePayload
): Promise<Role> => {
  const res = await axios.post("/roles", payload);
  return res.data;
};

/** PATCH /v1/roles/:roleId — update name / description */
export const updateRole = async (
  roleId:  string,
  payload: Partial<CreateRolePayload>
): Promise<Role> => {
  const res = await axios.patch(`/roles/${roleId}`, payload);
  return res.data;
};

/** DELETE /v1/roles/:roleId — delete a role
 *  ⚠️ Confirm this endpoint exists and that the backend blocks deleting
 *  system roles. Remove this if your backend doesn't support it. */
export const deleteRole = async (roleId: string): Promise<void> => {
  await axios.delete(`/roles/${roleId}`);
};

/** POST /v1/roles/:roleId/permissions — grant one permission */
export const assignPermissionToRole = async (
  roleId:       string,
  permissionId: string
): Promise<void> => {
  await axios.post(`/roles/${roleId}/permissions`, {
    permission_id: permissionId,
  });
};

/** DELETE /v1/roles/:roleId/permissions/:permissionId — revoke one permission */
export const removePermissionFromRole = async (
  roleId:       string,
  permissionId: string
): Promise<void> => {
  await axios.delete(`/roles/${roleId}/permissions/${permissionId}`);
};

/** PUT /v1/roles/:roleId/permissions/bulk — replace ALL permissions at once
 *  (use this instead of assign/remove if you prefer a single "Save" button) */
export const bulkReplacePermissions = async (
  roleId:        string,
  permissionIds: string[]
): Promise<void> => {
  await axios.put(`/roles/${roleId}/permissions/bulk`, {
    permission_ids: permissionIds,
  });
};