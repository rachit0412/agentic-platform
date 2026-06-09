import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, Cpu, Database, Shield, Terminal, Wifi, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';
import AnimatedBackground from './components/AnimatedBackground';
import LoginPage from './components/LoginPage';
import ThemeSwitcher from './components/ThemeSwitcher';
import useTheme from './hooks/useTheme';

/* ── Boot sequence lines for typewriter ────────────────── */
const BOOT_LINES = [
  { text: '> Initializing kernel modules...', icon: Cpu, color: '#6366f1' },
  { text: '> Loading neural network drivers...', icon: Database, color: '#8b5cf6' },
  { text: '> Establishing secure tunnel...', icon: Wifi, color: '#06b6d4' },
  { text: '> Verifying encryption keys...', icon: Shield, color: '#22d3ee' },
  { text: '> System integrity check: PASSED', icon: CheckCircle2, color: '#10b981' },
  { text: '> AGENTIC PLATFORM v2.0 — ONLINE', icon: Zap, color: '#f59e0b' },
];

/* ── Gamified Intro Gate ──────────────────────────────── */
function IntroGate({ onComplete }) {
  const [visibleLines, setVisibleLines] = useState(0);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('boot'); // 'boot' | 'ready' | 'open'

  useEffect(() => {
    // Typewriter: reveal lines one by one
    const lineTimers = BOOT_LINES.map((_, i) =>
      setTimeout(() => setVisibleLines(i + 1), 120 + i * 200)
    );
    // Progress bar synced with lines
    const progTimer = setInterval(() => {
      setProgress((p) => Math.min(p + 2, 100));
    }, 22);
    // Phase transitions
    const readyTimer = setTimeout(() => setPhase('ready'), 120 + BOOT_LINES.length * 200 + 150);
    const openTimer = setTimeout(() => setPhase('open'), 120 + BOOT_LINES.length * 200 + 500);
    return () => {
      lineTimers.forEach(clearTimeout);
      clearInterval(progTimer);
      clearTimeout(readyTimer);
      clearTimeout(openTimer);
    };
  }, []);

  return (
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Left gate panel */}
      <motion.div
        className="absolute top-0 left-0 w-1/2 h-full bg-gray-950"
        initial={{ x: 0 }}
        animate={phase === 'open' ? { x: '-100%' } : { x: 0 }}
        transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
      >
        <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-transparent via-indigo-500/60 to-transparent" />
        {/* Hex grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'radial-gradient(circle, #6366f1 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }} />
      </motion.div>

      {/* Right gate panel */}
      <motion.div
        className="absolute top-0 right-0 w-1/2 h-full bg-gray-950"
        initial={{ x: 0 }}
        animate={phase === 'open' ? { x: '100%' } : { x: 0 }}
        transition={{ duration: 0.5, ease: [0.76, 0, 0.24, 1] }}
      >
        <div className="absolute top-0 left-0 w-[1px] h-full bg-gradient-to-b from-transparent via-cyan-500/60 to-transparent" />
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'radial-gradient(circle, #06b6d4 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }} />
      </motion.div>

      {/* Center content — boot terminal + logo */}
      <motion.div
        className="relative z-10 flex flex-col items-center w-[420px] max-w-[90vw]"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
      >
        {/* Animated rings behind logo */}
        <motion.div
          className="absolute w-24 h-24 rounded-full border border-indigo-500/30"
          style={{ top: '-12px' }}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: [0.5, 1.8, 1.8], opacity: [0, 0.5, 0] }}
          transition={{ duration: 0.8, delay: 0.15 }}
        />
        <motion.div
          className="absolute w-24 h-24 rounded-full border border-cyan-500/20"
          style={{ top: '-12px' }}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: [0.5, 2.2, 2.2], opacity: [0, 0.3, 0] }}
          transition={{ duration: 0.8, delay: 0.25 }}
        />

        {/* Logo */}
        <motion.div
          className="flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/40 mb-3"
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <Zap className="w-8 h-8 text-white" />
        </motion.div>

        <motion.h1
          className="text-2xl font-bold text-white tracking-tight mb-1"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        >
          Agentic Platform
        </motion.h1>

        {/* ── Boot Terminal ──────────────────────────── */}
        <div className="w-full mt-4 rounded-lg border border-gray-800 bg-gray-950/80 backdrop-blur-sm overflow-hidden font-mono text-xs">
          {/* Terminal header bar */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 border-b border-gray-800 bg-gray-900/50">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
            <span className="ml-2 text-[10px] text-gray-500 tracking-wider flex items-center gap-1">
              <Terminal className="w-3 h-3" /> SYSTEM BOOT
            </span>
          </div>
          {/* Terminal body */}
          <div className="px-3 py-2 space-y-1 min-h-[140px]">
            {BOOT_LINES.map((line, i) => {
              const Icon = line.icon;
              return (
                <motion.div
                  key={i}
                  className="flex items-center gap-2"
                  initial={{ opacity: 0, x: -10 }}
                  animate={i < visibleLines ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                  transition={{ duration: 0.15 }}
                >
                  <Icon className="w-3 h-3 flex-shrink-0" style={{ color: line.color }} />
                  <span style={{ color: line.color }}>{line.text}</span>
                  {i < visibleLines - 1 && (
                    <CheckCircle2 className="w-3 h-3 ml-auto flex-shrink-0 text-emerald-400" />
                  )}
                </motion.div>
              );
            })}
            {/* Blinking cursor */}
            {phase === 'boot' && (
              <motion.span
                className="inline-block w-2 h-3.5 bg-indigo-400 ml-5"
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
            )}
          </div>
        </div>

        {/* ── Progress bar ──────────────────────────── */}
        <div className="w-full mt-3">
          <div className="flex justify-between text-[10px] font-mono text-gray-500 mb-1">
            <span>BOOT SEQUENCE</span>
            <span className="tabular-nums" style={{ color: progress >= 100 ? '#10b981' : '#6366f1' }}>
              {Math.min(progress, 100)}%
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              initial={{ width: '0%' }}
              animate={{ width: `${Math.min(progress, 100)}%` }}
              transition={{ duration: 0.05 }}
              style={{
                background: progress >= 100
                  ? 'linear-gradient(90deg, #10b981, #06b6d4)'
                  : 'linear-gradient(90deg, #6366f1, #8b5cf6, #06b6d4)',
                boxShadow: progress >= 100
                  ? '0 0 12px rgba(16,185,129,0.5)'
                  : '0 0 8px rgba(99,102,241,0.4)',
              }}
            />
          </div>
        </div>

        {/* ── System ready badge ──────────────────── */}
        <AnimatePresence>
          {phase !== 'boot' && (
            <motion.div
              className="mt-3 flex items-center gap-2 px-4 py-1.5 rounded-full border"
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              style={{
                borderColor: 'rgba(16,185,129,0.4)',
                background: 'rgba(16,185,129,0.08)',
                boxShadow: '0 0 20px rgba(16,185,129,0.15)',
              }}
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </motion.div>
              <span className="text-xs font-bold tracking-[0.2em] uppercase text-emerald-400">
                System Online
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Trigger completion after gates open */}
      <motion.div
        onAnimationComplete={onComplete}
        animate={{ opacity: 0 }}
        transition={{ delay: phase === 'open' ? 0.5 : 100 }}
        key={phase}
      />
    </motion.div>
  );
}

export default function App() {
  const { mode, resolved, setMode } = useTheme();
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    /* Safety fallback — auto-dismiss after boot sequence completes */
    const t = setTimeout(() => setShowIntro(false), 2800);
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
