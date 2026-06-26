import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/players': 'http://127.0.0.1:8000',
      '/compare': 'http://127.0.0.1:8000',
    },
  },
})
