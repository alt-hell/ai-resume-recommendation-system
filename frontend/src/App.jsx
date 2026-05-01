import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import AnimatedBackground from './components/AnimatedBackground';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Recommendations from './pages/Recommendations';
import JobLinks from './pages/JobLinks';
import ResumeCoach from './pages/ResumeCoach';
import CareerAdvisor from './pages/CareerAdvisor';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout" id="app-root">
        <AnimatedBackground />
        <Navbar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/job-links" element={<JobLinks />} />
            <Route path="/resume-coach" element={<ResumeCoach />} />
            <Route path="/career-advisor" element={<CareerAdvisor />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
