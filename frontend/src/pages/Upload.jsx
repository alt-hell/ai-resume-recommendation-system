import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HiOutlineCloudUpload, HiOutlineDocument, HiOutlineCheckCircle,
  HiOutlineLightBulb, HiOutlineExternalLink, HiOutlineAcademicCap,
  HiOutlineSparkles, HiOutlineShieldCheck, HiOutlineClock,
  HiOutlineChip, HiOutlineChevronRight, HiOutlineSearch,
  HiOutlineDatabase, HiOutlineLink, HiOutlineBeaker,
  HiOutlineTrendingUp,
} from 'react-icons/hi';
import { uploadResume } from '../api/client';
import SkillBadge from '../components/SkillBadge';
import './Upload.css';

const ANALYSIS_STAGES = [
  { label: 'Parsing document...', icon: <HiOutlineDocument /> },
  { label: 'Extracting skills (AI pipeline)...', icon: <HiOutlineChip /> },
  { label: 'Normalizing & categorizing...', icon: <HiOutlineSparkles /> },
  { label: 'Predicting domain fit...', icon: <HiOutlineLightBulb /> },
  { label: 'Building your profile...', icon: <HiOutlineShieldCheck /> },
];

const FEATURES = [
  { icon: HiOutlineSearch,    title: 'Smart Parsing',   desc: 'Supports PDF & DOCX with multi-strategy extraction' },
  { icon: HiOutlineChip,      title: 'AI Skill Detection', desc: 'LLM-powered skill identification from your resume' },
  { icon: HiOutlineTrendingUp,title: 'Role Prediction', desc: 'XGBoost ML predicts your ideal career role' },
  { icon: HiOutlineLightBulb, title: 'Gap Analysis',    desc: 'Find missing skills and get a learning roadmap' },
];

/* ─── 3-D Tilt Hook ─────────────────────────────────────────────────────── */
function useTilt(ref, strength = 14) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const onMove = (e) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width  - 0.5;
      const y = (e.clientY - r.top)  / r.height - 0.5;
      el.style.transform =
        `perspective(600px) rotateY(${x * strength}deg) rotateX(${-y * strength}deg) translateY(-4px)`;
    };
    const onLeave = () => { el.style.transform = ''; };

    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mousemove', onMove);
      el.removeEventListener('mouseleave', onLeave);
    };
  }, [ref, strength]);
}

/* ─── Tiltable wrapper component ────────────────────────────────────────── */
function TiltCard({ className, children, strength = 14, onClick, style }) {
  const ref = useRef(null);
  useTilt(ref, strength);
  return (
    <div ref={ref} className={className} onClick={onClick} style={style}>
      {children}
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────────────────────── */
export default function Upload() {
  const navigate = useNavigate();
  const [file,      setFile]      = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result,    setResult]    = useState(null);
  const [error,     setError]     = useState(null);
  const [stage,     setStage]     = useState(0);

  const handleUpload = useCallback(async (selectedFile) => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    setStage(0);

    const stageInterval = setInterval(() => {
      setStage((prev) => Math.min(prev + 1, ANALYSIS_STAGES.length - 1));
    }, 1500);

    try {
      const data = await uploadResume(selectedFile);
      setResult(data);
      sessionStorage.setItem('resumeData',   JSON.stringify(data));
      sessionStorage.setItem('resumeId',     data.resume_id);
      sessionStorage.removeItem('recommendationData');
      sessionStorage.removeItem('jobLinksData');
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
    } finally {
      clearInterval(stageInterval);
      setUploading(false);
    }
  }, []);

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setError(null);
    if (rejectedFiles.length > 0) {
      setError('Invalid file type. Please upload a PDF or DOCX file.');
      return;
    }
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      setFile(selectedFile);
      setResult(null);
      handleUpload(selectedFile);
    }
  }, [handleUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setStage(0);
  };

  return (
    <div className="upload-page page-enter" id="upload-page">


      <div className="upload-page__header">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <p className="upload-page__eyebrow"><HiOutlineSparkles /> AI-Powered Analysis</p>
          <h1>Upload Your <span className="gradient-text">Resume</span></h1>
          <p className="upload-page__subtitle">
            Drop your resume and get instant AI-powered skill extraction, role prediction, and career insights
          </p>
        </motion.div>
      </div>

      <AnimatePresence mode="wait">
        {uploading ? (
          /* ── Analyzing State ─────────────────────────────────────── */
          <motion.div
            key="loading"
            className="upload-analyzing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="upload-analyzing__card">
              <div className="upload-analyzing__file">
                <div className="upload-analyzing__file-icon-wrap">
                  <HiOutlineDocument className="upload-analyzing__file-icon" />
                  <div className="upload-analyzing__file-pulse" />
                </div>
                <div>
                  <p className="upload-analyzing__filename">{file?.name}</p>
                  <p className="upload-analyzing__filesize">
                    {file ? (file.size / 1024).toFixed(1) + ' KB' : ''}
                  </p>
                </div>
              </div>

              <div className="upload-analyzing__progress">
                <motion.div
                  className="upload-analyzing__progress-fill"
                  initial={{ width: '0%' }}
                  animate={{ width: `${((stage + 1) / ANALYSIS_STAGES.length) * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>

              <div className="upload-analyzing__stages">
                {ANALYSIS_STAGES.map((s, i) => (
                  <motion.div
                    key={s.label}
                    className={`upload-analyzing__stage ${i <= stage ? 'upload-analyzing__stage--active' : ''} ${i < stage ? 'upload-analyzing__stage--done' : ''}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    <div className="upload-analyzing__stage-dot">
                      {i < stage ? <HiOutlineCheckCircle /> : s.icon}
                    </div>
                    <span>{s.label}</span>
                    {i === stage && i < ANALYSIS_STAGES.length && (
                      <div className="upload-analyzing__stage-spinner" />
                    )}
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

        ) : result ? (
          /* ── Result State ───────────────────────────────────────── */
          <motion.div
            key="result"
            className="upload-result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {/* Success Header */}
            <div className="upload-result__header">
              <motion.div
                className="upload-result__success-icon"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 15 }}
              >
                <HiOutlineCheckCircle />
              </motion.div>
              <div>
                <h2>Resume Analyzed Successfully!</h2>
                <p className="upload-result__filename">
                  {result.filename} • {result.file_type?.toUpperCase()} •
                  Source: <strong>{result.extraction_source}</strong>
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="upload-result__stats">
              {[
                { value: result.total_skills,                                    label: 'Skills Found',    color: '#7c5cfc' },
                { value: `${(result.extraction_confidence * 100).toFixed(0)}%`, label: 'Confidence',      color: '#5eead4' },
                { value: `${(result.match_rate * 100).toFixed(0)}%`,            label: 'Match Rate',      color: '#a78bfa' },
                { value: result.unknown_skills?.length || 0,                     label: 'Unknown Skills',  color: '#fbbf24' },
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  className="upload-result__stat"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                >
                  <span className="upload-result__stat-value" style={{ color: stat.color }}>
                    {stat.value}
                  </span>
                  <span className="upload-result__stat-label">{stat.label}</span>
                </motion.div>
              ))}
            </div>

            {/* Normalized Skills */}
            <div className="upload-result__section">
              <h3>Extracted Skills ({result.normalized_skills?.length || 0})</h3>
              <div className="upload-result__skills">
                {result.normalized_skills?.map((skill, i) => (
                  <motion.div
                    key={skill}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 + i * 0.02 }}
                  >
                    <SkillBadge
                      skill={skill}
                      category={result.skill_categories?.[skill] || 'default'}
                    />
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Unknown Skills */}
            {result.unknown_skills?.length > 0 && (
              <div className="upload-result__section">
                <h3>Unrecognized Skills ({result.unknown_skills.length})</h3>
                <div className="upload-result__skills">
                  {result.unknown_skills.map((s) => (
                    <SkillBadge key={s} skill={s} category="default" />
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="upload-result__quick-actions">
              <h3>What's Next?</h3>
              <div className="upload-result__action-cards">
                {[
                  { icon: <HiOutlineLightBulb />,    title: 'Career Insights', desc: 'Role predictions & skill gap analysis', path: '/recommendations', accent: 'purple' },
                  { icon: <HiOutlineExternalLink />, title: 'Find Jobs',       desc: 'Top matching job listings',             path: '/job-links',       accent: 'teal'   },
                  { icon: <HiOutlineAcademicCap />,  title: 'Resume Coach',    desc: 'Get your resume scored & improved',     path: '/resume-coach',    accent: 'blue'   },
                  { icon: <HiOutlineSparkles />,     title: 'AI Advisor',      desc: 'Ask AI about your career path',         path: '/career-advisor',  accent: 'pink'   },
                ].map((action, i) => (
                  <motion.div
                    key={action.title}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + i * 0.1 }}
                  >
                    <TiltCard
                      className={`upload-action-card upload-action-card--${action.accent}`}
                      strength={10}
                      onClick={() => navigate(action.path)}
                    >
                      <div className={`upload-action-card__icon upload-action-card__icon--${action.accent}`}>
                        {action.icon}
                      </div>
                      <div>
                        <h4>{action.title}</h4>
                        <p>{action.desc}</p>
                      </div>
                      <HiOutlineChevronRight className="upload-action-card__arrow" />
                    </TiltCard>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Upload Another */}
            <div className="upload-result__footer">
              <button className="btn btn--ghost" onClick={handleReset} id="btn-upload-another">
                Upload Another Resume
              </button>
            </div>
          </motion.div>

        ) : (
          /* ── Dropzone State ─────────────────────────────────────── */
          <motion.div key="dropzone" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>

            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`upload-dropzone ${isDragActive ? 'upload-dropzone--active' : ''}`}
              id="dropzone"
            >
              <input {...getInputProps()} id="file-input" />
              <div className="upload-dropzone__content">
                <div className={`upload-dropzone__icon ${isDragActive ? 'animate-float' : ''}`}>
                  <HiOutlineCloudUpload />
                  <div className="upload-dropzone__icon-ring" />
                </div>
                {isDragActive ? (
                  <p className="upload-dropzone__text">Drop your resume here…</p>
                ) : (
                  <>
                    <p className="upload-dropzone__text">
                      Drag & drop your resume here, or <span className="upload-dropzone__browse">browse</span>
                    </p>
                    <p className="upload-dropzone__hint">
                      Supports PDF and DOCX • Max 10MB • Auto-analyzes on upload
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Error */}
            {error && (
              <motion.div className="upload-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <p>{error}</p>
              </motion.div>
            )}

            {/* Features Grid */}
            <div className="upload-features">
              <h3 className="upload-features__title">What Happens After Upload</h3>
              <div className="upload-features__grid">
                {FEATURES.map((f, i) => (
                  <motion.div
                    key={f.title}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + i * 0.1 }}
                  >
                    <TiltCard className="upload-feature-card" strength={14}>
                      <motion.div
                        className="upload-feature-card__icon"
                        animate={{ rotate: [0, -10, 10, -10, 0] }}
                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.5 }}
                      >
                        <f.icon />
                      </motion.div>
                      <h4>{f.title}</h4>
                      <p>{f.desc}</p>
                    </TiltCard>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Trust badges */}
            <div className="upload-trust">
              <div className="upload-trust__item"><HiOutlineShieldCheck /> Secure Processing</div>
              <div className="upload-trust__item"><HiOutlineClock /> 10-Second Analysis</div>
              <div className="upload-trust__item"><HiOutlineChip /> AI-Powered</div>
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}