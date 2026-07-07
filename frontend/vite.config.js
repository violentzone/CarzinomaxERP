import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// The dev server proxies `/api` to the FastAPI backend so the SPA can call the
// API same-origin (avoids hardcoding the backend host and any CORS surprises).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
