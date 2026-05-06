import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineLightBulb, HiOutlineAcademicCap, HiOutlineBriefcase,
  HiOutlineChevronRight, HiOutlineExclamationCircle, HiOutlineStar,
  HiOutlineClock, HiOutlineCheckCircle, HiOutlineSparkles, HiOutlineQuestionMarkCircle,
  HiOutlineExternalLink, HiOutlineTrendingUp, HiOutlineCurrencyRupee, HiOutlinePlay,
  HiOutlineChip, HiOutlineBeaker, HiOutlineChartBar, HiOutlineShieldCheck,
  HiOutlineUserGroup, HiOutlineGlobe,
} from 'react-icons/hi';
import { getRecommendation } from '../api/client';
import SkillBadge from '../components/SkillBadge';
import StatsCard from '../components/StatsCard';
import LoadingSpinner from '../components/LoadingSpinner';
import './Recommendations.css';

/* ── Icon type mapping (backend sends icon_type strings) ───────────────── */
const ICON_MAP = {
  chart: <HiOutlineChartBar />,
  briefcase: <HiOutlineBriefcase />,
  beaker: <HiOutlineBeaker />,
  chip: <HiOutlineChip />,
  academic: <HiOutlineAcademicCap />,
  globe: <HiOutlineGlobe />,
};

function getIconForType(iconType) {
  return ICON_MAP[iconType] || <HiOutlineAcademicCap />;
}

/* ── YouTube Button ────────────────────────────────────────────────────── */
function YouTubeButton({ skill }) {
  const url = `https://www.youtube.com/results?search_query=Learn+${encodeURIComponent(skill)}+tutorial+2025`;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn--youtube" title={`Learn ${skill} on YouTube`}>
      <HiOutlinePlay /> YouTube
    </a>
  );
}

/* ── Role Confidence Bar ───────────────────────────────────────────────── */
function RoleConfidenceBar({ role, confidence, rank }) {
  const pct = (confidence * 100).toFixed(1);
  const colors = ['#7c5cfc', '#5eead4', '#a78bfa'];
  return (
    <div className="role-bar">
      <div className="role-bar__header">
        <span className="role-bar__rank">#{rank}</span>
        <span className="role-bar__name">{role}</span>
        <span className="role-bar__pct" style={{ color: colors[rank - 1] || '#a0a0b8' }}>{pct}%</span>
      </div>
      <div className="role-bar__track">
        <motion.div
          className="role-bar__fill"
          style={{ background: colors[rank - 1] || '#a0a0b8' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, delay: rank * 0.2 }}
        />
      </div>
    </div>
  );
}

/* ── Course Showcase (No-Skills Users) ─────────────────────────────────── */
function CourseShowcase({ courses }) {
  const ACCENT_COLORS = [
    { gradient: 'linear-gradient(135deg, #7c5cfc, #a78bfa)', glow: 'rgba(124,92,252,0.15)' },
    { gradient: 'linear-gradient(135deg, #5eead4, #34d399)', glow: 'rgba(94,234,212,0.15)' },
    { gradient: 'linear-gradient(135deg, #f472b6, #ec4899)', glow: 'rgba(244,114,182,0.15)' },
    { gradient: 'linear-gradient(135deg, #fbbf24, #f59e0b)', glow: 'rgba(251,191,36,0.15)' },
  ];

  return (
    <motion.section
      className="course-showcase"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
    >
      <div className="course-showcase__header">
        <div className="course-showcase__badge">
          <HiOutlineAcademicCap /> RECOMMENDED PROGRAMS
        </div>
        <h2>Accelerate Your Career With <span className="gradient-text">TheCorrelation</span></h2>
        <p>
          Industry-leading programs designed to take you from beginner to job-ready.
          Each program includes mentorship, projects, and placement support.
        </p>
      </div>

      <div className="course-showcase__grid">
        {courses.map((course, i) => {
          const accent = ACCENT_COLORS[i % ACCENT_COLORS.length];
          return (
            <motion.div
              key={course.title}
              className="course-card"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.12, duration: 0.5 }}
              whileHover={{ y: -8, transition: { duration: 0.25 } }}
            >
              <div className="course-card__accent" style={{ background: accent.gradient }} />

              {/* Header */}
              <div className="course-card__header">
                <div className="course-card__icon" style={{ background: accent.glow }}>
                  {getIconForType(course.icon_type)}
                </div>
                <div className="course-card__meta">
                  <span className="course-card__provider">
                    <HiOutlineShieldCheck /> {course.provider}
                  </span>
                  <span className="course-card__duration">
                    <HiOutlineClock /> {course.duration}
                  </span>
                </div>
              </div>

              <h3 className="course-card__title">{course.title}</h3>
              <p className="course-card__desc">{course.description}</p>

              {/* Benefits */}
              <div className="course-card__benefits">
                <h4>Program Benefits</h4>
                <ul>
                  {course.benefits.map((benefit, j) => (
                    <motion.li
                      key={j}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + i * 0.12 + j * 0.08 }}
                    >
                      <HiOutlineCheckCircle className="course-card__benefit-icon" />
                      <span>{benefit}</span>
                    </motion.li>
                  ))}
                </ul>
              </div>

              {/* Skills */}
              <div className="course-card__skills">
                <h4>Skills You Will Learn</h4>
                <div className="course-card__skill-tags">
                  {course.skills_covered.map(s => (
                    <span key={s} className="course-card__skill-tag">{s}</span>
                  ))}
                </div>
              </div>

              {/* Career Outcomes */}
              {course.career_outcomes && (
                <div className="course-card__outcomes">
                  <div className="course-card__outcome-item">
                    <HiOutlineCurrencyRupee />
                    <span>{course.career_outcomes.salary_range}</span>
                  </div>
                  <div className="course-card__outcome-item">
                    <HiOutlineUserGroup />
                    <span>{course.career_outcomes.roles.join(', ')}</span>
                  </div>
                </div>
              )}

              {/* CTA */}
              <a
                href={course.url}
                target="_blank"
                rel="noopener noreferrer"
                className="course-card__cta"
                style={{ background: accent.gradient }}
              >
                Explore Program <HiOutlineChevronRight />
              </a>
            </motion.div>
          );
        })}
      </div>

      <motion.div
        className="course-showcase__footer"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
      >
        <a
          href="https://thecorrelation.in"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn--primary btn--lg"
        >
          <HiOutlineGlobe /> Visit TheCorrelation <HiOutlineChevronRight />
        </a>
      </motion.div>
    </motion.section>
  );
}

export default function Recommendations() {
  const navigate = useNavigate();
  
  const [data, setData] = useState(() => {
    const saved = sessionStorage.getItem('recommendationData');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const resumeId = sessionStorage.getItem('resumeId');

  const fetchRecommendation = async () => {
    if (!resumeId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRecommendation(resumeId);
      setData(result);
      sessionStorage.setItem('recommendationData', JSON.stringify(result));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId && !data && !loading) {
      fetchRecommendation();
    }
  }, [resumeId]);

  if (!resumeId) {
    return (
      <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <div className="recommendations-empty">
          <div className="recommendations-empty__icon"><HiOutlineBriefcase /></div>
          <h2>No Resume Uploaded Yet</h2>
          <p>Upload your resume first to get personalized career recommendations.</p>
          <button className="btn btn--primary" onClick={() => navigate('/upload')} id="btn-go-upload">
            Upload Resume
          </button>
        </div>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <LoadingSpinner message="Analyzing domain fit and formulating advanced career insights..." />
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <div className="recommendations-empty">
          <div className="recommendations-empty__icon recommendations-empty__icon--error">
            <HiOutlineExclamationCircle />
          </div>
          <h2>Something went wrong</h2>
          <p>{error}</p>
          <button className="btn btn--primary" onClick={fetchRecommendation}>
            Retry Analysis
          </button>
        </div>
      </motion.div>
    );
  }

  if (!data) {
    return (
      <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <LoadingSpinner message="Loading career insights..." />
      </motion.div>
    );
  }

  /* ── No-Skills User → Course Showcase ─────────────────────────────────── */
  if (data.is_no_skills_user && data.correlation_courses?.length > 0) {
    return (
      <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <div className="recommendations-page__header">
            <h1>Career <span className="gradient-text">Launchpad</span></h1>
            <p>No technical skills detected -- <strong>Let us help you get started</strong></p>
          </div>

          {/* Insight Banner */}
          <motion.div
            className="no-skills-banner"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <div className="no-skills-banner__icon">
              <HiOutlineLightBulb />
            </div>
            <div className="no-skills-banner__text">
              <h3>Your Career Journey Starts Here</h3>
              <p>{data.advanced_insights}</p>
            </div>
          </motion.div>

          <CourseShowcase courses={data.correlation_courses} />
        </motion.div>
      </motion.div>
    );
  }

  const salaryMin = data.salary_range_inr?.min ? (data.salary_range_inr.min / 100000).toFixed(0) : null;
  const salaryMax = data.salary_range_inr?.max ? (data.salary_range_inr.max / 100000).toFixed(0) : null;

  return (
    <motion.div className="recommendations-page" id="recommendations-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        {/* Header */}
        <div className="recommendations-page__header">
          <h1>Career Insights & <span className="gradient-text">Domain Fit</span></h1>
          <p>Advanced Analysis Engine  <strong>Powered by TheCorrelation</strong></p>
        </div>

        <div className="recommendations-grid">
          {/* LEFT COLUMN */}
          <motion.div className="rec-col-left" initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.2 }}>
            
            {/* Advanced Insights & Fit Card */}
            <div className="rec-fit-card">
              <div className="rec-fit-card__content">
                <div className="rec-fit-card__badge">
                  <HiOutlineBriefcase /> Best Match: {data.predicted_role}
                </div>
                <h2 className="rec-fit-card__title">
                  Domain Fit: {Number(data.domain_fit_percentage || data.confidence * 100).toFixed(0)}%
                </h2>
                <p className="rec-fit-card__desc">{data.advanced_insights}</p>
                {data.action_verb_feedback && (
                   <div className="rec-feedback-box">
                     <strong><HiOutlineExclamationCircle /> Resume Feedback: </strong> {data.action_verb_feedback}
                   </div>
                )}
                
                {data.course_recommendation && (
                  <div className="institute-cta">
                    <div className="institute-cta__icon"><HiOutlineAcademicCap /></div>
                    <div className="institute-cta__text">
                      <h4>{data.course_recommendation.title} -- {data.course_recommendation.provider}</h4>
                      <p>{data.course_recommendation.description}</p>
                    </div>
                    <a href={data.course_recommendation.url} target="_blank" rel="noreferrer" className="btn btn--secondary">Explore Course</a>
                  </div>
                )}
              </div>
            </div>

            {/* Salary Range */}
            {salaryMin && salaryMax && (
              <motion.div className="rec-salary-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
                <HiOutlineCurrencyRupee className="rec-salary-card__icon" />
                <div>
                  <h4>Expected Salary Range</h4>
                  <p className="rec-salary-card__range">INR {salaryMin} LPA -- INR {salaryMax} LPA</p>
                  <span className="rec-salary-card__role">for {data.predicted_role} in India</span>
                </div>
              </motion.div>
            )}

            {/* Stats Row */}
            <div className="rec-stats-row">
              <StatsCard icon={<HiOutlineCheckCircle />} label="Matched Skills" value={data.matched_skills?.length || 0} accent="primary" delay={0.1} />
              <StatsCard icon={<HiOutlineExclamationCircle />} label="Skill Gaps" value={data.skill_gap?.length || 0} accent="error" delay={0.2} />
              <StatsCard icon={<HiOutlineClock />} label="Weeks to Close" value={data.estimated_gap_weeks || 0} accent="warning" delay={0.3} />
              <StatsCard icon={<HiOutlineAcademicCap />} label="Learning Steps" value={data.learning_path?.length || 0} accent="secondary" delay={0.4} />
            </div>

            {/* Top 3 Roles */}
            {data.top_3_roles?.length > 0 && (
              <section className="rec-section">
                <h3 className="rec-section__title"><HiOutlineTrendingUp /> Top Predicted Roles</h3>
                <div className="rec-roles-card">
                  {data.top_3_roles.map((r, i) => (
                    <RoleConfidenceBar key={r.role} role={r.role} confidence={r.confidence} rank={r.rank || i + 1} />
                  ))}
                </div>
              </section>
            )}

          </motion.div>

          {/* RIGHT COLUMN */}
          <motion.div className="rec-col-right" initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.3 }}>
            
            {/* Interview Prep */}
            {data.interview_prep?.length > 0 && (
              <section className="rec-section prep-section">
                <h3 className="rec-section__title">
                  <HiOutlineQuestionMarkCircle /> Interview Preparation
                </h3>
                <div className="prep-card">
                  <p className="prep-section__desc">Based on your skill gaps, practice answering these questions for {data.predicted_role}:</p>
                  <ul className="prep-list">
                    {data.interview_prep.map((question, idx) => (
                      <li key={idx} className="prep-list__item">{question}</li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {/* Matched Skills */}
            <section className="rec-section">
              <h3 className="rec-section__title">Your Matched Skills ({data.matched_skills?.length || 0})</h3>
              <div className="rec-skills-wrap">
                {data.matched_skills?.map((s) => (
                  <SkillBadge key={s} skill={s} category="programming" />
                ))}
              </div>
            </section>

            {/* Skill Gap with YouTube */}
            {data.skill_gap?.length > 0 && (
              <section className="rec-section">
                <h3 className="rec-section__title">
                  <HiOutlineExclamationCircle /> Skill Gaps to Address
                </h3>
                <div className="rec-gap-list">
                  {data.skill_gap.map((g, i) => (
                    <motion.div
                      key={g.skill}
                      className={`rec-gap-item ${g.is_core ? 'rec-gap-item--core' : ''}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 + i * 0.05 }}
                    >
                      <div className="rec-gap-item__header">
                        <span className="rec-gap-item__name">{g.skill}</span>
                        <div className="rec-gap-item__actions">
                          {g.is_core && <span className="rec-gap-item__badge">Core</span>}
                          <YouTubeButton skill={g.skill} />
                        </div>
                      </div>
                      <span className="rec-gap-item__category">{g.category}</span>
                      {g.learning_resource && (
                        <p className="rec-gap-item__resource">{g.learning_resource}</p>
                      )}
                    </motion.div>
                  ))}
                </div>
              </section>
            )}

            {/* Navigate to Career Path */}
            <div className="rec-cta">
              <button className="btn btn--primary btn--lg" style={{width: '100%', marginTop: '1rem'}} onClick={() => navigate('/job-links')} id="btn-view-jobs">
                Find Matching Jobs <HiOutlineChevronRight />
              </button>
            </div>
            
          </motion.div>
        </div>

        {/* Career Exploration for General Skills Users */}
        {data.is_general_skills_user && data.career_exploration_suggestions?.length > 0 && (
          <motion.section
            className="rec-explore"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <div className="rec-explore__header">
              <div className="rec-explore__badge">
                <HiOutlineSparkles /> Personalized For You
              </div>
              <h2>Explore New Career Paths</h2>
              <p>Based on your current skill set, these fields are perfect to transition into -- <strong>no advanced prerequisites needed!</strong></p>
            </div>

            <div className="rec-explore__grid">
              {data.career_exploration_suggestions.map((career, i) => (
                <motion.div
                  key={career.title}
                  className="rec-explore-card"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 + i * 0.1 }}
                  whileHover={{ y: -6 }}
                >
                  <div className="rec-explore-card__icon">{getIconForType(career.icon_type)}</div>
                  <h3>{career.title}</h3>
                  <p>{career.description}</p>
                  
                  <div className="rec-explore-card__why">
                    <HiOutlineTrendingUp />
                    <span>{career.why_learn}</span>
                  </div>

                  <div className="rec-explore-card__prereq">
                    <HiOutlineCheckCircle />
                    <span>{career.prerequisites}</span>
                  </div>

                  <div className="rec-explore-card__skills">
                    <h4>Skills to Learn:</h4>
                    <div className="rec-explore-card__skill-tags">
                      {career.skills_to_learn.map(s => (
                        <span key={s} className="rec-explore-card__skill-tag">{s}</span>
                      ))}
                    </div>
                  </div>

                  <div className="rec-explore-card__actions">
                    <a href={career.explore_url} target="_blank" rel="noopener noreferrer" className="btn btn--teal btn--sm">
                      <HiOutlineExternalLink /> Explore Program
                    </a>
                    <a href={career.youtube_url} target="_blank" rel="noopener noreferrer" className="btn btn--youtube">
                      <HiOutlinePlay /> Watch Roadmap
                    </a>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </motion.div>
    </motion.div>
  );
}
