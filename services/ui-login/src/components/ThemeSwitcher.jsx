import { motion } from 'framer-motion';
import { Monitor, Moon, Sun } from 'lucide-react';

const icons = { dark: Moon, light: Sun, auto: Monitor };
const labels = { dark: 'Dark', light: 'Light', auto: 'Auto' };

export default function ThemeSwitcher({ mode, setMode }) {
  const modes = ['dark', 'light', 'auto'];

  return (
    <div className="flex items-center gap-1 rounded-full bg-white/10 dark:bg-white/5 backdrop-blur-md p-1 border border-white/10">
      {modes.map((m) => {
        const Icon = icons[m];
        const active = mode === m;
        return (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`relative flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-300 ${
              active
                ? 'text-white'
                : 'text-gray-400 dark:text-gray-500 hover:text-gray-200'
            }`}
            aria-label={`Switch to ${labels[m]} theme`}
          >
            {active && (
              <motion.span
                layoutId="theme-pill"
                className="absolute inset-0 rounded-full bg-white/15 dark:bg-white/10 border border-white/20"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <Icon className="relative z-10 w-3.5 h-3.5" />
            <span className="relative z-10 hidden sm:inline">{labels[m]}</span>
          </button>
        );
      })}
    </div>
  );
}
