import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// The dev server proxies `/api` to the FastAPI backend so the SPA can call the
// API same-origin (avoids hardcoding the backend host and any CORS surprises).
// The backend port comes from BACKEND_PORT in the repo-root .env (the one
// docker-compose.yml reads) or the shell, so both follow the same setting.
export default defineConfig(({ mode }) => {
  const rootDir = fileURLToPath(new URL('..', import.meta.url))
  const rootEnv = loadEnv(mode, rootDir, '')
  const backendPort = rootEnv.BACKEND_PORT || '8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
