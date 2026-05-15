import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Bypass function: skip proxy for browser page navigations (HTML requests),
// only proxy actual API calls (fetch/XHR with JSON accept headers).
const bypassHtml = (req) => {
  if (req.headers.accept?.includes('text/html')) {
    return req.url;  // Return URL = skip proxy, let Vite serve index.html
  }
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload':         { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/extract-skills': { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/recommend':      { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/career-path':    { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/resume-coach':   { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/trends':         { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/health':         { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/job-links':      { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
      '/career-advisor': { target: 'https://ai-resume-recommendation-system.onrender.com', changeOrigin: true, bypass: bypassHtml },
    },
  },
})
