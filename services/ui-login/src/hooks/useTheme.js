import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'agentic-theme';

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

export default function useTheme() {
  const [mode, setMode] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'auto';
    } catch {
      return 'auto';
    }
  });

  const resolved = mode === 'auto' ? getSystemTheme() : mode;

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', resolved === 'dark');

    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* storage full / disabled */
    }
  }, [mode, resolved]);

  /* Listen for system preference changes when in auto mode */
  useEffect(() => {
    if (mode !== 'auto') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setMode((m) => (m === 'auto' ? 'auto' : m)); // force re-render
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [mode]);

  const cycle = useCallback(() => {
    setMode((prev) => {
      const order = ['dark', 'light', 'auto'];
      return order[(order.indexOf(prev) + 1) % order.length];
    });
  }, []);

  return { mode, resolved, setMode, cycle };
}
