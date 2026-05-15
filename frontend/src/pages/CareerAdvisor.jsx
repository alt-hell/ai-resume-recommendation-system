import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  HiOutlineSparkles, HiOutlineLightBulb, HiOutlineChat,
  HiOutlinePaperAirplane, HiOutlineChip,
  HiOutlineRefresh, HiOutlineDocumentText, HiOutlineChartBar,
  HiOutlineGlobe, HiOutlineCode, HiOutlineCurrencyDollar,
  HiOutlineCube, HiOutlineUser, HiOutlineUpload,
} from 'react-icons/hi';
import { askCareerAdvisor, getCareerPrompts } from '../api/client';
import './CareerAdvisor.css';

/* Fallback prompts (used while loading or if API fails) */
const FALLBACK_PROMPTS = [
  { text: "How do I transition from manual testing to DevOps?",   iconKey: "refresh"   },
  { text: "What certifications should I get for Data Science?",    iconKey: "document"  },
  { text: "How can I move from non-tech to data analytics?",       iconKey: "chart"     },
  { text: "What is the career scope in GenAI and LLMs?",           iconKey: "chip"      },
  { text: "What skills do I need for a cloud engineer role?",       iconKey: "globe"     },
  { text: "How to build a portfolio for frontend development?",     iconKey: "code"      },
  { text: "What are the highest-paying tech roles in 2025?",        iconKey: "dollar"    },
  { text: "How to prepare for a system design interview?",          iconKey: "cube"      },
];

/* Icon rotation for personalized prompts */
const ICON_KEYS = ["refresh", "document", "chart", "chip", "globe", "code", "dollar", "cube"];

export default function CareerAdvisor() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [prompts, setPrompts] = useState(FALLBACK_PROMPTS);
  const [isPersonalized, setIsPersonalized] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const resumeId = sessionStorage.getItem('resumeId') || localStorage.getItem('resumeId');

  /* Fetch personalized prompts on mount */
  useEffect(() => {
    async function loadPrompts() {
      try {
        const result = await getCareerPrompts(resumeId);
        if (result.prompts && result.prompts.length > 0) {
          const formatted = result.prompts.map((text, i) => ({
            text,
            iconKey: ICON_KEYS[i % ICON_KEYS.length],
          }));
          setPrompts(formatted);
          setIsPersonalized(result.personalized || false);
        }
      } catch (err) {
        // Keep fallback prompts
      }
    }
    loadPrompts();
  }, [resumeId]);

  /* Resolve icon key to JSX element */
  const getPromptIcon = (iconKey) => {
    const map = {
      refresh:  <HiOutlineRefresh />,
      document: <HiOutlineDocumentText />,
      chart:    <HiOutlineChartBar />,
      chip:     <HiOutlineChip />,
      globe:    <HiOutlineGlobe />,
      code:     <HiOutlineCode />,
      dollar:   <HiOutlineCurrencyDollar />,
      cube:     <HiOutlineCube />,
    };
    return map[iconKey] || <HiOutlineLightBulb />;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const sendMessage = async (text) => {
    const question = text || input.trim();
    if (!question || loading) return;

    const userMsg = { role: 'user', content: question, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await askCareerAdvisor(resumeId, question);
      const aiMsg = {
        role: 'ai',
        content: result.answer,
        source: result.source,
        model: result.model,
        contextAware: result.context_aware,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'ai',
        content: 'Sorry, I couldn\'t process your question right now. Please try again.',
        source: 'error',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <motion.div 
      className="advisor-page" 
      id="career-advisor-page"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="advisor-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* Header */}
        <div className="advisor-header">
          <div className="advisor-header__icon">
            <HiOutlineSparkles />
            <div className="advisor-header__icon-ring" />
          </div>
          <div>
            <h1>AI Career <span className="gradient-text">Advisor</span></h1>
            <p>
              {resumeId
                ? 'Personalized guidance based on your resume profile'
                : 'Upload your resume first for personalized career advice'}
            </p>
          </div>
          {resumeId ? (
            <span className="badge badge--teal">
              <HiOutlineChip /> Resume Context Active
            </span>
          ) : (
            <button
              className="badge badge--amber"
              onClick={() => navigate('/upload')}
              style={{ cursor: 'pointer', border: 'none', background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}
            >
              <HiOutlineUpload /> Upload Resume
            </button>
          )}
        </div>

        {/* No Resume Warning */}
        {!resumeId && messages.length === 0 && (
          <motion.div
            className="advisor-no-resume"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.2)',
              borderRadius: '12px',
              padding: '16px 20px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '0.9rem',
              color: 'rgba(255,255,255,0.8)',
            }}
          >
            <HiOutlineUpload style={{ fontSize: '1.3rem', color: '#f59e0b', flexShrink: 0 }} />
            <span>
              <strong>Pro tip:</strong> Upload your resume first to get advice tailored to your specific skills, 
              gaps, and career goals. Without a resume, you'll get general guidance only.
            </span>
          </motion.div>
        )}

        {/* Chat Area */}
        <div className="advisor-chat">
          {messages.length === 0 ? (
            <div className="advisor-welcome">
              <div className="advisor-welcome__icon">
                <HiOutlineChat />
              </div>
              <h2>
                {resumeId
                  ? 'Your AI Career Advisor is Ready'
                  : 'Welcome to AI Career Advisor'}
              </h2>
              <p>
                {resumeId
                  ? 'I\'ve analyzed your resume and can give you personalized advice about your career path, skill gaps, and growth opportunities.'
                  : 'I can help you with career transitions, learning roadmaps, and interview preparation. Upload your resume for personalized advice!'}
              </p>
              
              <div className="advisor-welcome__divider">
                <span>{isPersonalized ? 'Personalized for you' : 'Try asking'}</span>
              </div>

              <div className="advisor-prompts">
                {prompts.map((prompt, i) => (
                  <motion.button
                    key={i}
                    className="advisor-prompt-chip"
                    onClick={() => sendMessage(prompt.text)}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                    whileHover={{ scale: 1.02, y: -2 }}
                  >
                    <span className="advisor-prompt-chip__icon">{getPromptIcon(prompt.iconKey)}</span>
                    <span>{prompt.text}</span>
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            <div className="advisor-messages">
              <AnimatePresence>
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    className={`advisor-message advisor-message--${msg.role}`}
                    initial={{ opacity: 0, y: 15, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className={`advisor-message__avatar advisor-message__avatar--${msg.role}`}>
                      {msg.role === 'user' ? <HiOutlineUser /> : <HiOutlineChip />}
                    </div>
                    <div className="advisor-message__bubble">
                      <div className="advisor-message__content">
                        {msg.content.split('\n').map((line, j) => (
                          <p key={j}>{line}</p>
                        ))}
                      </div>
                      {msg.source === 'ai' && (
                        <span className="advisor-message__meta">
                          <HiOutlineSparkles /> 
                          {msg.contextAware 
                            ? ' Personalized to your resume' 
                            : ' Powered by TheCorrelation'}
                        </span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
              
              {loading && (
                <motion.div
                  className="advisor-message advisor-message--ai"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="advisor-message__avatar advisor-message__avatar--ai">
                    <HiOutlineChip />
                  </div>
                  <div className="advisor-message__bubble">
                    <div className="advisor-typing">
                      <span /><span /><span />
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="advisor-input-area">
          {messages.length > 0 && (
            <div className="advisor-quick-prompts">
              {prompts.slice(0, 4).map((p, i) => (
                <button
                  key={i}
                  className="advisor-quick-chip"
                  onClick={() => sendMessage(p.text)}
                  disabled={loading}
                >
                  <span className="advisor-quick-chip__icon">{getPromptIcon(p.iconKey)}</span>
                  {p.text.length > 38 ? p.text.slice(0, 35) + '...' : p.text}
                </button>
              ))}
            </div>
          )}
          <div className="advisor-input-wrap">
            <textarea
              ref={inputRef}
              className="advisor-input"
              placeholder={resumeId 
                ? "Ask about your career path, skill gaps, next steps..." 
                : "Ask me about career paths, skills, transitions..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
              id="advisor-input"
            />
            <button
              className="advisor-send-btn"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              id="advisor-send"
            >
              <HiOutlinePaperAirplane />
            </button>
          </div>
          <p className="advisor-disclaimer">
            <HiOutlineLightBulb /> AI responses are for guidance only. Always verify with industry professionals.
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}
