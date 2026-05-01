import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineExternalLink, HiOutlineBriefcase, HiOutlineLocationMarker,
  HiOutlineClock, HiOutlineExclamationCircle, HiOutlineRefresh,
  HiOutlineArrowRight,
} from 'react-icons/hi';
import { getJobLinks } from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import './JobLinks.css';

const PLATFORM_CONFIG = {
  LinkedIn:       { color: '#0A66C2', letter: 'Li', gradient: 'linear-gradient(135deg, #0A66C2, #004182)' },
  Indeed:         { color: '#2164F3', letter: 'In', gradient: 'linear-gradient(135deg, #2164F3, #003399)' },
  Naukri:         { color: '#4A90D9', letter: 'Nk', gradient: 'linear-gradient(135deg, #4A90D9, #1E5799)' },
  Glassdoor:      { color: '#0CAA41', letter: 'Gd', gradient: 'linear-gradient(135deg, #0CAA41, #006622)' },
  'Google Jobs':  { color: '#4285F4', letter: 'GJ', gradient: 'linear-gradient(135deg, #4285F4, #1A73E8)' },
  ZipRecruiter:   { color: '#3B9B5D', letter: 'ZR', gradient: 'linear-gradient(135deg, #3B9B5D, #27663C)' },
  Monster:        { color: '#6E45A5', letter: 'Mo', gradient: 'linear-gradient(135deg, #6E45A5, #4A2D6E)' },
  Dice:           { color: '#EB1C26', letter: 'Di', gradient: 'linear-gradient(135deg, #EB1C26, #A3141A)' },
  'Job Board':    { color: '#7c5cfc', letter: 'JB', gradient: 'linear-gradient(135deg, #7c5cfc, #5e3fbf)' },
};

function getPlatformConfig(platform) {
  return PLATFORM_CONFIG[platform] || PLATFORM_CONFIG['Job Board'];
}

/**
 * Reads resume_id from every possible storage location the Upload page
 * might have used.  Returns the first truthy value found.
 */
function resolveResumeId() {
  // Try every key variant the upload flow could have used
  const candidates = [
    sessionStorage.getItem('resumeId'),
    sessionStorage.getItem('resume_id'),
    localStorage.getItem('resumeId'),
    localStorage.getItem('resume_id'),
  ];

  // Also check if it was stored as part of a JSON object
  try {
    const uploadData = sessionStorage.getItem('uploadData') || localStorage.getItem('uploadData');
    if (uploadData) {
      const parsed = JSON.parse(uploadData);
      candidates.push(parsed?.resume_id, parsed?.resumeId, parsed?.id);
    }
  } catch (_) { /* ignore parse errors */ }

  try {
    const resumeData = sessionStorage.getItem('resumeData') || localStorage.getItem('resumeData');
    if (resumeData) {
      const parsed = JSON.parse(resumeData);
      candidates.push(parsed?.resume_id, parsed?.resumeId, parsed?.id);
    }
  } catch (_) { /* ignore parse errors */ }

  return candidates.find(Boolean) || null;
}

export default function JobLinks() {
  const navigate = useNavigate();

  const [resumeId, setResumeId]   = useState(() => resolveResumeId());
  const [data,     setData]       = useState(() => {
    try {
      const saved = sessionStorage.getItem('jobLinksData');
      return saved ? JSON.parse(saved) : null;
    } catch (_) { return null; }
  });
  const [loading,  setLoading]    = useState(false);
  const [error,    setError]      = useState(null);

  /* ── fetch ─────────────────────────────────────────────────────────── */
  const fetchJobLinks = async (id = resumeId) => {
    if (!id) return;
    setLoading(true);
    setError(null);

    try {
      const result = await getJobLinks(id);
      setData(result);
      sessionStorage.setItem('jobLinksData', JSON.stringify(result));
    } catch (err) {
      const status  = err.status  ?? err.response?.status;
      const message = err.message ?? err.response?.data?.detail ?? 'Failed to load jobs';

      if (status === 404) {
        // Resume not found on server — clear stale cache but keep a helpful error
        // instead of silently wiping the UI back to "No Resume Uploaded"
        sessionStorage.removeItem('jobLinksData');
        setData(null);
        setError(
          'Your session has expired or the resume was not found on the server. ' +
          'Please re-upload your resume.'
        );
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  /* ── auto-fetch when resumeId is available but data is missing ──── */
  useEffect(() => {
    if (resumeId && !data) {
      fetchJobLinks(resumeId);
    }
  }, [resumeId]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── No resume in storage at all ─────────────────────────────────── */
  if (!resumeId) {
    return (
      <div className="joblinks-page page-enter">
        <div className="joblinks-empty">
          <div className="joblinks-empty__icon"><HiOutlineBriefcase /></div>
          <h2>No Resume Uploaded</h2>
          <p>Upload your resume first to discover matching job opportunities.</p>
          <button className="btn btn--primary" onClick={() => navigate('/upload')}>
            Upload Resume
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="joblinks-page page-enter">
        <LoadingSpinner message="Finding the best job matches for your profile…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="joblinks-page page-enter">
        <div className="joblinks-empty">
          <div className="joblinks-empty__icon joblinks-empty__icon--error">
            <HiOutlineExclamationCircle />
          </div>
          <h2>Failed to load jobs</h2>
          <p>{error}</p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn--ghost"    onClick={() => fetchJobLinks()}>
              <HiOutlineRefresh /> Retry
            </button>
            <button className="btn btn--primary"  onClick={() => navigate('/upload')}>
              Re-upload Resume
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="joblinks-page page-enter">
        <LoadingSpinner message="Loading job opportunities…" />
      </div>
    );
  }

  /* ── Main render ─────────────────────────────────────────────────── */
  return (
    <div className="joblinks-page page-enter">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>

        {/* Header */}
        <div className="joblinks-page__header">
          <h1>Top Job <span className="gradient-text">Matches</span></h1>
          <p>
            {data.total_found > 0 ? (
              <span>
                Found <strong>{data.total_found}+</strong> openings for{' '}
                <strong>{data.predicted_role}</strong>
              </span>
            ) : (
              <span>Job links for <strong>{data.predicted_role}</strong></span>
            )}
          </p>
        </div>

        {/* Job Cards */}
        <div className="joblinks-grid">
          {data.jobs?.map((job, i) => {
            const platform = getPlatformConfig(job.platform);
            const applyUrl =
              job.apply_url ||
              job.job_apply_link ||
              (Array.isArray(job.apply_options) && job.apply_options[0]?.link) ||
              null;

            return (
              <motion.div
                key={i}
                className="job-card"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
              >
                <div className="job-card__accent" style={{ background: platform.gradient }} />

                <div className="job-card__content">
                  <div className="job-card__header">
                    <div
                      className="job-card__platform-icon"
                      style={{ background: platform.gradient }}
                    >
                      <span className="job-card__platform-letter">{platform.letter}</span>
                    </div>
                    <span style={{ color: platform.color }}>{job.platform}</span>
                  </div>

                  <h3>{job.job_title}</h3>
                  <p className="job-card__company">{job.company}</p>

                  {job.location && (
                    <p className="job-card__meta">
                      <HiOutlineLocationMarker /> {job.location}
                    </p>
                  )}

                  {(job.posted_date || job.job_type) && (
                    <p className="job-card__meta">
                      <HiOutlineClock />
                      {[job.job_type, job.posted_date].filter(Boolean).join(' · ')}
                    </p>
                  )}

                  {job.description_snippet && (
                    <p className="job-card__snippet">{job.description_snippet}</p>
                  )}

                  {applyUrl ? (
                    <a
                      href={applyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="job-card__apply-btn"
                      style={{ background: platform.gradient }}
                    >
                      Apply Now <HiOutlineExternalLink />
                    </a>
                  ) : (
                    <span className="job-card__no-link">Link unavailable</span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Actions */}
        <div className="joblinks-actions">
          <button className="btn btn--ghost" onClick={() => fetchJobLinks()}>
            <HiOutlineRefresh /> Refresh Jobs
          </button>
          <button className="btn btn--primary" onClick={() => navigate('/resume-coach')}>
            Improve Resume <HiOutlineArrowRight />
          </button>
        </div>

      </motion.div>
    </div>
  );
}