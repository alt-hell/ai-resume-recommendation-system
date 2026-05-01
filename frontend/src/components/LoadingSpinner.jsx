import { motion } from 'framer-motion';
import './LoadingSpinner.css';

export default function LoadingSpinner({ message = 'Analyzing your resume...' }) {
  return (
    <div className="spinner-container" id="loading-spinner">
      <motion.div
        className="spinner-ring"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
      >
        <svg width="56" height="56" viewBox="0 0 56 56">
          <circle cx="28" cy="28" r="24" fill="none" stroke="url(#spinner-grad)" strokeWidth="4" strokeLinecap="round" strokeDasharray="120 40" />
          <defs>
            <linearGradient id="spinner-grad" x1="0" y1="0" x2="56" y2="56">
              <stop stopColor="#7c5cfc" />
              <stop offset="1" stopColor="#5eead4" />
            </linearGradient>
          </defs>
        </svg>
      </motion.div>
      <motion.p
        className="spinner-message"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        {message}
      </motion.p>
    </div>
  );
}
