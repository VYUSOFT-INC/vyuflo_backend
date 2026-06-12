// src/api/users.api.ts

import axios from "./axios";

// ── Types ──────────────────────────────────────────────────────────
export type UserRole   = "HR Admin" | "Applicant" | "Lawyer" | "Admin";
export type UserStatus = "Active" | "Pending" | "Suspended";

export interface AdminUser {
  id:          string;
  name:        string;
  email:       string;
  role:        UserRole;
  company:     string;
  status:      UserStatus;
  lastLogin:   string;
  initials:    string;
  avatarColor: string;
}

export interface UserStats {
  totalUsers:      { value: number; trend: string; trendUp: boolean };
  activeAccounts:  { value: number; trend: string; trendUp: boolean };
  pendingApproval: { value: number; trend: string; trendUp: boolean };
  suspended:       { value: number; trend: string; trendUp: null   };
}

export interface UserListResponse {
  users:      AdminUser[];
  total:      number;
  page:       number;
  limit:      number;
  totalPages: number;
}

export interface CreateUserPayload {
  name:     string;
  email:    string;
  role:     UserRole;
  company:  string;
  password: string;
}

// ── API calls ──────────────────────────────────────────────────────

/** GET /admin/users/stats */
export const fetchUserStats = async (): Promise<UserStats> => {
  const res = await axios.get("/admin/users/stats");
  return res.data.data;
};

/** GET /admin/users */
export const fetchUsers = async (params?: {
  search?: string;
  role?:   UserRole;
  status?: UserStatus;
  page?:   number;
  limit?:  number;
}): Promise<UserListResponse> => {
  const res = await axios.get("/admin/users", { params });
  return res.data.data;
};

/** GET /admin/users/:id */
export const fetchUserById = async (id: string): Promise<AdminUser> => {
  const res = await axios.get(`/admin/users/${id}`);
  return res.data.data.user;
};

/** POST /admin/users */
export const createUser = async (payload: CreateUserPayload): Promise<AdminUser> => {
  const res = await axios.post("/admin/users", payload);
  return res.data.data.user;
};

/** PUT /admin/users/:id */
export const updateUser = async (id: string, payload: Partial<AdminUser>): Promise<AdminUser> => {
  const res = await axios.put(`/admin/users/${id}`, payload);
  return res.data.data.user;
};

/** DELETE /admin/users/:id */
export const deleteUser = async (id: string): Promise<void> => {
  await axios.delete(`/admin/users/${id}`);
};

/** PUT /admin/users/:id/status */
export const updateUserStatus = async (id: string, status: UserStatus): Promise<AdminUser> => {
  const res = await axios.put(`/admin/users/${id}/status`, { status });
  return res.data.data.user;
};

/** PUT /admin/users/:id/role */
export const updateUserRole = async (id: string, role: UserRole): Promise<AdminUser> => {
  const res = await axios.put(`/admin/users/${id}/role`, { role });
  return res.data.data.user;
};

/** POST /admin/users/bulk-role */
export const bulkUpdateRole = async (userIds: string[], role: UserRole): Promise<{ updated: number }> => {
  const res = await axios.post("/admin/users/bulk-role", { userIds, role });
  return res.data.data;
};

/** GET /admin/users/export  — returns CSV blob */
export const exportUsers = async (params?: {
  role?:   UserRole;
  status?: UserStatus;
}): Promise<Blob> => {
  const res = await axios.get("/admin/users/export", { params, responseType: "blob" });
  return res.data;
};

/** POST /admin/users/invite */
export const inviteUser = async (email: string, role: UserRole): Promise<{ message: string }> => {
  const res = await axios.post("/admin/users/invite", { email, role });
  return res.data.data;
};
