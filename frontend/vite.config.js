import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload':         'https://ai-resume-recommendation-system.onrender.com',
      '/extract-skills': 'https://ai-resume-recommendation-system.onrender.com',
      '/recommend':      'https://ai-resume-recommendation-system.onrender.com',
      '/career-path':    'https://ai-resume-recommendation-system.onrender.com',
      '/resume-coach':   'https://ai-resume-recommendation-system.onrender.com',
      '/trends':         'https://ai-resume-recommendation-system.onrender.com',
      '/health':         'https://ai-resume-recommendation-system.onrender.com',
      '/job-links':      'https://ai-resume-recommendation-system.onrender.com',
      '/career-advisor': 'https://ai-resume-recommendation-system.onrender.com',
    },
  },
})
