// src/api/support.api.ts
//
// Admin Help & Support endpoints. Confirmed URLs from Swagger:
//   GET  /admin/support/articles            — list (FAQ / Popular / Search / Category)
//   GET  /admin/support/articles/{id}       — get single article (also increments view_count)
//   GET  /admin/support/system-status       — System Status card
//   POST /admin/support/tickets             — Create Ticket

import axios from '../axios';
import type {
  SupportArticle,
  SupportArticlesResponse,
  ListArticlesParams,
  SystemStatusResponse,
  CreateTicketBody,
  CreatedTicket,
} from '../../types/admin/support.types';

export const SUPPORT_PATHS = {
  articles:     '/admin/support/articles',
  article:      (id: string) => `/admin/support/articles/${id}`,
  systemStatus: '/admin/support/system-status',
  tickets:      '/admin/support/tickets',
} as const;

export const supportApi = {
  /** List articles — used by FAQ, Popular sidebar, Search, Category tabs. */
  listArticles: async (
    params: ListArticlesParams = {},
  ): Promise<SupportArticlesResponse> => {
    const res = await axios.get(SUPPORT_PATHS.articles, { params });
    return res.data;
  },

  /** Get single article / FAQ detail (also increments view_count). */
  getArticle: async (id: string): Promise<SupportArticle> => {
    const res = await axios.get(SUPPORT_PATHS.article(id));
    return res.data;
  },

  /** System Status card data. */
  getSystemStatus: async (): Promise<SystemStatusResponse> => {
    const res = await axios.get(SUPPORT_PATHS.systemStatus);
    return res.data;
  },

  /** Submit a support ticket — Create Ticket button. */
  createTicket: async (body: CreateTicketBody): Promise<CreatedTicket> => {
    const res = await axios.post(SUPPORT_PATHS.tickets, body);
    return res.data;
  },
};