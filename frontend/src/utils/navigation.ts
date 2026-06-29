// src/utils/navigation.ts

export function getDashboardRoute(role: string): string {
  switch (role) {
    case 'employee':  return '/dashboard';
    case 'hr':        return '/employer/dashboard';
    case 'attorney':  return '/lawyer/intake';
    case 'app_admin': return '/admin/dashboard';
    default:          return '/dashboard';
  }
}