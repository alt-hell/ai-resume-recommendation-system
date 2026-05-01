import { motion } from 'framer-motion';
import './StatsCard.css';

export default function StatsCard({ icon, label, value, accent = 'primary', delay = 0 }) {
  return (
    <motion.div
      className={`stats-card stats-card--${accent}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
    >
      <div className="stats-card__icon">{icon}</div>
      <div className="stats-card__content">
        <span className="stats-card__value">{value}</span>
        <span className="stats-card__label">{label}</span>
      </div>
    </motion.div>
  );
}
