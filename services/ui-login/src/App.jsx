import { AnimatePresence, motion } from 'framer-motion';
import { Activity, CheckCircle2, Cpu, Database, Lock, Shield, Wifi, Zap } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import AnimatedBackground from './components/AnimatedBackground';
import LoginPage from './components/LoginPage';
import ThemeSwitcher from './components/ThemeSwitcher';
import useTheme from './hooks/useTheme';

/* ── Neural node canvas ──────────────────────────────────── */
function NeuralCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let raf;
    const W = canvas.width = window.innerWidth;
    const H = canvas.height = window.innerHeight;
    const nodes = Array.from({ length: 55 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
      r: 1.5 + Math.random() * 2,
      pulse: Math.random() * Math.PI * 2,
    }));
    let t = 0;
    function draw() {
      t += 0.015;
      ctx.clearRect(0, 0, W, H);
      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 140) {
            const alpha = (1 - dist / 140) * 0.18;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(99,102,241,${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }
      // nodes
      for (const n of nodes) {
        n.pulse += 0.04;
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
        const glow = 0.4 + 0.35 * Math.sin(n.pulse);
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(99,102,241,${glow})`;
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(raf);
  }, []);
  return <canvas ref={ref} className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }} />;
}

/* ── Boot phases ──────────────────────────────────────────── */
const PHASES = [
  { id: 'scan',    label: 'SCANNING ENVIRONMENT',     icon: Wifi,     color: '#6366f1', ms: 0 },
  { id: 'init',    label: 'INITIALIZING AGENTS',       icon: Cpu,      color: '#8b5cf6', ms: 380 },
  { id: 'auth',    label: 'LOADING AUTH MODULES',      icon: Lock,     color: '#06b6d4', ms: 760 },
  { id: 'data',    label: 'CONNECTING DATA LAYER',     icon: Database, color: '#22d3ee', ms: 1100 },
  { id: 'sec',     label: 'VERIFYING INTEGRITY',       icon: Shield,   color: '#10b981', ms: 1440 },
  { id: 'online',  label: 'AGENTIC PLATFORM ONLINE',   icon: Zap,      color: '#f59e0b', ms: 1780 },
];

/* ── Pre-login Intro Gate ─────────────────────────────────── */
function IntroGate({ onComplete }) {
  const [activePhase, setActivePhase] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('boot'); // boot → ready → split

  useEffect(() => {
    // Reveal phases one by one
    const timers = PHASES.map((p, i) => setTimeout(() => setActivePhase(i), p.ms + 120));
    // Smooth progress bar
    const progInterval = setInterval(() => setProgress(p => Math.min(p + 1.4, 100)), 28);
    // Stage transitions
    const readyT  = setTimeout(() => setStage('ready'), 2100);
    const splitT  = setTimeout(() => setStage('split'), 2500);
    const doneT   = setTimeout(onComplete,              3200);
    return () => {
      timers.forEach(clearTimeout);
      clearInterval(progInterval);
      clearTimeout(readyT);
      clearTimeout(splitT);
      clearTimeout(doneT);
    };
  }, []);

  const panelVariants = {
    closed: { scaleX: 1 },
    open:   { scaleX: 0, transition: { duration: 0.55, ease: [0.76, 0, 0.24, 1] } },
  };

  return (
    <motion.div className="fixed inset-0 z-[200] overflow-hidden" exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
      {/* Dark backdrop */}
      <div className="absolute inset-0 bg-gray-950" />

      {/* Animated neural network */}
      <NeuralCanvas />

      {/* Vignette */}
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse 80% 80% at 50% 50%, transparent 40%, rgba(2,3,14,0.85) 100%)',
        pointerEvents: 'none',
      }} />

      {/* ── Left blast panel ── */}
      <motion.div
        className="absolute top-0 left-0 h-full origin-left overflow-hidden"
        style={{ width: '50%' }}
        animate={stage === 'split' ? 'open' : 'closed'}
        variants={panelVariants}
      >
        <div className="absolute inset-0" style={{ background: 'linear-gradient(160deg,#0d1117 0%,#0e1525 50%,#0d1117 100%)' }} />
        {/* Circuit grid */}
        <div className="absolute inset-0 opacity-[0.035]" style={{
          backgroundImage: 'linear-gradient(rgba(99,102,241,1) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,1) 1px,transparent 1px)',
          backgroundSize: '40px 40px',
        }} />
        {/* Scanlines */}
        <div className="absolute inset-0" style={{
          backgroundImage: 'repeating-linear-gradient(to bottom,transparent 0,transparent 3px,rgba(99,102,241,0.025) 3px,rgba(99,102,241,0.025) 4px)',
        }} />
        {/* Inner glow toward seam */}
        <div className="absolute inset-0" style={{ background: 'linear-gradient(to right,transparent 30%,rgba(99,102,241,0.06) 100%)' }} />
        {/* Seam edge */}
        <div className="absolute top-0 right-0 w-[2px] h-full" style={{ background: 'linear-gradient(to bottom,transparent,rgba(99,102,241,0.7) 30%,rgba(6,182,212,0.9) 50%,rgba(99,102,241,0.7) 70%,transparent)', boxShadow: '0 0 16px rgba(99,102,241,0.4)' }} />
        {/* Warning stripes top/bottom */}
        <div className="absolute top-0 left-0 right-0 h-5" style={{ background: 'repeating-linear-gradient(135deg,transparent 0,transparent 8px,rgba(245,158,11,0.07) 8px,rgba(245,158,11,0.07) 16px)' }} />
        <div className="absolute bottom-0 left-0 right-0 h-5" style={{ background: 'repeating-linear-gradient(135deg,transparent 0,transparent 8px,rgba(245,158,11,0.07) 8px,rgba(245,158,11,0.07) 16px)' }} />
        {/* Corner bolts */}
        {[[16,16],[16,'auto'],['auto',16],['auto','auto']].map(([t,b],i)=>(
          <div key={i} className="absolute w-4 h-4" style={{ top: typeof t==='number'?t:'auto', bottom: typeof b==='number'?b:'auto', left: i<2?16:'auto', right: i>=2?16:'auto' }}>
            <div className="w-full h-full rounded-full border border-indigo-500/20 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/30" />
            </div>
          </div>
        ))}
        <div className="absolute bottom-10 right-6 font-mono text-[8px] tracking-[0.3em] text-indigo-500/15 uppercase">GATE-L :: SECTOR-7G</div>
      </motion.div>

      {/* ── Right blast panel ── */}
      <motion.div
        className="absolute top-0 right-0 h-full origin-right overflow-hidden"
        style={{ width: '50%' }}
        animate={stage === 'split' ? 'open' : 'closed'}
        variants={panelVariants}
      >
        <div className="absolute inset-0" style={{ background: 'linear-gradient(200deg,#0d1117 0%,#0e1525 50%,#0d1117 100%)' }} />
        <div className="absolute inset-0 opacity-[0.035]" style={{
          backgroundImage: 'linear-gradient(rgba(6,182,212,1) 1px,transparent 1px),linear-gradient(90deg,rgba(6,182,212,1) 1px,transparent 1px)',
          backgroundSize: '40px 40px',
        }} />
        <div className="absolute inset-0" style={{
          backgroundImage: 'repeating-linear-gradient(to bottom,transparent 0,transparent 3px,rgba(6,182,212,0.025) 3px,rgba(6,182,212,0.025) 4px)',
        }} />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(to left,transparent 30%,rgba(6,182,212,0.05) 100%)' }} />
        <div className="absolute top-0 left-0 w-[2px] h-full" style={{ background: 'linear-gradient(to bottom,transparent,rgba(6,182,212,0.7) 30%,rgba(99,102,241,0.9) 50%,rgba(6,182,212,0.7) 70%,transparent)', boxShadow: '0 0 16px rgba(6,182,212,0.4)' }} />
        <div className="absolute top-0 left-0 right-0 h-5" style={{ background: 'repeating-linear-gradient(45deg,transparent 0,transparent 8px,rgba(245,158,11,0.07) 8px,rgba(245,158,11,0.07) 16px)' }} />
        <div className="absolute bottom-0 left-0 right-0 h-5" style={{ background: 'repeating-linear-gradient(45deg,transparent 0,transparent 8px,rgba(245,158,11,0.07) 8px,rgba(245,158,11,0.07) 16px)' }} />
        {[[16,16],[16,'auto'],['auto',16],['auto','auto']].map(([t,b],i)=>(
          <div key={i} className="absolute w-4 h-4" style={{ top: typeof t==='number'?t:'auto', bottom: typeof b==='number'?b:'auto', left: i<2?16:'auto', right: i>=2?16:'auto' }}>
            <div className="w-full h-full rounded-full border border-cyan-500/20 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-500/30" />
            </div>
          </div>
        ))}
        <div className="absolute bottom-10 left-6 font-mono text-[8px] tracking-[0.3em] text-cyan-500/15 uppercase">GATE-R :: SECTOR-7G</div>
      </motion.div>

      {/* ── Center HUD ── */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="relative flex flex-col items-center w-[400px] max-w-[88vw]">

          {/* Rotating outer rings */}
          <div className="absolute" style={{ top: '-48px', left: '50%', transform: 'translateX(-50%)' }}>
            {[80, 100, 120].map((size, i) => (
              <motion.div
                key={i}
                className="absolute rounded-full border"
                style={{
                  width: size, height: size,
                  top: '50%', left: '50%',
                  marginTop: -size/2, marginLeft: -size/2,
                  borderColor: i===0 ? 'rgba(99,102,241,0.5)' : i===1 ? 'rgba(6,182,212,0.3)' : 'rgba(139,92,246,0.2)',
                  borderStyle: i===1 ? 'dashed' : 'solid',
                  boxShadow: i===0 ? '0 0 20px rgba(99,102,241,0.2)' : 'none',
                }}
                animate={{ rotate: i % 2 === 0 ? 360 : -360 }}
                transition={{ duration: 4 + i * 2, repeat: Infinity, ease: 'linear' }}
              />
            ))}
            {/* Center logo */}
            <motion.div
              className="absolute flex items-center justify-center rounded-2xl"
              style={{
                width: 56, height: 56,
                top: '50%', left: '50%',
                marginTop: -28, marginLeft: -28,
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6,#06b6d4)',
                boxShadow: '0 0 30px rgba(99,102,241,0.5), 0 0 60px rgba(99,102,241,0.2)',
              }}
              initial={{ scale: 0, rotate: -90 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 260, damping: 18, delay: 0.1 }}
            >
              <Zap className="w-7 h-7 text-white" />
            </motion.div>
          </div>

          {/* Title */}
          <motion.div className="mt-24 text-center mb-4"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4 }}>
            <div className="text-xl font-bold text-white tracking-tight">Agentic Platform</div>
            <div className="text-[10px] font-mono tracking-[0.35em] text-indigo-400/60 mt-0.5 uppercase">AI Operations Gateway</div>
          </motion.div>

          {/* Phase checklist */}
          <div className="w-full bg-gray-950/70 backdrop-blur-sm border border-gray-800/80 rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800/80 bg-gray-900/60">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
              </div>
              <span className="ml-2 font-mono text-[10px] text-gray-500 tracking-widest flex items-center gap-1.5">
                <Activity className="w-3 h-3" /> SYSTEM INITIALISATION
              </span>
            </div>
            <div className="px-4 py-3 space-y-2">
              {PHASES.map((p, i) => {
                const Icon = p.icon;
                const done  = i < activePhase;
                const active = i === activePhase;
                return (
                  <motion.div key={p.id} className="flex items-center gap-2.5"
                    initial={{ opacity: 0, x: -12 }}
                    animate={i <= activePhase ? { opacity: 1, x: 0 } : { opacity: 0, x: -12 }}
                    transition={{ duration: 0.2 }}>
                    <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                      {done
                        ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        : <Icon className="w-3.5 h-3.5" style={{ color: active ? p.color : 'rgba(107,114,128,0.5)' }} />
                      }
                    </div>
                    <span className="font-mono text-[11px] flex-1" style={{ color: done ? '#6ee7b7' : active ? p.color : 'rgba(107,114,128,0.6)' }}>
                      {p.label}
                    </span>
                    {active && (
                      <motion.span className="font-mono text-[9px]" style={{ color: p.color }}
                        animate={{ opacity: [1, 0.3] }} transition={{ duration: 0.4, repeat: Infinity, repeatType: 'reverse' }}>
                        ●●●
                      </motion.span>
                    )}
                    {done && <span className="font-mono text-[9px] text-emerald-400/60">OK</span>}
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full mt-3">
            <div className="flex justify-between font-mono text-[10px] mb-1 text-gray-500">
              <span>BOOT SEQUENCE</span>
              <motion.span style={{ color: progress >= 100 ? '#10b981' : '#6366f1' }}
                animate={{ opacity: [1, 0.6] }} transition={{ duration: 0.5, repeat: Infinity, repeatType: 'reverse' }}>
                {Math.floor(Math.min(progress, 100))}%
              </motion.span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-800 overflow-hidden">
              <motion.div className="h-full rounded-full"
                initial={{ width: '0%' }} animate={{ width: `${Math.min(progress, 100)}%` }}
                transition={{ duration: 0.05 }}
                style={{
                  background: progress >= 100 ? 'linear-gradient(90deg,#10b981,#06b6d4)' : 'linear-gradient(90deg,#6366f1,#8b5cf6,#06b6d4)',
                  boxShadow: progress >= 100 ? '0 0 12px rgba(16,185,129,0.5)' : '0 0 8px rgba(99,102,241,0.4)',
                }}
              />
            </div>
          </div>

          {/* System Online badge */}
          <AnimatePresence>
            {stage !== 'boot' && (
              <motion.div className="mt-3 flex items-center gap-2 px-4 py-1.5 rounded-full border font-mono text-xs font-bold tracking-[0.2em] uppercase text-emerald-400"
                initial={{ opacity: 0, scale: 0.7, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ type: 'spring', stiffness: 400, damping: 18 }}
                style={{ borderColor: 'rgba(16,185,129,0.4)', background: 'rgba(16,185,129,0.08)', boxShadow: '0 0 20px rgba(16,185,129,0.12)' }}>
                <CheckCircle2 className="w-4 h-4" />
                System Online
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

export default function App() {
  const { mode, resolved, setMode } = useTheme();
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setShowIntro(false), 3400);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden font-sans text-gray-900 dark:text-white">
      <AnimatedBackground resolved={resolved} />

      <div className="fixed top-4 right-4 z-50">
        <ThemeSwitcher mode={mode} setMode={setMode} />
      </div>

      <AnimatePresence>
        {!showIntro && (
          <motion.div className="h-full"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
            <LoginPage />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showIntro && <IntroGate onComplete={() => setShowIntro(false)} />}
      </AnimatePresence>
    </div>
  );
}

