import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { HiOutlineCloudUpload, HiOutlineLightBulb, HiOutlineExternalLink, HiOutlineAcademicCap, HiOutlineChevronRight, HiOutlineSparkles, HiOutlineChip, HiOutlineShieldCheck, HiOutlineTrendingUp, HiOutlineCube } from 'react-icons/hi';
import './Dashboard.css';

const features = [
  {
    icon: <HiOutlineCloudUpload />,
    title: 'Upload Resume',
    desc: 'Upload your resume and get instant AI-powered skill extraction with deep, intelligent analysis—built to elevate your career with TheCorrelation.',
    path: '/upload',
    accent: 'primary',
  },
  {
    icon: <HiOutlineLightBulb />,
    title: 'Career Insights',
    desc: 'Predict your best-matching role, identify skill gaps, and get a personalized learning path.',
    path: '/recommendations',
    accent: 'secondary',
  },
  {
    icon: <HiOutlineExternalLink />,
    title: 'Find Jobs',
    desc: 'Discover top matching job listings from LinkedIn, Indeed, Naukri, and more platforms.',
    path: '/job-links',
    accent: 'warm',
  },
  {
    icon: <HiOutlineAcademicCap />,
    title: 'Resume Coach',
    desc: 'Get your resume scored, improvement tips, project suggestions, and a perfect resume blueprint.',
    path: '/resume-coach',
    accent: 'info',
  },
];

const stats = [
  { value: 15, suffix: '+', label: 'Roles Predicted', icon: <HiOutlineTrendingUp /> },
  { value: 500, suffix: '+', label: 'Skills Tracked', icon: <HiOutlineCube /> },
  { value: 95, suffix: '%', label: 'Accuracy Rate', icon: <HiOutlineShieldCheck /> },
  { value: 6, suffix: '', label: 'Job Platforms', icon: <HiOutlineExternalLink /> },
];

const techStack = [
  { name: 'XGBoost', desc: 'Role prediction' },
  { name: 'NLP Pipeline', desc: 'Skill extraction' },
  { name: 'AI Insights', desc: 'Career guidance' },
  { name: 'Multi-Platform', desc: 'Job matching' },
];

function AnimatedCounter({ value, suffix = '', duration = 2 }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const end = value;
    const totalSteps = 60;
    const stepDuration = (duration * 1000) / totalSteps;
    const increment = end / totalSteps;
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, stepDuration);
    return () => clearInterval(timer);
  }, [value, duration]);
  return <>{count}{suffix}</>;
}

const stagger = {
  container: { transition: { staggerChildren: 0.12 } },
  item: {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
  },
};

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <motion.div 
      className="dashboard" 
      id="dashboard-page"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.4 }}
    >      {/* Hero Section */}
      <section className="dashboard__hero">
        <div className="dashboard__hero-glow" />
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <p className="dashboard__hero-eyebrow">
            <HiOutlineSparkles /> AI-Powered Career Intelligence
          </p>
          <h1 className="dashboard__hero-title">
            Transform Your <span className="gradient-text">Resume</span> Into
            <br />Actionable Career Insights
          </h1>
          <p className="dashboard__hero-subtitle">
            Upload your resume and let our model extract skills, predict your ideal role,
            identify gaps, and find matching jobs — all in seconds.
          </p>
          <div className="dashboard__hero-actions">
            <button
              className="btn btn--primary btn--lg"
              onClick={() => navigate('/upload')}
              id="cta-upload"
            >
              <HiOutlineCloudUpload />
              Upload Resume
            </button>
            <button
              className="btn btn--ghost btn--lg"
              onClick={() => navigate('/career-advisor')}
              id="cta-advisor"
            >
              <HiOutlineSparkles />
              AI Career Advisor
              <HiOutlineChevronRight />
            </button>
          </div>
        </motion.div>
      </section>

      {/* Stats Counter Section */}
      <motion.section
        className="dashboard__stats"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.6 }}
      >
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            className="dashboard__stat-card"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 + i * 0.1 }}
          >
            <div className="dashboard__stat-icon">{s.icon}</div>
            <span className="dashboard__stat-value">
              <AnimatedCounter value={s.value} suffix={s.suffix} />
            </span>
            <span className="dashboard__stat-label">{s.label}</span>
          </motion.div>
        ))}
      </motion.section>

      {/* Features Grid */}
      <motion.section
        className="dashboard__features"
        variants={stagger.container}
        initial="hidden"
        animate="visible"
      >
        <h2 className="dashboard__section-title">How It Works</h2>
        <div className="section-divider section-divider--center" />
        <div className="dashboard__features-grid">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              className={`dashboard__feature-card dashboard__feature-card--${f.accent}`}
              variants={stagger.item}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              onClick={() => navigate(f.path)}
              id={`feature-${f.accent}`}
            >
              <div className="dashboard__feature-step">{String(i + 1).padStart(2, '0')}</div>
              <div className="dashboard__feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
              <span className="dashboard__feature-link">
                Get Started <HiOutlineChevronRight />
              </span>
            </motion.div>
          ))}
        </div>
      </motion.section>

      {/* AI Advisor CTA Banner */}
      <motion.section
        className="dashboard__advisor-cta"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <div className="dashboard__advisor-cta-glow" />
        <div className="dashboard__advisor-cta-content">
          <div className="dashboard__advisor-cta-badge">
            <HiOutlineSparkles /> NEW FEATURE
          </div>
          <h2>AI Career Advisor</h2>
          <p>Ask our AI anything about career transitions, learning paths, certifications, and salary expectations. Powered by advanced language models.</p>
          <button className="btn btn--teal btn--lg" onClick={() => navigate('/career-advisor')}>
            Try AI Advisor <HiOutlineChevronRight />
          </button>
        </div>
        <div className="dashboard__advisor-cta-visual">
          <div className="dashboard__advisor-orb dashboard__advisor-orb--1" />
          <div className="dashboard__advisor-orb dashboard__advisor-orb--2" />
          <div className="dashboard__advisor-orb dashboard__advisor-orb--3" />
          <HiOutlineChip className="dashboard__advisor-chip-icon" />
        </div>
      </motion.section>

      {/* Pipeline */}
      <section className="dashboard__pipeline">
        <h2 className="dashboard__section-title">The Pipeline</h2>
        <div className="section-divider section-divider--center" />
        <div className="dashboard__pipeline-steps">
          {['Upload PDF/DOCX', 'Parse & Clean', 'Extract Skills', 'Normalize & Categorize', 'Predict Role', 'Find Jobs'].map((step, i) => (
            <motion.div
              key={step}
              className="dashboard__pipeline-step"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              <div className="dashboard__pipeline-number">{i + 1}</div>
              <span>{step}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Tech Stack Showcase */}
      <motion.section
        className="dashboard__tech"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        <div className="dashboard__tech-strip">
          {techStack.map((t, i) => (
            <div key={i} className="dashboard__tech-item">
              <span className="dashboard__tech-name">{t.name}</span>
              <span className="dashboard__tech-desc">{t.desc}</span>
            </div>
          ))}
        </div>
      </motion.section>
    </motion.div>
  );
}
