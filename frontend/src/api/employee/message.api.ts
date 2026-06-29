// src/api/message.api.ts

import axios from "../axios";
import type {
  Conversation,
  Message,
  ThreadListResponse,
  MessageListResponse,
} from "../../types/employee/message.types";

const messageApi = {

  // ── GET /messages/conversations ───────────────────────────────────────────
  // Returns all threads for current user, sorted by most recent.
  listConversations: async (): Promise<Conversation[]> => {
    const res = await axios.get<ThreadListResponse>("/messages/conversations");
    const data = res.data;
    return Array.isArray(data) ? data : data.items ?? [];
  },

  // ── GET /messages/conversations/:id ──────────────────────────────────────
  // Get a single conversation by ID.
  getConversation: async (threadId: string): Promise<Conversation> => {
    const res = await axios.get<Conversation>(`/messages/conversations/${threadId}`);
    return res.data;
  },

  // ── POST /messages/conversations ─────────────────────────────────────────
  // Create a new direct or group conversation.
  // For direct threads: returns existing thread if one already exists (idempotent).
  // Called from:
  //   - "Message Support" button in ApplicationDetail
  //   - Pencil ✏️ icon in SecureMessaging
  createConversation: async (payload: {
    thread_type:      "direct" | "group";
    participant_ids:  string[];
    application_id?:  string;
    title?:           string;
    initial_message?: string;
  }): Promise<Conversation> => {
    const res = await axios.post<Conversation>("/messages/conversations", payload);
    return res.data;
  },

  // ── GET /messages/conversations/:id/messages ──────────────────────────────
  // Returns messages oldest-first. limit/offset for pagination.
  listMessages: async (
    threadId: string,
    limit    = 100,
    offset   = 0,
  ): Promise<Message[]> => {
    const res = await axios.get<MessageListResponse>(
      `/messages/conversations/${threadId}/messages`,
      { params: { limit, offset } },
    );
    const data = res.data;
    return Array.isArray(data) ? data : data.items ?? [];
  },

  // ── POST /messages/conversations/:id/messages (text) ─────────────────────
  sendText: async (threadId: string, content: string): Promise<Message> => {
    const res = await axios.post<Message>(
      `/messages/conversations/${threadId}/messages`,
      { content },
    );
    return res.data;
  },

  // ── POST /messages/conversations/:id/messages (file) ─────────────────────
  sendFile: async (threadId: string, content: string | undefined, file: File): Promise<Message> => {
    const form = new FormData();
    if (content) form.append("content", content);
    form.append("file", file);
    const res = await axios.post<Message>(
      `/messages/conversations/${threadId}/messages`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return res.data;
  },

  // ── PATCH /messages/conversations/:id/read ────────────────────────────────
  // Resets unread_count to 0 for current user. Called when user opens a thread.
  markRead: async (threadId: string): Promise<void> => {
    await axios.patch(`/messages/conversations/${threadId}/read`);
  },

  // ── GET /users?roles=hr,attorney ─────────────────────────────────────────
  // Used by the New Conversation modal to show who the employee can message.
  listStaff: async (): Promise<{
    id:         string;
    first_name: string;
    last_name:  string;
    role:       string;
    avatar_url?: string;
  }[]> => {
    const res = await axios.get("/users", {
      params: { roles: "hr,attorney,support" },
    });
    const data = res.data;
    return Array.isArray(data) ? data : data.items ?? [];
  },
};

export default messageApi;