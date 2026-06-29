import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      port: 5174,
      allowedHosts: ['.ngrok-free.dev', '.ngrok-free.app'],
      proxy: {
        '/api': {
          target: env.VITE_PROXY_TARGET,
          changeOrigin: true,
          secure: false,
        },
        '/static': {
          target: 'https://helper-sheep-imminent.ngrok-free.dev/',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})