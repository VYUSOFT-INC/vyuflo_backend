// src/api/selectAttorney.api.ts
import type {
  AttorneyProfile,
  AttorneyListResponse,
  FetchAttorneysParams,
} from "../../types/employee/selectAttorney.types";
import axios from "../axios";

// =============================================================================
// Attorney API
// =============================================================================

export const attorneyApi = {

  /**
   * GET /api/v1/attorneys
   * Returns paginated + enriched attorney list for the Select Attorney screen.
   * All filtering, sorting, badge computation done server-side.
   */
  list: async (params?: FetchAttorneysParams): Promise<AttorneyListResponse> => {
    // visa_types[] and languages[] must be sent as repeated query params
    // e.g. ?visa_types=H-1B&visa_types=O-1 — axios serialises arrays correctly
    const res = await axios.get<AttorneyListResponse>("/attorneys", {
      params,
      paramsSerializer: (p) => {
        const qs = new URLSearchParams();
        Object.entries(p).forEach(([key, val]) => {
          if (val === undefined || val === null) return;
          if (Array.isArray(val)) {
            val.forEach((v) => qs.append(key, String(v)));
          } else {
            qs.set(key, String(val));
          }
        });
        return qs.toString();
      },
    });
    return res.data;
  },

  /**
   * GET /api/v1/attorneys/:id
   * Returns a single enriched attorney — used by BookConsultation to pre-fill
   * the Selected Attorney card.
   */
  get: async (attorneyId: string): Promise<AttorneyProfile> => {
    const res = await axios.get<AttorneyProfile>(`/attorneys/${attorneyId}`);
    return res.data;
  },
};

// ── Named exports (matches application.api.ts pattern) ───────────────────────

export const listAttorneys = (params?: FetchAttorneysParams) =>
  attorneyApi.list(params);

export const getAttorney = (id: string) =>
  attorneyApi.get(id);