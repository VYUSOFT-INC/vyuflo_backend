import api from './axios';

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
  read: boolean;
}

export interface Conversation {
  id: string;
  participants: Array<{ id: string; name: string; role: string; avatar?: string }>;
  last_message?: Message;
  unread_count: number;
  updated_at: string;
}

export const getConversations = () =>
  api.get<{ data: Conversation[] }>('/messages/conversations');

export const getMessages = (conversationId: string, params?: Record<string, string | number>) =>
  api.get<{ data: Message[] }>(`/messages/conversations/${conversationId}`, { params });

export const sendMessage = (conversationId: string, content: string) =>
  api.post<Message>(`/messages/conversations/${conversationId}`, { content });

export const createConversation = (participantIds: string[]) =>
  api.post<Conversation>('/messages/conversations', { participant_ids: participantIds });
