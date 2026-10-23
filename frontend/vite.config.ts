/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Django dev server; the browser only ever talks to the Vite origin, so no CORS is needed.
  server: { proxy: { '/api': 'http://127.0.0.1:8010' } },
  test: { environment: 'node' },
})
