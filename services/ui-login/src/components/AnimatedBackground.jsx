import { motion } from 'framer-motion';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

/*
 * Futuristic interactive background — canvas blobs track mouse,
 * hex grid highlights near cursor, particles respond to movement.
 */

const BLOBS = [
  { x: 0.15, y: 0.25, r: 350, color: [99, 102, 241], speed: 0.00015 },
  { x: 0.75, y: 0.55, r: 300, color: [168, 85, 247], speed: 0.00020 },
  { x: 0.50, y: 0.85, r: 320, color: [6, 182, 212], speed: 0.00012 },
  { x: 0.85, y: 0.15, r: 280, color: [59, 130, 246], speed: 0.00018 },
  { x: 0.25, y: 0.70, r: 260, color: [139, 92, 246], speed: 0.00022 },
  { x: 0.60, y: 0.30, r: 200, color: [236, 72, 153], speed: 0.00025 },
];

/* ── Mouse-reactive glow that follows cursor ──────────── */
function MouseGlow({ mousePos }) {
  return (
    <div
      className="absolute rounded-full pointer-events-none transition-opacity duration-500"
      style={{
        width: '500px',
        height: '500px',
        left: `${mousePos.x - 250}px`,
        top: `${mousePos.y - 250}px`,
        background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, rgba(6,182,212,0.06) 40%, transparent 70%)',
        filter: 'blur(40px)',
        opacity: mousePos.active ? 1 : 0,
      }}
    />
  );
}

/* ── Ripple effect on click ───────────────────────────── */
function ClickRipple({ ripples }) {
  return (
    <>
      {ripples.map((r) => (
        <motion.div
          key={r.id}
          className="absolute rounded-full border border-indigo-400/30 dark:border-indigo-300/20 pointer-events-none"
          initial={{ width: 0, height: 0, x: r.x, y: r.y, opacity: 0.6 }}
          animate={{ width: 300, height: 300, x: r.x - 150, y: r.y - 150, opacity: 0 }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
        />
      ))}
    </>
  );
}

function Particles({ count = 30, mousePos }) {
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        size: Math.random() * 3 + 1,
        delay: Math.random() * 12,
        duration: Math.random() * 10 + 12,
        opacity: Math.random() * 0.4 + 0.1,
      })),
    [count],
  );

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => {
        /* Parallax offset based on mouse — subtle shift */
        const mx = mousePos.active ? (mousePos.x / window.innerWidth - 0.5) * 8 * ((p.id % 3) + 1) : 0;
        const my = mousePos.active ? (mousePos.y / window.innerHeight - 0.5) * 8 * ((p.id % 3) + 1) : 0;
        return (
          <div
            key={p.id}
            className="absolute rounded-full bg-indigo-400 dark:bg-indigo-300"
            style={{
              left: `calc(${p.left}% + ${mx}px)`,
              bottom: '-4px',
              width: `${p.size}px`,
              height: `${p.size}px`,
              opacity: p.opacity,
              animation: `particle-float ${p.duration}s ease-in-out ${p.delay}s infinite`,
              transition: 'left 0.3s ease-out',
            }}
          />
        );
      })}
    </div>
  );
}

function OrbitalRings({ mousePos }) {
  const mx = mousePos.active ? (mousePos.x / window.innerWidth - 0.5) * 20 : 0;
  const my = mousePos.active ? (mousePos.y / window.innerHeight - 0.5) * 20 : 0;

  const rings = [
    { size: 600, border: 'border-indigo-500/10 dark:border-indigo-400/[0.07]', dur: '25s', delay: '0s', parallax: 1 },
    { size: 450, border: 'border-purple-500/10 dark:border-purple-400/[0.07]', dur: '20s', delay: '-5s', parallax: 1.5 },
    { size: 320, border: 'border-cyan-500/[0.08] dark:border-cyan-400/[0.05]', dur: '30s', delay: '-10s', parallax: 2 },
  ];
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {rings.map((r, i) => (
        <div
          key={i}
          className={`absolute rounded-full border ${r.border}`}
          style={{
            width: `${r.size}px`,
            height: `${r.size}px`,
            animation: `orbit ${r.dur} linear ${r.delay} infinite`,
            transform: `translate(${mx * r.parallax}px, ${my * r.parallax}px)`,
            transition: 'transform 0.4s ease-out',
          }}
        >
          <div
            className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-indigo-400/40 dark:bg-indigo-300/30 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
          />
        </div>
      ))}
    </div>
  );
}

function ScanLine() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <motion.div
        className="absolute left-0 right-0 h-[2px]"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.5), rgba(6,182,212,0.5), transparent)',
          boxShadow: '0 0 20px 4px rgba(99,102,241,0.2)',
        }}
        animate={{ top: ['-2px', '100%'] }}
        transition={{ duration: 5, ease: 'easeInOut', repeat: Infinity, repeatDelay: 2 }}
      />
    </div>
  );
}

function HexGrid({ mousePos }) {
  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-[0.035] dark:opacity-[0.06]" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="hex" width="56" height="100" patternUnits="userSpaceOnUse" patternTransform="scale(1.5)">
          <path d="M28 66L0 50L0 16L28 0L56 16L56 50L28 66L28 100" fill="none" stroke="currentColor" strokeWidth="0.5" />
          <path d="M28 0L28 34L0 50L0 84L28 100L56 84L56 50L28 34" fill="none" stroke="currentColor" strokeWidth="0.5" />
        </pattern>
        {/* Radial highlight near mouse */}
        <radialGradient id="hex-highlight" cx={mousePos.active ? mousePos.x / window.innerWidth : 0.5} cy={mousePos.active ? mousePos.y / window.innerHeight : 0.5} r="0.25">
          <stop offset="0%" stopColor="currentColor" stopOpacity={mousePos.active ? 0.4 : 0} />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#hex)" className="text-indigo-500" />
      <rect width="100%" height="100%" fill="url(#hex-highlight)" className="text-indigo-400 transition-opacity duration-300" />
    </svg>
  );
}

export default function AnimatedBackground({ resolved }) {
  const canvasRef = useRef(null);
  const frameRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0, active: false });
  const [mousePos, setMousePos] = useState({ x: 0, y: 0, active: false });
  const [ripples, setRipples] = useState([]);

  /* ── Track mouse position ───────────────────────────── */
  const handleMouseMove = useCallback((e) => {
    mouseRef.current = { x: e.clientX, y: e.clientY, active: true };
    setMousePos({ x: e.clientX, y: e.clientY, active: true });
  }, []);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = { ...mouseRef.current, active: false };
    setMousePos((p) => ({ ...p, active: false }));
  }, []);

  const handleClick = useCallback((e) => {
    const id = Date.now();
    setRipples((prev) => [...prev.slice(-4), { id, x: e.clientX, y: e.clientY }]);
    setTimeout(() => setRipples((prev) => prev.filter((r) => r.id !== id)), 1300);
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    window.addEventListener('click', handleClick);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('click', handleClick);
    };
  }, [handleMouseMove, handleMouseLeave, handleClick]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let w, h;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    const dark = resolved === 'dark';

    const draw = (time) => {
      ctx.fillStyle = dark ? '#030712' : '#f0f4ff';
      ctx.fillRect(0, 0, w, h);

      const m = mouseRef.current;

      for (const blob of BLOBS) {
        /* Base animation + mouse attraction */
        let cx = w * blob.x + Math.sin(time * blob.speed * 1.3) * w * 0.08;
        let cy = h * blob.y + Math.cos(time * blob.speed) * h * 0.08;

        /* Gently attract blobs toward cursor */
        if (m.active) {
          const dx = m.x - cx;
          const dy = m.y - cy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const pull = Math.max(0, 1 - dist / 600) * 0.15;
          cx += dx * pull;
          cy += dy * pull;
        }

        const r = blob.r * (Math.min(w, h) / 900);
        const [cr, cg, cb] = blob.color;
        const alpha = dark ? 0.18 : 0.10;

        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
        grad.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);
      }

      frameRef.current = requestAnimationFrame(draw);
    };

    frameRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [resolved]);

  return (
    <>
      {/* Base canvas blobs — interactive with mouse */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 -z-10"
        style={{ width: '100%', height: '100%' }}
      />

      {/* Mouse-following glow */}
      <div className="fixed inset-0 -z-[9] pointer-events-none">
        <MouseGlow mousePos={mousePos} />
      </div>

      {/* Click ripples */}
      <div className="fixed inset-0 -z-[9] pointer-events-none">
        <ClickRipple ripples={ripples} />
      </div>

      {/* Hex grid overlay — highlights near cursor */}
      <div className="fixed inset-0 -z-[8]">
        <HexGrid mousePos={mousePos} />
      </div>

      {/* Perspective grid — fading from bottom */}
      <div className="fixed inset-0 -z-[7] perspective-grid" style={{ maskImage: 'linear-gradient(to top, rgba(0,0,0,0.4) 0%, transparent 60%)', WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,0.4) 0%, transparent 60%)' }} />

      {/* Orbital rings — parallax with mouse */}
      <div className="fixed inset-0 -z-[6]">
        <OrbitalRings mousePos={mousePos} />
      </div>

      {/* Floating particles — parallax with mouse */}
      <div className="fixed inset-0 -z-[5]">
        <Particles mousePos={mousePos} />
      </div>

      {/* Scan line */}
      <div className="fixed inset-0 -z-[4]">
        <ScanLine />
      </div>

      {/* Corner accents */}
      <div className="fixed top-0 left-0 w-32 h-32 -z-[3] pointer-events-none">
        <div className="absolute top-4 left-4 w-16 h-[1px] bg-gradient-to-r from-indigo-500/40 to-transparent" />
        <div className="absolute top-4 left-4 w-[1px] h-16 bg-gradient-to-b from-indigo-500/40 to-transparent" />
      </div>
      <div className="fixed bottom-0 right-0 w-32 h-32 -z-[3] pointer-events-none">
        <div className="absolute bottom-4 right-4 w-16 h-[1px] bg-gradient-to-l from-cyan-500/40 to-transparent" />
        <div className="absolute bottom-4 right-4 w-[1px] h-16 bg-gradient-to-t from-cyan-500/40 to-transparent" />
      </div>

      {/* Vignette */}
      <div className="fixed inset-0 -z-[2] pointer-events-none" style={{ background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.3) 100%)' }} />
    </>
  );
}
