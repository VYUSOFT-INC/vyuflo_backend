// src/types/support.types.ts
//
// Types for the Admin Help & Support endpoints.

/* ───── Article (FAQ + Popular Articles) ────────────────────────────── */

export type ArticleType = 'faq' | 'article' | string;

export interface SupportArticle {
  id:           string;
  title:        string;
  summary:      string;
  body:         string;
  article_type: ArticleType;
  category:     string;
  tag:          string;
  view_count:   number;
  is_featured:  boolean;
  published_at: string;
  updated_at:   string;
}

export interface SupportArticlesResponse {
  items:       SupportArticle[];
  total:       number;
  page:        number;
  limit:       number;
  total_pages: number;
}

export interface ListArticlesParams {
  page?:         number;
  limit?:        number;
  category?:     string;
  search?:       string;
  article_type?: ArticleType;
  featured?:     boolean;
}

/* ───── System Status ───────────────────────────────────────────────── */

export type ServiceStatus = 'operational' | 'degraded' | 'down' | string;

export interface SystemStatusService {
  service_name:  string;
  status:        ServiceStatus;
  uptime_label:  string;   // e.g. "99.9% Uptime"
  status_badge:  string;   // e.g. "Operational"
}

export interface SystemStatusResponse {
  overall_status:       string;     // e.g. "All Systems Operational"
  services:             SystemStatusService[];
  view_status_page_url: string;
}

/* ───── Tickets ─────────────────────────────────────────────────────── */

export type TicketCategory = 'technical' | 'billing' | 'integration' | 'general' | 'other' | string;
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent' | string;

export interface CreateTicketBody {
  subject:  string;
  body:     string;
  category: TicketCategory;
  priority: TicketPriority;
}

export interface CreatedTicket {
  id:            string;
  ticket_number: string;
  subject:       string;
  category:      string;
  priority:      string;
  status:        string;
  created_at:    string;
}