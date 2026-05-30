import { AnimatePresence, motion } from 'framer-motion';
import { Zap } from 'lucide-react';
import { useEffect, useState } from 'react';
import AnimatedBackground from './components/AnimatedBackground';
import LoginPage from './components/LoginPage';
import ThemeSwitcher from './components/ThemeSwitcher';
import useTheme from './hooks/useTheme';

/* ── Intro "gate" splash ──────────────────────────────── */
function IntroGate({ onComplete }) {
  return (
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Left gate panel */}
      <motion.div
        className="absolute top-0 left-0 w-1/2 h-full bg-gray-950"
        initial={{ x: 0 }}
        animate={{ x: '-100%' }}
        transition={{ delay: 1.6, duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
      >
        <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-transparent via-indigo-500/60 to-transparent" />
      </motion.div>

      {/* Right gate panel */}
      <motion.div
        className="absolute top-0 right-0 w-1/2 h-full bg-gray-950"
        initial={{ x: 0 }}
        animate={{ x: '100%' }}
        transition={{ delay: 1.6, duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
      >
        <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-cyan-500/60 to-transparent" />
      </motion.div>

      {/* Center logo + text */}
      <motion.div
        className="relative z-10 flex flex-col items-center"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        {/* Animated ring behind logo */}
        <motion.div
          className="absolute w-24 h-24 rounded-full border border-indigo-500/30"
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: [0.5, 1.8, 1.8], opacity: [0, 0.5, 0] }}
          transition={{ duration: 1.5, delay: 0.3 }}
        />
        <motion.div
          className="absolute w-24 h-24 rounded-full border border-cyan-500/20"
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: [0.5, 2.2, 2.2], opacity: [0, 0.3, 0] }}
          transition={{ duration: 1.5, delay: 0.5 }}
        />

        <motion.div
          className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/40 mb-4"
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Zap className="w-8 h-8 text-white" />
        </motion.div>

        <motion.h1
          className="text-2xl font-bold text-white tracking-tight"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4 }}
        >
          Agentic Platform
        </motion.h1>

        <motion.div
          className="mt-3 flex items-center gap-1.5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7, duration: 0.3 }}
        >
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-indigo-400"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 0.8, delay: 0.8 + i * 0.15, repeat: 1 }}
            />
          ))}
          <span className="ml-1 text-xs text-gray-400 font-medium tracking-wider uppercase">
            Initializing
          </span>
        </motion.div>
      </motion.div>

      {/* Trigger completion after animation */}
      <motion.div
        onAnimationComplete={onComplete}
        animate={{ opacity: 0 }}
        transition={{ delay: 2.5 }}
      />
    </motion.div>
  );
}

export default function App() {
  const { mode, resolved, setMode } = useTheme();
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    /* Safety fallback — auto-dismiss after 3s */
    const t = setTimeout(() => setShowIntro(false), 3000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden font-sans text-gray-900 dark:text-white">
      <AnimatedBackground resolved={resolved} />

      {/* Theme switcher — top-right corner */}
      <div className="fixed top-4 right-4 z-50">
        <ThemeSwitcher mode={mode} setMode={setMode} />
      </div>

      {/* Main content — only visible after intro */}
      <AnimatePresence>
        {!showIntro && (
          <motion.div
            className="h-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <LoginPage />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Intro gate overlay */}
      <AnimatePresence>
        {showIntro && <IntroGate onComplete={() => setShowIntro(false)} />}
      </AnimatePresence>
    </div>
  );
}
