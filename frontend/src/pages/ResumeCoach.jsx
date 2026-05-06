import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineAcademicCap, HiOutlineSparkles, HiOutlineCheckCircle,
  HiOutlineExclamationCircle, HiOutlineLightningBolt, HiOutlineCode,
  HiOutlineClock, HiOutlineChevronRight, HiOutlineCloudUpload,
  HiOutlineDocumentText, HiOutlineStar, HiOutlinePlay, HiOutlineCalendar,
} from 'react-icons/hi';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import { getResumeCoach } from '../api/client';
import SkillBadge from '../components/SkillBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import './ResumeCoach.css';

const PRIORITY_COLORS = {
  high: { bg: 'rgba(248, 113, 113, 0.1)', border: 'rgba(248, 113, 113, 0.3)', color: '#f87171', label: 'High Priority' },
  medium: { bg: 'rgba(251, 191, 36, 0.1)', border: 'rgba(251, 191, 36, 0.3)', color: '#fbbf24', label: 'Medium' },
  low: { bg: 'rgba(94, 234, 212, 0.1)', border: 'rgba(94, 234, 212, 0.3)', color: '#5eead4', label: 'Tip' },
};

const DIFFICULTY_COLORS = {
  Beginner: '#34d399',
  Intermediate: '#fbbf24',
  Advanced: '#f87171',
};

function YouTubeSkillButton({ skill }) {
  const url = `https://www.youtube.com/results?search_query=Learn+${encodeURIComponent(skill)}+tutorial+2025`;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn--youtube" title={`Learn ${skill} on YouTube`}>
      <HiOutlinePlay /> Learn
    </a>
  );
}

function ScoreRing({ score, size = 140, strokeWidth = 10, label }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 75 ? '#34d399' : score >= 50 ? '#fbbf24' : '#f87171';

  return (
    <div className="score-ring">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={strokeWidth} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeLinecap="round" strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="score-ring__inner">
        <motion.span className="score-ring__value" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
          {score}
        </motion.span>
        <span className="score-ring__label">{label || 'Score'}</span>
      </div>
    </div>
  );
}

function ScoreBar({ label, score, delay = 0 }) {
  const color = score >= 75 ? '#34d399' : score >= 50 ? '#fbbf24' : '#f87171';
  return (
    <div className="score-bar">
      <div className="score-bar__header">
        <span className="score-bar__label">{label}</span>
        <span className="score-bar__value" style={{ color }}>{score}%</span>
      </div>
      <div className="score-bar__track">
        <motion.div
          className="score-bar__fill"
          style={{ background: color }}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 1, delay, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

function buildWeeklyPlan(tips, projectSuggestions, blueprint) {
  const weeks = [];
  const missingSkills = blueprint?.required_skills?.filter(s => !s.have).map(s => s.skill) || [];
  
  weeks.push({
    week: 1,
    title: 'Foundation & Assessment',
    tasks: [
      'Review and restructure your resume based on the improvement tips above',
      missingSkills[0] ? `Start learning: ${missingSkills[0]}` : 'Polish your professional summary',
      'Set up your GitHub profile and portfolio structure',
    ],
  });
  weeks.push({
    week: 2,
    title: 'Skill Building',
    tasks: [
      missingSkills[1] ? `Deep dive into: ${missingSkills[1]}` : 'Practice coding challenges',
      missingSkills[2] ? `Begin exploring: ${missingSkills[2]}` : 'Build a mini-project',
      'Connect with professionals in your target domain on LinkedIn',
    ],
  });
  weeks.push({
    week: 3,
    title: 'Project Development',
    tasks: [
      projectSuggestions?.[0] ? `Start project: ${projectSuggestions[0].title}` : 'Build a portfolio project',
      'Document your project with a detailed README',
      'Practice explaining your technical decisions',
    ],
  });
  weeks.push({
    week: 4,
    title: 'Polish & Apply',
    tasks: [
      'Update your resume with new skills and projects',
      'Practice interview questions from the insights page',
      'Apply to 5+ matching jobs from the Job Links page',
    ],
  });
  return weeks;
}

export default function ResumeCoach() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const resumeId = sessionStorage.getItem('resumeId');

  const fetchCoaching = async () => {
    if (!resumeId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getResumeCoach(resumeId);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId && !data) {
      fetchCoaching();
    }
  }, [resumeId]);

  if (!resumeId) {
    return (
      <motion.div className="coach-page" id="resume-coach-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <div className="coach-empty">
          <div className="coach-empty__icon"><HiOutlineAcademicCap /></div>
          <h2>No Resume Uploaded</h2>
          <p>Upload your resume first to get personalized coaching and project suggestions.</p>
          <button className="btn btn--primary" onClick={() => navigate('/upload')}>
            <HiOutlineCloudUpload /> Upload Resume
          </button>
        </div>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <motion.div className="coach-page" id="resume-coach-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <LoadingSpinner message="Generating your personalized resume coaching..." />
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div className="coach-page" id="resume-coach-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
        <div className="coach-empty">
          <div className="coach-empty__icon coach-empty__icon--error"><HiOutlineExclamationCircle /></div>
          <h2>Something went wrong</h2>
          <p>{error}</p>
          <button className="btn btn--primary" onClick={fetchCoaching}>Retry</button>
        </div>
      </motion.div>
    );
  }

  if (!data) return null;

  const { score, improvement_tips, project_suggestions, blueprint } = data;
  const weeklyPlan = buildWeeklyPlan(improvement_tips, project_suggestions, blueprint);

  // Build radar data
  const radarData = [
    { subject: 'Skills', value: score.skills_score, fullMark: 100 },
    { subject: 'Projects', value: score.projects_score, fullMark: 100 },
    { subject: 'Structure', value: score.structure_score, fullMark: 100 },
    { subject: 'Action Verbs', value: score.action_verbs_score, fullMark: 100 },
  ];

  return (
    <motion.div className="coach-page" id="resume-coach-page" initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.4 }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        {/* Header */}
        <div className="coach-page__header">
          <div>
            <h1>Resume <span className="gradient-text">Coach</span></h1>
            <p>Personalized coaching for <strong>{data.predicted_role}</strong></p>
          </div>
          {!data.has_recommendation && (
            <button className="btn btn--secondary btn--sm" onClick={() => navigate('/recommendations')}>
              Generate Insights First <HiOutlineChevronRight />
            </button>
          )}
        </div>

        {/* Score Section */}
        <section className="coach-score-section">
          <div className="coach-score-card">
            <div className="coach-score-card__ring">
              <ScoreRing score={score.overall} label="Overall" />
            </div>
            <div className="coach-score-card__breakdown">
              <h3><HiOutlineStar /> Resume Quality Breakdown</h3>
              <div className="coach-score-card__bars">
                <ScoreBar label="Skills Coverage" score={score.skills_score} delay={0.2} />
                <ScoreBar label="Project Impact" score={score.projects_score} delay={0.4} />
                <ScoreBar label="Resume Structure" score={score.structure_score} delay={0.6} />
                <ScoreBar label="Action Verbs" score={score.action_verbs_score} delay={0.8} />
              </div>
              <div className="coach-score-card__stats">
                <span>{score.total_skills} skills detected</span>
                <span>{score.action_verbs_found} action verbs</span>
                <span>{score.sections_found} sections found</span>
              </div>
            </div>
          </div>
        </section>

        {/* Radar Chart */}
        <section className="coach-radar-section">
          <h3 className="coach-section__title"><HiOutlineSparkles /> Skills Radar</h3>
          <div className="coach-radar-card">
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#a0a0b8', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name="Score" dataKey="value" stroke="#7c5cfc" fill="#7c5cfc" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <div className="coach-grid">
          {/* Left Column */}
          <div className="coach-col-left">
            {/* Improvement Tips */}
            <section className="coach-section">
              <h3 className="coach-section__title">
                <HiOutlineLightningBolt /> Improvement Tips ({improvement_tips.length})
              </h3>
              <div className="coach-tips-list">
                {improvement_tips.map((tip, i) => {
                  const pStyle = PRIORITY_COLORS[tip.priority] || PRIORITY_COLORS.low;
                  return (
                    <motion.div
                      key={i}
                      className="coach-tip-card"
                      style={{ borderLeftColor: pStyle.color }}
                      initial={{ opacity: 0, x: -15 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <div className="coach-tip-card__header">
                        <span className="coach-tip-card__priority" style={{ background: pStyle.bg, color: pStyle.color, borderColor: pStyle.border }}>
                          {pStyle.label}
                        </span>
                        <span className="coach-tip-card__category">{tip.category}</span>
                      </div>
                      <h4>{tip.tip}</h4>
                      <p>{tip.detail}</p>
                    </motion.div>
                  );
                })}
              </div>
            </section>

            {/* Weekly Learning Plan */}
            <section className="coach-section">
              <h3 className="coach-section__title">
                <HiOutlineCalendar /> 4-Week Learning Plan
              </h3>
              <div className="coach-weekly-plan">
                {weeklyPlan.map((week, i) => (
                  <motion.div
                    key={i}
                    className="coach-week-card"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                  >
                    <div className="coach-week-card__header">
                      <span className="coach-week-card__number">Week {week.week}</span>
                      <h4>{week.title}</h4>
                    </div>
                    <ul className="coach-week-card__tasks">
                      {week.tasks.map((task, j) => (
                        <li key={j}><HiOutlineCheckCircle /> {task}</li>
                      ))}
                    </ul>
                  </motion.div>
                ))}
              </div>
            </section>
          </div>

          {/* Right Column */}
          <div className="coach-col-right">
            {/* Project Suggestions */}
            <section className="coach-section">
              <h3 className="coach-section__title">
                <HiOutlineCode /> Suggested Projects
              </h3>
              <div className="coach-projects-list">
                {project_suggestions.map((proj, i) => (
                  <motion.div
                    key={i}
                    className="coach-project-card"
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.08 }}
                  >
                    <div className="coach-project-card__header">
                      <h4>{proj.title}</h4>
                      <div className="coach-project-card__meta">
                        <span className="coach-project-card__difficulty" style={{ color: DIFFICULTY_COLORS[proj.difficulty] || '#a0a0b8' }}>
                          {proj.difficulty}
                        </span>
                        <span className="coach-project-card__time">
                          <HiOutlineClock /> {proj.time_weeks}w
                        </span>
                      </div>
                    </div>
                    <p>{proj.description}</p>
                    <div className="coach-project-card__stack">
                      {proj.tech_stack.map((tech) => (
                        <SkillBadge key={tech} skill={tech} category="framework" size="sm" />
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            </section>

            {/* Blueprint with YouTube */}
            <section className="coach-section">
              <h3 className="coach-section__title">
                <HiOutlineDocumentText /> Perfect Resume Blueprint
              </h3>

              <div className="coach-blueprint">
                <div className="coach-blueprint__block">
                  <h4>Required Skills ({Math.round(blueprint.required_coverage)}% covered)</h4>
                  <div className="coach-blueprint__skills">
                    {blueprint.required_skills.map((s) => (
                      <div key={s.skill} className={`coach-blueprint__skill ${s.have ? 'coach-blueprint__skill--have' : ''}`}>
                        {s.have ? <HiOutlineCheckCircle /> : <HiOutlineExclamationCircle />}
                        <span>{s.skill}</span>
                        {!s.have && <YouTubeSkillButton skill={s.skill} />}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="coach-blueprint__block">
                  <h4>Bonus Skills</h4>
                  <div className="coach-blueprint__skills">
                    {blueprint.bonus_skills.map((s) => (
                      <div key={s.skill} className={`coach-blueprint__skill coach-blueprint__skill--bonus ${s.have ? 'coach-blueprint__skill--have' : ''}`}>
                        {s.have ? <HiOutlineCheckCircle /> : <HiOutlineSparkles />}
                        <span>{s.skill}</span>
                        {!s.have && <YouTubeSkillButton skill={s.skill} />}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="coach-blueprint__block">
                  <h4>Ideal Resume Sections</h4>
                  <div className="coach-blueprint__sections">
                    {blueprint.sections_checklist.map((sec) => (
                      <div key={sec.section} className="coach-blueprint__section-item">
                        <HiOutlineCheckCircle />
                        <div>
                          <strong>{sec.section}</strong>
                          <p>{sec.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
