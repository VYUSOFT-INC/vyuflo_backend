// src/hooks/useMessages.ts
import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import messageApi from "../../api/employee/message.api";
import type {
  Conversation,
  Message,
  SendMessagePayload,
} from "../../types/employee/message.types";

export function useMessages() {
  const [conversations,   setConversations]  = useState<Conversation[]>([]);
  const [messages,        setMessages]       = useState<Message[]>([]);
  const [activeConvId,    setActiveConvIdRaw] = useState<string | null>(null);
  const [isLoading,       setIsLoading]      = useState(true);
  const [isSending,       setIsSending]      = useState(false);
  const [isCreating,      setIsCreating]     = useState(false);
  const [searchQuery,     setSearchQuery]    = useState("");
  const [activeTab,       setActiveTab]      = useState<"all" | "unread" | "archived">("all");

  const convPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const msgPollRef  = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Read ?thread_id= from URL — auto-opens a specific conversation ────────
  // Used when "Message Support" button in ApplicationDetail navigates here.
  const [searchParams] = useSearchParams();

  // ── Fetch conversations ───────────────────────────────────────────────────
  const fetchConversations = useCallback(async () => {
    try {
      const items = await messageApi.listConversations();
      setConversations(items);
    } catch (e) {
      console.error("Failed to fetch conversations", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── Fetch messages for active thread ─────────────────────────────────────
  const fetchMessages = useCallback(async (threadId: string) => {
    try {
      const items = await messageApi.listMessages(threadId);
      setMessages(items);
    } catch (e) {
      console.error("Failed to fetch messages", e);
    }
  }, []);

  // ── Set active conversation ───────────────────────────────────────────────
  const setActiveConvId = useCallback((id: string | null) => {
    setActiveConvIdRaw(id);
    setMessages([]);

    if (id) {
      fetchMessages(id);

      // Mark as read immediately
      messageApi.markRead(id).then(() => {
        setConversations(prev =>
          prev.map(c => c.id === id ? { ...c, unread_count: 0 } : c)
        );
      }).catch(() => {});
    }

    // Reset message polling
    if (msgPollRef.current) {
      clearInterval(msgPollRef.current);
      msgPollRef.current = null;
    }
    if (id) {
      msgPollRef.current = setInterval(() => fetchMessages(id), 5000);
    }
  }, [fetchMessages]);

  // ── Create new conversation ───────────────────────────────────────────────
  // Called from:
  //   1. Pencil ✏️ icon in SecureMessaging sidebar
  //   2. "Message Support" button in ApplicationDetail
  //      (navigate to /messages?thread_id=xxx handles it via URL param below)
  const createConversation = useCallback(async (payload: {
    thread_type:      "direct" | "group";
    participant_ids:  string[];
    application_id?:  string;
    initial_message?: string;
  }): Promise<Conversation | null> => {
    setIsCreating(true);
    try {
      const thread = await messageApi.createConversation(payload);

      // Add to conversations list if not already there
      setConversations(prev => {
        const exists = prev.find(c => c.id === thread.id);
        if (exists) return prev;
        return [thread, ...prev];
      });

      // Auto-open the new/existing thread
      setActiveConvId(thread.id);
      return thread;
    } catch (e) {
      console.error("Failed to create conversation", e);
      return null;
    } finally {
      setIsCreating(false);
    }
  }, [setActiveConvId]);

  // ── Send message ──────────────────────────────────────────────────────────
  const sendMessage = useCallback(async ({
    conversationId, content, file,
  }: SendMessagePayload) => {
    setIsSending(true);
    try {
      const newMsg = file
        ? await messageApi.sendFile(conversationId, content, file)
        : await messageApi.sendText(conversationId, content ?? "");

      // Append to message list
      setMessages(prev => [...prev, newMsg]);

      // Update conversation preview
      setConversations(prev =>
        prev.map(c =>
          c.id === conversationId
            ? {
                ...c,
                last_message:    content ?? (file ? `📎 ${file.name}` : ""),
                last_message_at: newMsg.created_at,
              }
            : c
        )
      );
    } catch (e) {
      console.error("Failed to send message", e);
    } finally {
      setIsSending(false);
    }
  }, []);

  // ── On mount: fetch conversations + handle ?thread_id= URL param ──────────
  useEffect(() => {
    fetchConversations();
    convPollRef.current = setInterval(fetchConversations, 5000);
    return () => {
      if (convPollRef.current) clearInterval(convPollRef.current);
      if (msgPollRef.current)  clearInterval(msgPollRef.current);
    };
  }, [fetchConversations]);

  // ── Auto-open thread from URL param — runs after conversations load ────────
  // When ApplicationDetail navigates: /messages?thread_id=xxx
  useEffect(() => {
    const threadIdFromUrl = searchParams.get("thread_id");
    if (threadIdFromUrl && !activeConvId && !isLoading) {
      setActiveConvId(threadIdFromUrl);
    }
  }, [searchParams, isLoading, activeConvId, setActiveConvId]);

  return {
    conversations,
    messages,
    activeConvId,
    setActiveConvId,
    sendMessage,
    createConversation,   // ← NEW: used by pencil icon modal
    isLoading,
    isSending,
    isCreating,           // ← NEW: loading state for create
    searchQuery,          setSearchQuery,
    activeTab,            setActiveTab,
  };
}