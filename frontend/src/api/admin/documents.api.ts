import api from './axios';

export interface Document {
  id: string;
  name: string;
  category: string;
  status: string;
  file_size: string;
  mime_type: string;
  case_id?: string;
  uploaded_at: string;
  url?: string;
}

export const getDocuments = (params?: Record<string, string | number>) =>
  api.get<{ data: Document[]; total: number }>('/documents', { params });

export const getDocument = (id: string) =>
  api.get<Document>(`/documents/${id}`);

export const uploadDocument = (formData: FormData) =>
  api.post<Document>('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const updateDocument = (id: string, data: Partial<Document>) =>
  api.put<Document>(`/documents/${id}`, data);

export const deleteDocument = (id: string) =>
  api.delete(`/documents/${id}`);
