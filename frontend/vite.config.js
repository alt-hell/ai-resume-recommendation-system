import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload':         'http://localhost:8000',
      '/extract-skills': 'http://localhost:8000',
      '/recommend':      'http://localhost:8000',
      '/career-path':    'http://localhost:8000',
      '/resume-coach':   'http://localhost:8000',
      '/trends':         'http://localhost:8000',
      '/health':         'http://localhost:8000',
      '/job-links':      'http://localhost:8000',
      '/career-advisor': 'http://localhost:8000',
    },
  },
})
