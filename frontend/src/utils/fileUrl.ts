// // src/utils/fileUrl.ts
// export const getFileUrl = (path: string | null | undefined): string | null => {
//   if (!path) return null;

//   // Already a full URL (S3, CDN, http) — return as-is
//   if (path.startsWith("http://") || path.startsWith("https://")) return path;

//   // Strip /api/v1 from base — static files are mounted at root /static, not under /api/v1
//   const base = (import.meta.env.VITE_API_BASE_URL as string ?? '').replace('/api/v1', '');

//   return `${base}/static/${path.replace(/^uploads\//, '')}`;
// };  

export const getFileUrl = (path: string | null | undefined): string | null => {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `/static/${path.replace(/^uploads\//, '')}`;
};