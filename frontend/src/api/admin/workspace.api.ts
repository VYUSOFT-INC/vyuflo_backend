// src/api/workspace.api.ts
//
// API wrapper for Workspace Dashboard endpoints. Currently only /team is used
// (Resource Allocation widget on Admin Dashboard). Other endpoints listed for
// future expansion.

import axios from '../axios';
import type { TeamWorkloadResponse } from '../../types/admin/workspace.types';

export const WORKSPACE_PATHS = {
  dashboard:          '/workspace/dashboard',
  kpi:                '/workspace/kpi',
  recentApplications: '/workspace/recent-applications',
  myTasks:            '/workspace/my-tasks',
  upcomingDeadlines:  '/workspace/upcoming-deadlines',
  activityFeed:       '/workspace/activity-feed',
  casePipeline:       '/workspace/case-pipeline',
  pendingDocuments:   '/workspace/pending-documents',
  team:               '/workspace/team',
} as const;

export const workspaceApi = {
  /**
   * Team workload — attorneys and HR staff with live case metrics.
   * Visibility:
   *   app_admin → full team
   *   hr        → attorneys + HR
   *   attorney  → themselves only
   */
  getTeam: async (): Promise<TeamWorkloadResponse> => {
    const res = await axios.get(WORKSPACE_PATHS.team);
    return res.data;
  },
};