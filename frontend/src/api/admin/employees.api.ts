import api from './axios';

export interface Employee {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export const getEmployees = (params?: Record<string, string | number>) =>
  api.get<{ data: Employee[]; total: number }>('/employees', { params });

export const getEmployee = (id: string) =>
  api.get<Employee>(`/employees/${id}`);

export const createEmployee = (data: Partial<Employee>) =>
  api.post<Employee>('/employees', data);

export const updateEmployee = (id: string, data: Partial<Employee>) =>
  api.put<Employee>(`/employees/${id}`, data);

export const deleteEmployee = (id: string) =>
  api.delete(`/employees/${id}`);
