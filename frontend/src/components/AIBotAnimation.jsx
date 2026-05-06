import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import './AIBotAnimation.css';

export default function AIBotAnimation() {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      // Normalize mouse coordinates to range [-1, 1] based on window size
      mouseX.set((e.clientX / window.innerWidth - 0.5) * 2);
      mouseY.set((e.clientY / window.innerHeight - 0.5) * 2);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  // Random blinking effect
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setIsBlinking(true);
      setTimeout(() => setIsBlinking(false), 150);
      
      // Sometimes double blink
      if (Math.random() > 0.7) {
        setTimeout(() => {
          setIsBlinking(true);
          setTimeout(() => setIsBlinking(false), 150);
        }, 300);
      }
    }, Math.random() * 4000 + 2000); // Blink every 2-6 seconds
    
    return () => clearInterval(blinkInterval);
  }, []);

  // Spring configuration for smooth tracking
  const springConfig = { damping: 20, stiffness: 100 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);

  // Map mouse position to 3D rotations for the head
  const rotateX = useTransform(smoothY, [-1, 1], [15, -15]);
  const rotateY = useTransform(smoothX, [-1, 1], [-25, 25]);
  
  // Subtle eye movement tracking the mouse
  const eyeMoveX = useTransform(smoothX, [-1, 1], [-8, 8]);
  const eyeMoveY = useTransform(smoothY, [-1, 1], [-4, 4]);

  return (
    <div className="ai-bot-container">
      <motion.div
        className="ai-bot"
        style={{ rotateX, rotateY }}
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* Glowing Aura Behind the Bot */}
        <div className="ai-bot-aura" />
        
        {/* Main Head Structure */}
        <div className="ai-bot-head">
          {/* Side Antennas/Ears */}
          <div className="ai-bot-ear left">
            <div className="ai-bot-ear-light" />
          </div>
          <div className="ai-bot-ear right">
            <div className="ai-bot-ear-light" />
          </div>
          
          {/* The Face Screen */}
          <div className="ai-bot-face">
            {/* Eyes */}
            <motion.div className="ai-bot-eyes" style={{ x: eyeMoveX, y: eyeMoveY }}>
              <div className="ai-bot-eye">
                <motion.div 
                  className="ai-bot-pupil"
                  animate={{ scaleY: isBlinking ? 0.1 : 1 }}
                  transition={{ duration: 0.1 }}
                />
              </div>
              <div className="ai-bot-eye">
                <motion.div 
                  className="ai-bot-pupil"
                  animate={{ scaleY: isBlinking ? 0.1 : 1 }}
                  transition={{ duration: 0.1 }}
                />
              </div>
            </motion.div>
            
            {/* AI Talking Waveform Mouth */}
            <div className="ai-bot-mouth">
              <motion.div className="ai-bot-wave" animate={{ height: [4, 12, 4] }} transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }} />
              <motion.div className="ai-bot-wave" animate={{ height: [8, 18, 8] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.2, ease: "easeInOut" }} />
              <motion.div className="ai-bot-wave" animate={{ height: [12, 24, 12] }} transition={{ duration: 1.8, repeat: Infinity, delay: 0.1, ease: "easeInOut" }} />
              <motion.div className="ai-bot-wave" animate={{ height: [8, 18, 8] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0.3, ease: "easeInOut" }} />
              <motion.div className="ai-bot-wave" animate={{ height: [4, 12, 4] }} transition={{ duration: 1.6, repeat: Infinity, delay: 0.4, ease: "easeInOut" }} />
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
