import './SkillBadge.css';

const CATEGORY_COLORS = {
  'programming': { bg: 'rgba(124, 92, 252, 0.12)', color: '#a78bfa' },
  'framework': { bg: 'rgba(94, 234, 212, 0.12)', color: '#5eead4' },
  'database': { bg: 'rgba(251, 191, 36, 0.12)', color: '#fbbf24' },
  'cloud': { bg: 'rgba(96, 165, 250, 0.12)', color: '#60a5fa' },
  'devops': { bg: 'rgba(244, 114, 182, 0.12)', color: '#f472b6' },
  'ml_ai': { bg: 'rgba(52, 211, 153, 0.12)', color: '#34d399' },
  'soft_skill': { bg: 'rgba(156, 163, 175, 0.12)', color: '#9ca3af' },
  'default': { bg: 'rgba(124, 92, 252, 0.08)', color: '#8b8b9e' },
};

export default function SkillBadge({ skill, category = 'default', size = 'md' }) {
  const catKey = category?.toLowerCase().replace(/[\s/]+/g, '_');
  const colors = CATEGORY_COLORS[catKey] || CATEGORY_COLORS.default;

  return (
    <span
      className={`skill-badge skill-badge--${size}`}
      style={{ background: colors.bg, color: colors.color, borderColor: `${colors.color}22` }}
      title={category}
    >
      {skill}
    </span>
  );
}
