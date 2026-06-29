// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { MsalProvider } from '@azure/msal-react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { msalInstance } from './lib/sso'
import './index.css'

import App from './App.tsx'

// ─────────────────────────────────────────────────────────────────────────────
// React Query client — singleton for the entire app
// ─────────────────────────────────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,         // Data considered fresh for 1 minute
      gcTime: 5 * 60 * 1000,        // Cache garbage-collected after 5 minutes
      refetchOnWindowFocus: false,  // Don't refetch when tab refocuses
      retry: 1,                     // Retry failed queries once
    },
    mutations: {
      retry: 0,                     // Don't retry mutations on failure
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
        <MsalProvider instance={msalInstance}>
          <App />
        </MsalProvider>
      </GoogleOAuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)