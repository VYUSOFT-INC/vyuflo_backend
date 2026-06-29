// src/api/settings.api.ts
import axios from "../axios";
import type {
  SettingListResponse,
  SettingBulkUpdatePayload,
} from "../../types/admin/settings.types";

// NOTE: paths assume axios baseURL ends with /api  → full URL /api/v1/settings
// If your baseURL already includes /v1, change these to "/settings".

/** GET /v1/settings — list all system settings (flat list) */
export const fetchSettings = async (): Promise<SettingListResponse> => {
 const res = await axios.get("/settings");
  return res.data;
};

/** PATCH /v1/settings/bulk — "Save Changes": update many at once */
export const bulkUpdateSettings = async (
  payload: SettingBulkUpdatePayload
): Promise<{ message: string; updated_count: number; keys: string[] }> => {
  const res = await axios.patch("/settings/bulk", payload);
  return res.data;
};