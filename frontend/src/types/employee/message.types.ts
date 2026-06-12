// src/types/message.types.ts

// ── Matches ThreadResponse from backend ──────────────────────────────────────
export interface Conversation {
  id:               string;
  thread_type:      "direct" | "group";
  title?:           string;
  application_id?:  string;
  is_archived:      boolean;

  // The other participant (direct) or group info
  participant_id?:  string;
  participant_name: string;
  participant_role?: string;
  avatar_url?:      string;
  is_online:        boolean;

  // Left-panel preview
  last_message?:    string;
  last_message_at?: string;
  unread_count:     number;

  created_at:       string;
}

// ── Matches MessageResponse from backend ─────────────────────────────────────
export interface Message {
  id:           string;
  thread_id:    string;
  sender_id:    string;
  content?:     string;
  message_type: "text" | "file_attachment" | "call_event" | "system_notification";

  // Attachment fields
  attachment_name?: string;
  attachment_url?:  string;
  attachment_size?: string;
  document_id?:     string;

  // Call fields
  call_duration_seconds?: number;
  call_status?: "incoming" | "outgoing" | "missed" | "declined";

  is_read:    boolean;
  is_edited:  boolean;
  is_deleted: boolean;

  created_at: string;
  updated_at?: string;
}

export interface ThreadListResponse {
  items: Conversation[];
  total: number;
}

export interface MessageListResponse {
  items: Message[];
  total: number;
}

export interface SendMessagePayload {
  conversationId: string;
  content?:       string;
  file?:          File;
}