import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import AnimatedBackground from './components/AnimatedBackground';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Recommendations from './pages/Recommendations';
import JobLinks from './pages/JobLinks';
import ResumeCoach from './pages/ResumeCoach';
import CareerAdvisor from './pages/CareerAdvisor';
import './App.css';

function AppContent() {
  const location = useLocation();
  return (
    <div className="app-layout" id="app-root">
      <AnimatedBackground />
      <Navbar />
      <main className="app-main">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/job-links" element={<JobLinks />} />
            <Route path="/resume-coach" element={<ResumeCoach />} />
            <Route path="/career-advisor" element={<CareerAdvisor />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
