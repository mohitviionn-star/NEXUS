import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180, // NEXUS web dev port (kept clear of the default 5173)
    strictPort: false, // if 5180 is also busy, fall through to the next free port
  },
})
