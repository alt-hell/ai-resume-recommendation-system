/**
 * DEBUGGING HELPER — paste this in your browser console after uploading a resume
 * to see exactly what key your Upload page uses in storage.
 *
 * Run this in DevTools → Console:
 *
 *   Object.keys(sessionStorage).forEach(k => console.log(k, sessionStorage.getItem(k)));
 *   Object.keys(localStorage).forEach(k => console.log(k, localStorage.getItem(k)));
 */

/**
 * API Client — Axios instance for communicating with the FastAPI backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Accept': 'application/json' },
});

// ── Response interceptor ─────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      error.message ||
      'An unexpected error occurred';
    console.error('[API Error]', message);
    return Promise.reject({ message, status: error.response?.status });
  }
);

// ── API Functions ────────────────────────────────────────────────────────

/** Upload a resume file (PDF/DOCX) */
export async function uploadResume(file) {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  });

  // ── Persist resume_id in BOTH storage locations so all pages can find it ──
  const resumeId = data?.resume_id ?? data?.id ?? data?.resumeId;
  if (resumeId) {
    sessionStorage.setItem('resumeId', resumeId);   // canonical key
    sessionStorage.setItem('resume_id', resumeId);  // alternate key
    localStorage.setItem('resumeId', resumeId);     // survives page refresh
    localStorage.setItem('resume_id', resumeId);
  }

  return data;
}

/** Get role recommendations for a resume */
export async function getRecommendation(resumeId) {
  const { data } = await api.get(`/recommend/${resumeId}`);
  return data;
}

/** Get top 5 job application links for a resume */
export async function getJobLinks(resumeId) {
  const { data } = await api.get(`/job-links/${resumeId}`);
  return data;
}

/** Get personalized resume coaching */
export async function getResumeCoach(resumeId) {
  const { data } = await api.get(`/resume-coach/${resumeId}`);
  return data;
}

/** Ask the AI Career Advisor a question */
export async function askCareerAdvisor(resumeId, question) {
  const { data } = await api.post('/career-advisor', {
    resume_id: resumeId || null,
    question,
  });
  return data;
}

/** Get suggested career advisor prompts */
export async function getCareerPrompts() {
  const { data } = await api.get('/career-advisor/prompts');
  return data;
}

/** Get skill demand trends */
export async function getSkillTrends(topN = 30, category = null) {
  const params = { top_n: topN };
  if (category) params.category = category;
  const { data } = await api.get('/trends', { params });
  return data;
}

/** Get trending skills for a specific role */
export async function getRoleTrends(roleName, topN = 10) {
  const { data } = await api.get(`/trends/role/${encodeURIComponent(roleName)}`, {
    params: { top_n: topN },
  });
  return data;
}

/** Health check */
export async function healthCheck() {
  const { data } = await api.get('/health');
  return data;
}

export default api;