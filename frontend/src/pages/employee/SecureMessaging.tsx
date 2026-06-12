// src/pages/employee/SecureMessaging.tsx
import { useState, useEffect, useRef, useCallback } from "react";
import { useCurrentUser } from "../../hooks/useAuth";
import { useMessages } from "../../hooks/employee/useMessages";
import messageApi from "../../api/employee/message.api";
import type { Conversation, Message } from "../../types/employee/message.types";

// ── Assets ────────────────────────────────────────────────────────────────────
// import imgDefaultAvatar from "../../assets/icons/user-avatar-2.jpg";

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtTime(iso?: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function fmtConvTime(iso?: string): string {
  if (!iso) return "";
  const d    = new Date(iso);
  const now  = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 60000);
  if (diff < 1)    return "Just now";
  if (diff < 60)   return `${diff} min ago`;
  if (diff < 1440) return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  return "Yesterday";
}

function getInitials(name?: string): string {
  if (!name) return "?";
  return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
}

// Seeded color from name — consistent per user
const AVATAR_COLORS = [
  "bg-[#6366f1]", "bg-[#8b5cf6]", "bg-[#ec4899]",
  "bg-[#f59e0b]", "bg-[#10b981]", "bg-[#3b82f6]",
];
function avatarColor(name?: string): string {
  if (!name) return AVATAR_COLORS[0];
  const idx = name.split("").reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

// ── Avatar ────────────────────────────────────────────────────────────────────
function Avatar({
  src, name, size = 40, online,
}: {
  src?: string; name?: string; size?: number; online?: boolean;
}) {
  const [imgErr, setImgErr] = useState(false);
  const sz = `${size}px`;
  return (
    <div className="relative shrink-0" style={{ width: sz, height: sz }}>
      {src && !imgErr ? (
        <img
          src={src} alt={name ?? ""}
          onError={() => setImgErr(true)}
          className="rounded-full object-cover w-full h-full"
        />
      ) : (
        <div className={`${avatarColor(name)} rounded-full flex items-center justify-center
                         text-white font-semibold w-full h-full`}
             style={{ fontSize: size * 0.35 }}>
          {getInitials(name)}
        </div>
      )}
      {online !== undefined && (
        <span className={`absolute bottom-0 right-0 rounded-full border-2 border-white
                          ${online ? "bg-[#22c55e]" : "bg-[#94a3b8]"}`}
              style={{ width: size * 0.28, height: size * 0.28 }} />
      )}
    </div>
  );
}

// ── Conversation list item ────────────────────────────────────────────────────
function ConvItem({
  conv, active, onClick,
}: {
  conv: Conversation; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-[12px] px-[16px] py-[12px] text-left
                  transition-colors rounded-[12px] ${
        active
          ? "bg-[#f0f5ff]"
          : "hover:bg-[#f8fafc]"
      }`}
    >
      <Avatar src={conv.avatar_url} name={conv.participant_name} size={44} online={conv.is_online} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-[2px]">
          <p className={`text-[14px] tracking-[-0.3px] truncate ${
            conv.unread_count ? "font-semibold text-[#0f172a]" : "font-medium text-[#0f172a]"
          }`}>
            {conv.participant_name}
          </p>
          <span className="text-[11px] text-[#94a3b8] whitespace-nowrap ml-[8px] shrink-0">
            {fmtConvTime(conv.last_message_at)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-[8px]">
          <p className="text-[12px] text-[#64748b] truncate leading-[16px]">
            {conv.last_message ?? "No messages yet"}
          </p>
          {(conv.unread_count ?? 0) > 0 && (
            <span className="bg-[#3a46e5] text-white text-[10px] font-bold
                             rounded-full min-w-[18px] h-[18px] flex items-center justify-center
                             px-[5px] shrink-0">
              {conv.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({
  msg, isMine, senderAvatar, senderName,
}: {
  msg: Message; isMine: boolean; senderAvatar?: string; senderName?: string;
}) {
  const hasAttachment = !!msg.attachment_name;

  return (
    <div className={`flex items-end gap-[8px] ${isMine ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar — only for received messages */}
      {!isMine && (
        <Avatar src={senderAvatar} name={senderName} size={36} />
      )}

      <div className={`flex flex-col gap-[4px] max-w-[65%] ${isMine ? "items-end" : "items-start"}`}>
        {/* Attachment card */}
        {hasAttachment && (
          <div className={`flex items-center gap-[12px] px-[14px] py-[12px] rounded-[14px]
                           ${isMine
                             ? "rounded-br-[4px]"
                             : "rounded-bl-[4px]"
                           }`}
               style={isMine
                 ? { background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)" }
                 : { background: "#f1f5f9" }
               }>
            {/* File icon */}
            <div className={`rounded-[10px] flex items-center justify-center shrink-0 size-[40px] ${
              isMine ? "bg-white/20" : "bg-[#e2e8f0]"
            }`}>
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
                  fill={isMine ? "white" : "#6366f1"} fillOpacity={isMine ? 0.9 : 1} />
                <path d="M14 2v6h6" stroke={isMine ? "white" : "#6366f1"}
                  strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className={`text-[13px] font-semibold truncate max-w-[180px] ${
                isMine ? "text-white" : "text-[#0f172a]"
              }`}>
                {msg.attachment_name}
              </p>
              {msg.attachment_size && (
                <p className={`text-[11px] mt-[1px] ${isMine ? "text-white/70" : "text-[#64748b]"}`}>
                  {msg.attachment_size}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Text bubble */}
        {msg.content && (
          <div className={`px-[14px] py-[10px] rounded-[18px] ${
            isMine
              ? "rounded-br-[4px] text-white"
              : "rounded-bl-[4px] bg-white border border-[#f1f5f9] text-[#0f172a]"
          }`}
               style={isMine
                 ? { background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)" }
                 : undefined
               }>
            <p className="text-[14px] leading-[22px] tracking-[-0.2px]">{msg.content}</p>
          </div>
        )}

        {/* Timestamp + read receipt */}
        <div className={`flex items-center gap-[4px] ${isMine ? "flex-row-reverse" : "flex-row"}`}>
          <span className="text-[11px] text-[#94a3b8]">{fmtTime(msg.created_at)}</span>
          {isMine && msg.is_read && (
            <svg width="14" height="10" viewBox="0 0 16 10" fill="none">
              <path d="M1 5l4 4L15 1" stroke="#3a46e5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M5 5l4 4" stroke="#3a46e5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </div>
      </div>

      {/* Spacer for sent messages */}
      {isMine && <div className="size-[36px] shrink-0" />}
    </div>
  );
}

// ── Date separator ────────────────────────────────────────────────────────────
function DateSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-[12px] py-[8px]">
      <div className="flex-1 h-px bg-[#f1f5f9]" />
      <span className="text-[11px] text-[#94a3b8] font-medium px-[4px]">{label}</span>
      <div className="flex-1 h-px bg-[#f1f5f9]" />
    </div>
  );
}

// ── Call event pill ───────────────────────────────────────────────────────────
function CallEvent({ label, time }: { label: string; time: string }) {
  return (
    <div className="flex items-center justify-center gap-[8px] py-[4px]">
      <div className="bg-[#f0f5ff] border border-[#e5edff] rounded-full
                      flex items-center gap-[8px] px-[14px] py-[6px]">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.01 2.18 2 2 0 012 .01h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92z"
            stroke="#3a46e5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-[12px] text-[#3a46e5] font-medium">{label}</span>
        <span className="text-[11px] text-[#94a3b8]">{time}</span>
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyChat() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="flex flex-col items-center gap-[16px] text-center px-[32px]">
        <div className="bg-[#f0f5ff] rounded-full p-[24px]">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"
              stroke="#3a46e5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <p className="text-[#0f172a] text-[16px] font-semibold tracking-[-0.3px]">
            Select a conversation
          </p>
          <p className="text-[#64748b] text-[13px] mt-[4px]">
            Choose a conversation from the left to start messaging
          </p>
        </div>
      </div>
    </div>
  );
}

// ── New Conversation Modal ────────────────────────────────────────────────────
// Opens when user clicks pencil ✏️ icon in the Conversations header.
// Fetches HR/attorney staff list → user picks one → createConversation() called.
function NewConvModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose:    () => void;
  onCreate:   (userId: string, name: string) => void;
  isCreating: boolean;
}) {
  const [staff,   setStaff]   = useState<{ id: string; first_name: string; last_name: string; role: string; avatar_url?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [search,  setSearch]  = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    messageApi.listStaff()
      .then(setStaff)
      .catch(() => setStaff([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = staff.filter(s =>
    `${s.first_name} ${s.last_name}`.toLowerCase().includes(search.toLowerCase())
  );

  const selectedStaff = staff.find(s => s.id === selected);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-[16px] shadow-[0_20px_60px_rgba(0,0,0,0.15)]
                      w-[400px] flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-[20px] py-[16px]
                        border-b border-[#f1f5f9]">
          <h3 className="text-[#0f172a] text-[15px] font-bold tracking-[-0.3px]">
            New Conversation
          </h3>
          <button onClick={onClose}
                  className="text-[#94a3b8] hover:text-[#374151] transition p-[4px] rounded-[6px]
                             hover:bg-[#f1f5f9]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="px-[16px] pt-[14px] pb-[8px]">
          <div className="relative">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                 className="absolute left-[11px] top-1/2 -translate-y-1/2 text-[#94a3b8]">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <input
              autoFocus
              type="text"
              placeholder="Search HR or attorney..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-[#f8fafc] border border-[#f1f5f9] rounded-[10px]
                         pl-[34px] pr-[12px] py-[9px] text-[13px] text-[#0f172a]
                         placeholder:text-[#94a3b8] focus:outline-none
                         focus:border-[#3a46e5] focus:ring-1 focus:ring-[#3a46e5]/20 transition"
              style={{ fontFamily: "Inter, sans-serif" }}
            />
          </div>
        </div>

        {/* Staff list */}
        <div className="flex-1 overflow-y-auto max-h-[280px] px-[10px] pb-[10px]">
          {loading ? (
            <div className="flex items-center justify-center py-[32px]">
              <svg className="w-5 h-5 animate-spin text-[#3a46e5]" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-center text-[#94a3b8] text-[13px] py-[32px]">No staff found</p>
          ) : (
            filtered.map(s => (
              <button
                key={s.id}
                onClick={() => setSelected(selected === s.id ? null : s.id)}
                className={`w-full flex items-center gap-[12px] px-[10px] py-[10px]
                            rounded-[10px] transition text-left ${
                  selected === s.id
                    ? "bg-[#f0f5ff] border border-[#e5edff]"
                    : "hover:bg-[#f8fafc] border border-transparent"
                }`}
              >
                {/* Avatar */}
                <div className={`size-[36px] rounded-full flex items-center justify-center
                                  shrink-0 text-white text-[13px] font-semibold ${
                  s.role === "attorney" ? "bg-[#3a46e5]"
                  : s.role === "hr"     ? "bg-[#f59e0b]"
                  : "bg-[#10b981]"
                }`}>
                  {s.first_name[0]}{s.last_name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[#0f172a] text-[13px] font-semibold truncate">
                    {s.first_name} {s.last_name}
                  </p>
                  <p className="text-[#64748b] text-[11px] capitalize">{s.role}</p>
                </div>
                {selected === s.id && (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" fill="#3a46e5"/>
                    <path d="M8 12l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                )}
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-[16px] py-[14px] border-t border-[#f1f5f9] flex items-center gap-[10px]">
          <button onClick={onClose}
                  className="flex-1 h-[38px] rounded-[10px] border border-[#e2e8f0]
                             text-[#374151] text-[13px] font-medium hover:bg-[#f8fafc] transition">
            Cancel
          </button>
          <button
            disabled={!selected || isCreating}
            onClick={() => {
              if (!selected || !selectedStaff) return;
              onCreate(selected, `${selectedStaff.first_name} ${selectedStaff.last_name}`);
            }}
            className="flex-1 h-[38px] rounded-[10px] text-white text-[13px] font-semibold
                       hover:opacity-90 transition disabled:opacity-40"
            style={{ background: "linear-gradient(135deg, #3a46e5, #7c3aed)" }}
          >
            {isCreating ? "Starting…" : "Start Conversation"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
export default function SecureMessaging() {
  const { data: currentUser } = useCurrentUser();
  const {
    conversations,
    messages,
    activeConvId,
    setActiveConvId,
    sendMessage,
    createConversation,
    isLoading,
    isSending,
    isCreating,
    searchQuery,
    setSearchQuery,
    activeTab,
    setActiveTab,
  } = useMessages();

  const [inputText,    setInputText]    = useState("");
  const [attachFile,   setAttachFile]   = useState<File | null>(null);
  const [showNewConv,  setShowNewConv]  = useState(false);
  const messagesEndRef                  = useRef<HTMLDivElement>(null);
  const fileInputRef                    = useRef<HTMLInputElement>(null);
  const textareaRef                     = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  }, [inputText]);

  const activeConv = conversations.find(c => c.id === activeConvId);
  const myUserId   = currentUser?.id;

  // Group messages by date for separators
  const groupedMessages = messages.reduce<Array<{ type: "date"; label: string } | { type: "msg"; msg: Message }>>((acc, msg) => {
    const dateLabel = new Date(msg.created_at).toLocaleDateString("en-US", {
      weekday: "long", month: "long", day: "numeric",
    });
    const prev = acc.findLast(x => x.type === "date");
    if (!prev || (prev as any).label !== dateLabel) {
      acc.push({ type: "date", label: dateLabel });
    }
    acc.push({ type: "msg", msg });
    return acc;
  }, []);

  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text && !attachFile) return;
    if (!activeConvId) return;
    setInputText("");
    setAttachFile(null);
    await sendMessage({ conversationId: activeConvId, content: text, file: attachFile ?? undefined });
  }, [inputText, attachFile, activeConvId, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const filteredConvs = conversations.filter(c => {
    const matchSearch = !searchQuery || c.participant_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchTab    = activeTab === "all"
      ? true
      : activeTab === "unread"
      ? (c.unread_count ?? 0) > 0
      : c.is_archived;
    return matchSearch && matchTab;
  });

  const unreadCount = conversations.filter(c => (c.unread_count ?? 0) > 0).length;

  return (
    // ── Full page scroll wrapper ──────────────────────────────────────────────
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden" style={{ fontFamily: "Inter, sans-serif" }}>

      {/* ── Page header ── */}
      <header className="bg-white border-b border-[#f1f5f9] shrink-0
                         flex items-center justify-between
                         px-[24px] sm:px-[32px] h-[64px]">
        <h1 className="text-[#0f172a] text-[20px] font-bold tracking-[-0.5px]">
          Secure Messaging Center
        </h1>
        {/* Notification bell */}
        <button className="bg-white border border-[#e2e8f0] rounded-[10px]
                           flex items-center justify-center size-[40px] relative
                           hover:bg-[#f8fafc] transition">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"
              stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {unreadCount > 0 && (
            <span className="absolute top-[8px] right-[10px] bg-[#3a46e5] rounded-full size-[8px]" />
          )}
        </button>
      </header>

      {/* ── Main two-panel layout ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ══════════════════════════════════════════════════════════════════
            LEFT PANEL — Conversation list
        ══════════════════════════════════════════════════════════════════ */}
        <div className={`flex flex-col w-full sm:w-[300px] lg:w-[320px] shrink-0
                         border-r border-[#f1f5f9] bg-white
                         ${activeConvId ? "hidden sm:flex" : "flex"}`}>

          {/* Left header */}
          <div className="px-[16px] pt-[20px] pb-[12px] shrink-0">
            <div className="flex items-center justify-between mb-[16px]">
              <h2 className="text-[#0f172a] text-[16px] font-semibold tracking-[-0.4px]">
                Conversations
              </h2>
              <button
                onClick={() => setShowNewConv(true)}
                className="text-[#3a46e5] hover:bg-[#f0f5ff] rounded-[8px] p-[6px] transition"
                title="New conversation"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                   className="absolute left-[12px] top-1/2 -translate-y-1/2 text-[#94a3b8]">
                <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <input
                type="text"
                placeholder="Search messages..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-[#f8fafc] border border-[#f1f5f9] rounded-[10px]
                           pl-[36px] pr-[12px] py-[9px] text-[13px] text-[#0f172a]
                           placeholder:text-[#94a3b8] focus:outline-none
                           focus:border-[#3a46e5] focus:ring-1 focus:ring-[#3a46e5]/20 transition"
                style={{ fontFamily: "Inter, sans-serif" }}
              />
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-[4px] px-[16px] pb-[12px] shrink-0">
            {(["all", "unread", "archived"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-[6px] px-[12px] py-[6px] rounded-[8px]
                            text-[12px] font-medium capitalize transition ${
                  activeTab === tab
                    ? "bg-[#f0f5ff] text-[#3a46e5]"
                    : "text-[#64748b] hover:bg-[#f8fafc]"
                }`}
              >
                {tab}
                {tab === "all" && unreadCount > 0 && (
                  <span className="bg-[#3a46e5] text-white text-[10px] font-bold
                                   rounded-full min-w-[16px] h-[16px] flex items-center
                                   justify-center px-[4px]">
                    {unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto px-[8px] pb-[16px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-[48px]">
                <svg className="w-6 h-6 animate-spin text-[#3a46e5]" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              </div>
            ) : filteredConvs.length === 0 ? (
              <div className="flex flex-col items-center gap-[8px] py-[48px] px-[16px] text-center">
                <p className="text-[#64748b] text-[13px]">No conversations found</p>
              </div>
            ) : (
              filteredConvs.map(conv => (
                <ConvItem
                  key={conv.id}
                  conv={conv}
                  active={conv.id === activeConvId}
                  onClick={() => setActiveConvId(conv.id)}
                />
              ))
            )}
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            RIGHT PANEL — Chat window
        ══════════════════════════════════════════════════════════════════ */}
        <div className={`flex flex-col flex-1 min-w-0 bg-[#f8fafc]
                         ${!activeConvId ? "hidden sm:flex" : "flex"}`}>

          {!activeConvId ? (
            <EmptyChat />
          ) : (
            <>
              {/* Chat header */}
              <div className="bg-white border-b border-[#f1f5f9] shrink-0
                              flex items-center justify-between
                              px-[20px] sm:px-[24px] py-[14px]">
                <div className="flex items-center gap-[12px]">
                  {/* Back button — mobile only */}
                  <button
                    onClick={() => setActiveConvId(null)}
                    className="sm:hidden text-[#64748b] hover:text-[#0f172a] transition mr-[4px]"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M19 12H5M12 5l-7 7 7 7" stroke="currentColor"
                        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  <Avatar
                    src={activeConv?.avatar_url}
                    name={activeConv?.participant_name}
                    size={42}
                    online={activeConv?.is_online}
                  />
                  <div>
                    <p className="text-[#0f172a] text-[15px] font-semibold tracking-[-0.3px]">
                      {activeConv?.participant_name}
                    </p>
                    <p className="text-[12px] text-[#64748b] flex items-center gap-[5px]">
                      {activeConv?.is_online && (
                        <span className="inline-block w-[7px] h-[7px] bg-[#22c55e] rounded-full" />
                      )}
                      {activeConv?.is_online ? "Online" : "Offline"}
                      {activeConv?.participant_role && (
                        <> • {activeConv.participant_role}</>
                      )}
                    </p>
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-[6px]">
                  <button className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[10px]
                                     flex items-center justify-center size-[36px]
                                     hover:bg-[#f1f5f9] transition text-[#64748b]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8 19.79 19.79 0 01.01 2.18 2 2 0 012 .01h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92z"
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </button>
                  <button className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[10px]
                                     flex items-center justify-center size-[36px]
                                     hover:bg-[#f1f5f9] transition text-[#64748b]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M23 7l-7 5 7 5V7zM1 5a2 2 0 012-2h11a2 2 0 012 2v14a2 2 0 01-2 2H3a2 2 0 01-2-2V5z"
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  <button className="bg-[#f8fafc] border border-[#e2e8f0] rounded-[10px]
                                     flex items-center justify-center size-[36px]
                                     hover:bg-[#f1f5f9] transition text-[#64748b]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="5" r="1" fill="currentColor"/>
                      <circle cx="12" cy="12" r="1" fill="currentColor"/>
                      <circle cx="12" cy="19" r="1" fill="currentColor"/>
                    </svg>
                  </button>
                </div>
              </div>

              {/* Messages area */}
              <div className="flex-1 overflow-y-auto px-[16px] sm:px-[24px] py-[20px]">
                <div className="flex flex-col gap-[16px] max-w-[800px] mx-auto">
                  {groupedMessages.map((item, idx) => {
                    if (item.type === "date") {
                      return <DateSeparator key={`date-${idx}`} label={item.label} />;
                    }
                    const msg    = item.msg;
                    const isMine = msg.sender_id === myUserId;

                    // Check for call events
                    if (msg.message_type === "call_event") {
                      return (
                        <CallEvent
                          key={msg.id}
                          label={msg.content ?? "Call"}
                          time={fmtTime(msg.created_at)}
                        />
                      );
                    }

                    return (
                      <MessageBubble
                        key={msg.id}
                        msg={msg}
                        isMine={isMine}
                        senderAvatar={isMine ? undefined : activeConv?.avatar_url}
                        senderName={isMine ? undefined : activeConv?.participant_name}
                      />
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Compose bar */}
              <div className="bg-white border-t border-[#f1f5f9] shrink-0
                              px-[16px] sm:px-[20px] py-[14px]">
                {/* Attachment preview */}
                {attachFile && (
                  <div className="flex items-center gap-[10px] mb-[10px] px-[14px] py-[10px]
                                  bg-[#f0f5ff] border border-[#e5edff] rounded-[10px]">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
                        fill="#3a46e5"/>
                    </svg>
                    <span className="text-[13px] text-[#3a46e5] font-medium flex-1 truncate">
                      {attachFile.name}
                    </span>
                    <button onClick={() => setAttachFile(null)}
                            className="text-[#94a3b8] hover:text-[#ef4444] transition">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <path d="M18 6L6 18M6 6l12 12" stroke="currentColor"
                          strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                    </button>
                  </div>
                )}

                <div className="flex items-end gap-[10px]">
                  {/* Emoji */}
                  <button className="text-[#94a3b8] hover:text-[#64748b] transition shrink-0 mb-[2px]">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.8"/>
                      <path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="currentColor"
                        strokeWidth="1.8" strokeLinecap="round"/>
                      <circle cx="9" cy="10" r="1" fill="currentColor"/>
                      <circle cx="15" cy="10" r="1" fill="currentColor"/>
                    </svg>
                  </button>

                  {/* Attach */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[#94a3b8] hover:text-[#64748b] transition shrink-0 mb-[2px]"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
                        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={e => setAttachFile(e.target.files?.[0] ?? null)}
                  />

                  {/* Text input */}
                  <div className="flex-1 bg-[#f8fafc] border border-[#f1f5f9] rounded-[14px]
                                  focus-within:border-[#3a46e5] focus-within:ring-1
                                  focus-within:ring-[#3a46e5]/20 transition px-[14px] py-[10px]">
                    <textarea
                      ref={textareaRef}
                      rows={1}
                      value={inputText}
                      onChange={e => setInputText(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Type a message..."
                      className="w-full bg-transparent text-[14px] text-[#0f172a]
                                 placeholder:text-[#94a3b8] focus:outline-none resize-none
                                 leading-[22px] max-h-[120px] overflow-y-auto"
                      style={{ fontFamily: "Inter, sans-serif" }}
                    />
                  </div>

                  {/* Send */}
                  <button
                    onClick={handleSend}
                    disabled={isSending || (!inputText.trim() && !attachFile)}
                    className="shrink-0 size-[44px] rounded-[12px] flex items-center justify-center
                               text-white transition hover:opacity-90 disabled:opacity-40
                               shadow-[0px_4px_12px_rgba(58,70,229,0.3)]"
                    style={{ background: "linear-gradient(135deg, #3a46e5 0%, #7c3aed 100%)" }}
                  >
                    {isSending ? (
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
                          stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── New Conversation Modal ── */}
      {showNewConv && (
        <NewConvModal
          onClose={() => setShowNewConv(false)}
          isCreating={isCreating}
          onCreate={async (userId) => {
            await createConversation({
              thread_type:     "direct",
              participant_ids: [userId],
            });
            setShowNewConv(false);
          }}
        />
      )}
    </div>
  );
}