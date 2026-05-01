import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  HiOutlineHome,
  HiOutlineCloudUpload,
  HiOutlineLightBulb,
  HiOutlineExternalLink,
  HiOutlineAcademicCap,
  HiOutlineSparkles,
} from 'react-icons/hi';
import './Navbar.css';

const navItems = [
  { to: '/', icon: HiOutlineHome, label: 'Dashboard' },
  { to: '/upload', icon: HiOutlineCloudUpload, label: 'Upload Resume' },
  { to: '/recommendations', icon: HiOutlineLightBulb, label: 'Insights' },
  { to: '/job-links', icon: HiOutlineExternalLink, label: 'Job Links' },
  { to: '/resume-coach', icon: HiOutlineAcademicCap, label: 'Resume Coach' },
  { to: '/career-advisor', icon: HiOutlineSparkles, label: 'Career Advisor', isNew: true },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="navbar" id="main-nav">

      {/* Logo */}
      <div className="navbar__logo">
        <div className="navbar__logo-icon">
          <img
            src="/favicon-32x32.png"
            alt="SkillSync Logo"
            width="28"
            height="28"
            style={{ borderRadius: '8px', objectFit: 'cover' }}
          />
        </div>
        <div className="navbar__logo-text">
          <span className="navbar__logo-title">SkillSync</span>
          <span className="navbar__logo-subtitle">Career Assistant</span>
        </div>
      </div>

      {/* Nav Links */}
      <ul className="navbar__links">
        {navItems.map(({ to, icon: Icon, label, isNew }) => {
          const isActive = location.pathname === to;
          return (
            <li key={to}>
              <NavLink
                to={to}
                className="navbar__link"
                id={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
              >
                {isActive && (
                  <motion.div
                    className="navbar__link-bg"
                    layoutId="nav-active"
                    transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                  />
                )}
                <Icon className="navbar__link-icon" />
                <span className="navbar__link-label">{label}</span>
                {isNew && <span className="navbar__link-new">NEW</span>}
              </NavLink>
            </li>
          );
        })}
      </ul>

      {/* Footer */}
      <div className="navbar__footer">
        <div className="navbar__status">
          <div className="navbar__status-dot" />
          <span>System Online</span>
        </div>
        <p className="navbar__version">Career Assistant v3.0</p>
        <p style={{ fontSize: '11px', color: '#888', marginTop: '4px' }}>
          Powered by{' '}
          <span style={{ color: '#7c5cfc', fontWeight: '600' }}>
            TheCorrelation
          </span>
        </p>
      </div>

    </nav>
  );
}