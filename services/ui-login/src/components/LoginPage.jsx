import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, Eye, EyeOff, Info, Loader2, X, Zap } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

/* ── In production the login app is served from the console itself,
   so all API calls are same-origin.  In dev (Vite) we proxy to the
   console at port 3000 which already proxies to the agent-service. */
const CONSOLE_URL = import.meta.env.PROD ? '' : 'http://localhost:3000';
const API_BASE = CONSOLE_URL; /* agent-service API (for register, forgot-pw) */

/* ── Overlay modal shell ───────────────────────────────── */
function Modal({ open, onClose, children }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed inset-0 z-[61] flex items-center justify-center px-4 pointer-events-none"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="pointer-events-auto relative w-full max-w-md rounded-2xl border border-white/20 dark:border-white/10 bg-white/80 dark:bg-gray-900/90 backdrop-blur-2xl shadow-2xl overflow-hidden">
              <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-indigo-400/70 dark:via-indigo-400/50 to-transparent" />
              <button
                onClick={onClose}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="px-8 pt-8 pb-8 sm:px-10">{children}</div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/* ── Toast notification ────────────────────────────────── */
function Toast({ message, show, onDone }) {
  useEffect(() => {
    if (show) {
      const t = setTimeout(onDone, 3000);
      return () => clearTimeout(t);
    }
  }, [show, onDone]);
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70] flex items-center gap-2 rounded-xl border border-white/20 dark:border-white/10 bg-white/80 dark:bg-gray-900/90 backdrop-blur-2xl shadow-2xl px-5 py-3"
        >
          <Info className="w-4 h-4 text-indigo-500 dark:text-indigo-400 shrink-0" />
          <span className="text-sm text-gray-700 dark:text-gray-300">{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ── Glass input ───────────────────────────────────────── */
function GlassInput({ label, type = 'text', value, onChange, placeholder, required, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">
        {label}
      </label>
      <div className="neon-ring rounded-xl">
        <div className="relative">
          <input
            type={type}
            value={value}
            onChange={onChange}
            required={required}
            placeholder={placeholder}
            className="w-full rounded-xl border border-white/30 dark:border-white/10 bg-white/50 dark:bg-white/[0.04] px-4 py-3 pr-11 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none transition-all duration-300 focus:border-indigo-400/50 dark:focus:border-indigo-400/30 focus:bg-white/70 dark:focus:bg-white/[0.07]"
          />
          {children}
        </div>
      </div>
    </div>
  );
}

/* ── Forgot-password modal ─────────────────────────────── */
function ForgotPasswordModal({ open, onClose }) {
  const [identifier, setIdentifier] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [foundUser, setFoundUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetDone, setResetDone] = useState(false);

  const handleLookup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || data.detail || 'User not found');
      }
      setFoundUser(data);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: foundUser.id, new_password: newPassword }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.detail || 'Reset failed');
      setResetDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onClose();
    setTimeout(() => { setSent(false); setIdentifier(''); setError(''); setFoundUser(null); setNewPassword(''); setConfirmPassword(''); setResetDone(false); }, 300);
  };

  return (
    <Modal open={open} onClose={handleClose}>
      {resetDone ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-center py-4">
          <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Password reset!</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">You can now sign in with your new password.</p>
          <button onClick={handleClose} className="text-sm font-medium text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors">
            Back to sign in
          </button>
        </motion.div>
      ) : sent ? (
        <>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Set new password</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            Account found: <span className="font-medium text-gray-700 dark:text-gray-200">{foundUser?.username}</span>
            {foundUser?.email && <span className="text-gray-400"> ({foundUser.email})</span>}
          </p>
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 px-4 py-2.5 text-sm text-red-600 dark:text-red-400">{error}</motion.div>
            )}
          </AnimatePresence>
          <form onSubmit={handleResetPassword} className="space-y-4">
            <GlassInput label="New password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Min. 8 characters" required />
            <GlassInput label="Confirm password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Re-enter password" required />
            <SubmitButton loading={loading} text="Reset password" />
          </form>
        </>
      ) : (
        <>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Reset password</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            Enter your username or email to find your account.
          </p>
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 px-4 py-2.5 text-sm text-red-600 dark:text-red-400">{error}</motion.div>
            )}
          </AnimatePresence>
          <form onSubmit={handleLookup} className="space-y-5">
            <GlassInput
              label="Username or Email"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="admin or you@company.com"
              required
            />
            <SubmitButton loading={loading} text="Find account" />
          </form>
        </>
      )}
    </Modal>
  );
}

/* ── Sign-up modal ─────────────────────────────────────── */
function SignUpModal({ open, onClose }) {
  const [form, setForm] = useState({ name: '', username: '', email: '', password: '', confirm: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState('form'); // 'form' | 'verify' | 'done'
  const [userId, setUserId] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [displayCode, setDisplayCode] = useState('');

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (!form.email) {
      setError('Email is required.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.username,
          password: form.password,
          display_name: form.name,
          email: form.email,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || data.detail || 'Registration failed');
      }
      const data = await res.json();
      setUserId(data.id);
      // Show the verification code (in production this would be sent via email)
      setDisplayCode(data.verification_code || '');
      setStep('verify');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    if (verifyCode.length !== 6) {
      setError('Please enter the 6-digit code.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, code: verifyCode }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Verification failed');
      }
      setStep('done');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    try {
      const res = await fetch(`${API_BASE}/auth/resend-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Failed to resend');
      setDisplayCode(data.verification_code || '');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleClose = () => {
    onClose();
    setTimeout(() => { setStep('form'); setError(''); setForm({ name: '', username: '', email: '', password: '', confirm: '' }); setVerifyCode(''); setDisplayCode(''); setUserId(''); }, 300);
  };

  return (
    <Modal open={open} onClose={handleClose}>
      {step === 'done' ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-4"
        >
          <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Email verified!</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Your account is ready. You can now sign in.</p>
          <button
            onClick={handleClose}
            className="text-sm font-medium text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
          >
            Back to sign in
          </button>
        </motion.div>
      ) : step === 'verify' ? (
        <>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Verify your email</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
            Enter the 6-digit verification code to activate your account.
          </p>
          {displayCode && (
            <div className="mb-4 rounded-lg border border-indigo-300/40 dark:border-indigo-500/20 bg-indigo-50/80 dark:bg-indigo-500/10 px-4 py-2.5 text-sm text-indigo-700 dark:text-indigo-300">
              <span className="font-medium">Your code:</span> <span className="font-mono font-bold text-lg tracking-widest">{displayCode}</span>
              <br /><span className="text-xs opacity-70">(In production, this would be sent to your email)</span>
            </div>
          )}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 px-4 py-2.5 text-sm text-red-600 dark:text-red-400">{error}</motion.div>
            )}
          </AnimatePresence>
          <form onSubmit={handleVerify} className="space-y-4">
            <GlassInput label="Verification code" value={verifyCode} onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" required />
            <SubmitButton loading={loading} text="Verify email" />
          </form>
          <p className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
            Didn&apos;t receive the code?{' '}
            <button type="button" onClick={handleResend} className="font-medium text-indigo-500 dark:text-indigo-400 hover:underline">Resend code</button>
          </p>
        </>
      ) : (
        <>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Create account</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Join the Agentic Platform.</p>
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 px-4 py-2.5 text-sm text-red-600 dark:text-red-400"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>
          <form onSubmit={handleSubmit} className="space-y-4">
            <GlassInput label="Full name" value={form.name} onChange={set('name')} placeholder="Jane Doe" required />
            <GlassInput label="Username" value={form.username} onChange={set('username')} placeholder="janedoe" required />
            <GlassInput label="Email" type="email" value={form.email} onChange={set('email')} placeholder="you@company.com" required />
            <GlassInput label="Password" type="password" value={form.password} onChange={set('password')} placeholder="Min. 8 characters" required />
            <GlassInput label="Confirm password" type="password" value={form.confirm} onChange={set('confirm')} placeholder="Re-enter password" required />
            <SubmitButton loading={loading} text="Create account" />
          </form>
        </>
      )}
    </Modal>
  );
}

/* ── Verify email modal (shown when login blocked due to unverified email) ── */
function VerifyFromLoginModal({ open, userId, email, onClose }) {
  const [code, setCode] = useState('');
  const [displayCode, setDisplayCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    if (code.length !== 6) { setError('Please enter the 6-digit code.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, code }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Verification failed');
      }
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    try {
      const res = await fetch(`${API_BASE}/auth/resend-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Failed to resend');
      setDisplayCode(data.verification_code || '');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleClose = () => {
    onClose();
    setTimeout(() => { setCode(''); setError(''); setDone(false); setDisplayCode(''); }, 300);
  };

  return (
    <Modal open={open} onClose={handleClose}>
      {done ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-center py-4">
          <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Email verified!</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">You can now sign in with your credentials.</p>
          <button onClick={handleClose} className="text-sm font-medium text-indigo-500 hover:text-indigo-600 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors">
            Back to sign in
          </button>
        </motion.div>
      ) : (
        <>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Verify your email</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Your email <span className="font-medium text-gray-700 dark:text-gray-200">{email}</span> must be verified before you can sign in.
          </p>
          {displayCode && (
            <div className="mb-4 rounded-lg border border-indigo-300/40 dark:border-indigo-500/20 bg-indigo-50/80 dark:bg-indigo-500/10 px-4 py-2.5 text-sm text-indigo-700 dark:text-indigo-300">
              <span className="font-medium">Your code:</span> <span className="font-mono font-bold text-lg tracking-widest">{displayCode}</span>
            </div>
          )}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="mb-4 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 px-4 py-2.5 text-sm text-red-600 dark:text-red-400">{error}</motion.div>
            )}
          </AnimatePresence>
          <form onSubmit={handleVerify} className="space-y-4">
            <GlassInput label="Verification code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" required />
            <SubmitButton loading={loading} text="Verify email" />
          </form>
          <p className="mt-4 text-center text-xs text-gray-500 dark:text-gray-400">
            Need a code?{' '}
            <button type="button" onClick={handleResend} className="font-medium text-indigo-500 dark:text-indigo-400 hover:underline">Send verification code</button>
          </p>
        </>
      )}
    </Modal>
  );
}

/* ── Shared submit button ──────────────────────────────── */
function SubmitButton({ loading, text }) {
  return (
    <motion.button
      type="submit"
      disabled={loading}
      whileHover={loading ? {} : { scale: 1.01 }}
      whileTap={loading ? {} : { scale: 0.98 }}
      className="relative w-full rounded-xl py-3.5 text-sm font-semibold text-white overflow-hidden transition-all duration-300 disabled:opacity-70 disabled:cursor-not-allowed group"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 bg-[length:200%_100%] group-hover:animate-shimmer" />
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-r from-indigo-500/0 via-white/20 to-indigo-500/0" />
      <div className="absolute -inset-1 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 group-hover:opacity-30 blur-lg transition-opacity duration-500" />
      <span className="relative z-10 flex items-center justify-center gap-2">
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" />Please wait…</> : text}
      </span>
    </motion.button>
  );
}

/* ── Main login page ───────────────────────────────────── */
export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForgot, setShowForgot] = useState(false);
  const [showSignUp, setShowSignUp] = useState(false);
  const [toast, setToast] = useState('');
  const [verifyModal, setVerifyModal] = useState(null); // { userId, email }
  const [gateOpen, setGateOpen] = useState(false);

  /* ── Remember me: restore saved credentials ──────────── */
  useEffect(() => {
    try {
      const saved = localStorage.getItem('agentic-remember');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.username) setUsername(parsed.username);
        if (parsed.password) setPassword(parsed.password);
        setRemember(true);
      }
    } catch { /* ignore */ }
  }, []);

  /* ── Login handler — authenticates via console to set session cookie ── */
  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      /* Call the console's /auth/login so the session cookie is set */
      const res = await fetch(`${CONSOLE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 403 && data.code === 'email_not_verified') {
          // Show verification modal
          setVerifyModal({ userId: data.user_id, email: data.email });
          setLoading(false);
          return;
        }
        if (res.status === 429) {
          throw new Error(data.error || 'Too many login attempts. Try again later.');
        }
        const remaining = data.remaining_attempts;
        const msg = remaining != null
          ? `Invalid credentials. ${remaining} attempt${remaining !== 1 ? 's' : ''} remaining.`
          : (data.error || data.detail || 'Invalid credentials.');
        throw new Error(msg);
      }

      /* Persist remember-me */
      if (remember) {
        localStorage.setItem('agentic-remember', JSON.stringify({ username, password }));
      } else {
        localStorage.removeItem('agentic-remember');
      }

      /* Trigger dramatic gate animation, then redirect */
      setLoading(false);
      setGateOpen(true);
      setTimeout(() => { window.location.href = '/'; }, 1400);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [username, password, remember]);

  /* ── Social login handler ────────────────────────────── */
  const handleSocialLogin = useCallback((provider) => {
    setToast(`${provider} SSO is coming soon. Use username/password for now.`);
  }, []);

  /* ── Card animation variants ─────────────────────────── */
  const cardVariants = {
    hidden: { opacity: 0, y: 30, scale: 0.96 },
    visible: {
      opacity: 1, y: 0, scale: 1,
      transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] },
    },
  };

  return (
    <>
      <div className="relative flex h-full items-center justify-center px-4">
        {/* ── Radial glow behind card ────────────────────── */}
        {!gateOpen && (
          <>
            <div className="pointer-events-none absolute w-[500px] h-[500px] rounded-full bg-indigo-500/20 dark:bg-indigo-500/15 blur-[120px] animate-glow-pulse" />
            <div className="pointer-events-none absolute w-[400px] h-[400px] rounded-full bg-cyan-400/15 dark:bg-cyan-400/10 blur-[100px] translate-x-32 translate-y-20 animate-glow-pulse [animation-delay:1.5s]" />
          </>
        )}

        {/* ── Glass card ─────────────────────────────────── */}
        <motion.div
          variants={cardVariants}
          initial="hidden"
          animate={gateOpen ? 'hidden' : 'visible'}
          className="relative w-full max-w-md"
          style={gateOpen ? { opacity: 0, pointerEvents: 'none' } : undefined}
        >
          {/* Outer neon border glow */}
          <div className="absolute -inset-[1px] rounded-2xl bg-gradient-to-br from-indigo-500/30 via-purple-500/20 to-cyan-500/30 dark:from-indigo-500/25 dark:via-purple-500/15 dark:to-cyan-500/25 blur-[2px]" />

          <div className="relative rounded-2xl border border-white/20 dark:border-white/10 bg-white/60 dark:bg-white/[0.06] backdrop-blur-2xl shadow-[0_8px_60px_-12px_rgba(99,102,241,0.25)] dark:shadow-[0_8px_60px_-12px_rgba(99,102,241,0.15)] overflow-hidden">
            {/* Top shimmer accent bar */}
            <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-indigo-400/70 dark:via-indigo-400/50 to-transparent" />

            <div className="px-8 pt-10 pb-10 sm:px-10">
              {/* ── Logo / Brand ───────────────────────────── */}
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.5 }}
                className="flex flex-col items-center mb-8"
              >
                <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30 mb-4">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
                  Agentic Platform
                </h1>
                <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
                  Welcome back — sign in to continue
                </p>
              </motion.div>

              {/* ── Error message ───────────────────────────── */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-5 rounded-lg border border-red-300/40 dark:border-red-500/20 bg-red-50/80 dark:bg-red-500/10 backdrop-blur px-4 py-2.5 text-sm text-red-600 dark:text-red-400"
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* ── Form ────────────────────────────────────── */}
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Username / Email */}
                <GlassInput
                  label="Username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  required
                />

                {/* Password */}
                <GlassInput
                  label="Password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                >
                  <button
                    type="button"
                    onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-indigo-400 hover:text-indigo-500 dark:text-indigo-300 dark:hover:text-indigo-200 transition-colors"
                    aria-label={showPw ? 'Hide password' : 'Show password'}
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </GlassInput>

                {/* Remember + Forgot */}
                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setRemember(checked);
                        if (checked && username) {
                          localStorage.setItem('agentic-remember', JSON.stringify({ username, password }));
                        } else if (!checked) {
                          localStorage.removeItem('agentic-remember');
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 dark:border-white/20 bg-white/50 dark:bg-white/[0.04] text-indigo-500 focus:ring-indigo-500/30 transition-all cursor-pointer"
                    />
                    <span className="text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors select-none">
                      Remember me
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowForgot(true)}
                    className="text-indigo-500 dark:text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 font-medium transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>

                {/* Submit */}
                <SubmitButton loading={loading} text="Sign in" />
              </form>

              {/* ── Divider ──────────────────────────────────── */}
              <div className="relative my-7">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200/60 dark:border-white/10" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-3 text-xs text-gray-400 dark:text-gray-500 bg-white/60 dark:bg-transparent backdrop-blur-sm rounded">
                    or continue with
                  </span>
                </div>
              </div>

              {/* ── Social buttons ────────────────────────────── */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { name: 'Google', icon: GoogleIcon },
                  { name: 'GitHub', icon: GitHubIcon },
                  { name: 'Microsoft', icon: MicrosoftIcon },
                ].map(({ name, icon: Icon }) => (
                  <motion.button
                    key={name}
                    type="button"
                    onClick={() => handleSocialLogin(name)}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    className="flex items-center justify-center gap-2 rounded-xl border border-white/25 dark:border-white/10 bg-white/40 dark:bg-white/[0.04] py-2.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-white/60 dark:hover:bg-white/[0.08] transition-all duration-200"
                    aria-label={`Sign in with ${name}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">{name}</span>
                  </motion.button>
                ))}
              </div>

              {/* ── Sign up link ──────────────────────────────── */}
              <p className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  onClick={() => setShowSignUp(true)}
                  className="font-semibold text-indigo-500 dark:text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors"
                >
                  Sign up
                </button>
              </p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* ── Modals ────────────────────────────────────────── */}
      <ForgotPasswordModal open={showForgot} onClose={() => setShowForgot(false)} />
      <SignUpModal open={showSignUp} onClose={() => setShowSignUp(false)} />
      {verifyModal && (
        <VerifyFromLoginModal
          open={!!verifyModal}
          userId={verifyModal.userId}
          email={verifyModal.email}
          onClose={() => setVerifyModal(null)}
        />
      )}
      <Toast message={toast} show={!!toast} onDone={() => setToast('')} />

      {/* ── Cinematic Vault Gate Transition ─────────────────── */}
      <AnimatePresence>
        {gateOpen && (() => {
          const isDark = document.documentElement.classList.contains('dark');
          const bg = isDark
            ? 'radial-gradient(ellipse at center, #0c1222 0%, #070b14 100%)'
            : 'radial-gradient(ellipse at center, #f1f5f9 0%, #e2e8f0 100%)';
          const panelBgL = isDark
            ? 'linear-gradient(160deg, #0e1525 0%, #141d2f 40%, #0e1525 100%)'
            : 'linear-gradient(160deg, #e2e8f0 0%, #f1f5f9 40%, #e2e8f0 100%)';
          const panelBgR = isDark
            ? 'linear-gradient(200deg, #0e1525 0%, #141d2f 40%, #0e1525 100%)'
            : 'linear-gradient(200deg, #e2e8f0 0%, #f1f5f9 40%, #e2e8f0 100%)';
          const panelBorder = isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.2)';
          const panelShadowL = isDark
            ? '6px 0 60px rgba(99,102,241,0.15), inset -1px 0 0 rgba(99,102,241,0.1)'
            : '6px 0 60px rgba(99,102,241,0.1), inset -1px 0 0 rgba(99,102,241,0.08)';
          const panelShadowR = isDark
            ? '-6px 0 60px rgba(99,102,241,0.15), inset 1px 0 0 rgba(99,102,241,0.1)'
            : '-6px 0 60px rgba(99,102,241,0.1), inset 1px 0 0 rgba(99,102,241,0.08)';
          const circuitColor = isDark ? '#6366f1' : '#818cf8';
          const circuitOpacity = isDark ? '0.03' : '0.06';
          const seamColor = isDark
            ? 'linear-gradient(to bottom, transparent 5%, rgba(6,182,212,0.7) 25%, rgba(99,102,241,0.9) 50%, rgba(6,182,212,0.7) 75%, transparent 95%)'
            : 'linear-gradient(to bottom, transparent 5%, rgba(79,70,229,0.5) 25%, rgba(99,102,241,0.7) 50%, rgba(79,70,229,0.5) 75%, transparent 95%)';
          const lockBarBg = isDark ? 'rgba(6,182,212,0.8)' : 'rgba(79,70,229,0.6)';
          const lockBarShadow = isDark ? '0 0 8px rgba(6,182,212,0.4)' : '0 0 8px rgba(79,70,229,0.3)';
          const centerSeamBg = isDark
            ? 'linear-gradient(to bottom, transparent 3%, rgba(6,182,212,0.9) 15%, rgba(99,102,241,1) 50%, rgba(6,182,212,0.9) 85%, transparent 97%)'
            : 'linear-gradient(to bottom, transparent 3%, rgba(79,70,229,0.6) 15%, rgba(99,102,241,0.8) 50%, rgba(79,70,229,0.6) 85%, transparent 97%)';
          const centerSeamShadow = isDark
            ? '0 0 20px rgba(99,102,241,0.6), 0 0 60px rgba(6,182,212,0.3)'
            : '0 0 20px rgba(99,102,241,0.3), 0 0 60px rgba(79,70,229,0.15)';
          const auraBg = isDark
            ? 'linear-gradient(to bottom, transparent 10%, rgba(99,102,241,0.15) 30%, rgba(6,182,212,0.2) 50%, rgba(99,102,241,0.15) 70%, transparent 90%)'
            : 'linear-gradient(to bottom, transparent 10%, rgba(99,102,241,0.08) 30%, rgba(79,70,229,0.12) 50%, rgba(99,102,241,0.08) 70%, transparent 90%)';
          const ringBorder = isDark ? 'rgba(6,182,212,0.5)' : 'rgba(79,70,229,0.35)';
          const ringShadow = isDark
            ? '0 0 30px rgba(6,182,212,0.2), inset 0 0 30px rgba(99,102,241,0.1)'
            : '0 0 30px rgba(79,70,229,0.15), inset 0 0 30px rgba(99,102,241,0.05)';
          const subtitleColor = isDark ? 'rgba(6,182,212,0.6)' : 'rgba(79,70,229,0.6)';
          const dotBg = isDark ? '#06b6d4' : '#6366f1';
          const dotShadow = isDark ? '0 0 6px rgba(6,182,212,0.5)' : '0 0 6px rgba(99,102,241,0.4)';
          const stripeOpacity = isDark ? '0.06' : '0.08';
          const chevronClass = isDark ? 'text-indigo-400' : 'text-indigo-500';
          const scanlinesBg = isDark
            ? 'repeating-linear-gradient(to bottom, transparent 0, transparent 2px, rgba(99,102,241,0.02) 2px, rgba(99,102,241,0.02) 4px)'
            : 'repeating-linear-gradient(to bottom, transparent 0, transparent 2px, rgba(99,102,241,0.03) 2px, rgba(99,102,241,0.03) 4px)';
          const sheenColor = isDark
            ? 'linear-gradient(105deg, transparent 40%, rgba(99,102,241,0.06) 45%, rgba(255,255,255,0.03) 50%, rgba(99,102,241,0.06) 55%, transparent 60%)'
            : 'linear-gradient(105deg, transparent 40%, rgba(99,102,241,0.08) 45%, rgba(255,255,255,0.06) 50%, rgba(99,102,241,0.08) 55%, transparent 60%)';
          const techTextColor = isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.35)';
          const boltColor = isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.2)';
          const boltInner = isDark ? 'rgba(6,182,212,0.3)' : 'rgba(79,70,229,0.25)';
          const scanBeamColor = isDark
            ? 'linear-gradient(to bottom, transparent, rgba(6,182,212,0.15), rgba(99,102,241,0.08), transparent)'
            : 'linear-gradient(to bottom, transparent, rgba(79,70,229,0.12), rgba(99,102,241,0.06), transparent)';
          const innerGlowL = isDark
            ? 'linear-gradient(to left, rgba(99,102,241,0.08) 0%, transparent 60%)'
            : 'linear-gradient(to left, rgba(99,102,241,0.06) 0%, transparent 60%)';
          const innerGlowR = isDark
            ? 'linear-gradient(to right, rgba(99,102,241,0.08) 0%, transparent 60%)'
            : 'linear-gradient(to right, rgba(99,102,241,0.06) 0%, transparent 60%)';

          /* Shared panel inner content renderer */
          const PanelInner = ({ side }) => {
            const isLeft = side === 'left';
            return (
              <div className="absolute inset-0 overflow-hidden">
                {/* Circuit board pattern */}
                <svg className="absolute inset-0 w-full h-full" style={{ opacity: circuitOpacity }} xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <pattern id={`circuit-${side[0]}`} width="80" height="80" patternUnits="userSpaceOnUse">
                      <path d="M40 0v20M40 60v20M0 40h20M60 40h80M40 20a4 4 0 1 0 0 0.01M40 60a4 4 0 1 0 0 0.01M20 40a4 4 0 1 0 0 0.01M60 40a4 4 0 1 0 0 0.01M20 40h20v20M60 40h-20v-20" fill="none" stroke={circuitColor} strokeWidth="0.5"/>
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill={`url(#circuit-${side[0]})`}/>
                </svg>

                {/* Horizontal scanlines overlay */}
                <div className="absolute inset-0" style={{ background: scanlinesBg }} />

                {/* Metallic sheen sweep */}
                <motion.div
                  className="absolute inset-0"
                  initial={{ x: '-100%' }}
                  animate={{ x: '200%' }}
                  transition={{ duration: 0.8, delay: 0.05, ease: 'easeInOut' }}
                  style={{ background: sheenColor }}
                />

                {/* Inner glow near seam edge */}
                <div className="absolute inset-0" style={{ background: isLeft ? innerGlowL : innerGlowR }} />

                {/* Vertical scan beam */}
                <motion.div
                  className="absolute top-0 h-full"
                  initial={{ [isLeft ? 'right' : 'left']: '100%', opacity: 0 }}
                  animate={{ [isLeft ? 'right' : 'left']: '-10%', opacity: [0, 0.8, 0] }}
                  transition={{ duration: 0.6, delay: 0.08, ease: 'linear' }}
                  style={{ width: '40px', background: scanBeamColor }}
                />

                {/* Glowing edge seam */}
                <motion.div
                  className={`absolute top-0 ${isLeft ? 'right-0' : 'left-0'} w-[3px] h-full`}
                  initial={{ opacity: 0.5 }}
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 0.5, repeat: 1 }}
                  style={{ background: seamColor }}
                />
                {/* Secondary edge highlight */}
                <div className={`absolute top-0 ${isLeft ? 'right-[3px]' : 'left-[3px]'} w-[1px] h-full`}
                  style={{ background: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.08)' }} />

                {/* Horizontal lock bars — thicker, with glow trail */}
                {[0.15, 0.3, 0.45, 0.55, 0.7, 0.85].map((pos, i) => (
                  <motion.div
                    key={`lb-${side[0]}-${i}`}
                    className={`absolute ${isLeft ? 'right-0' : 'left-0'}`}
                    initial={{ width: '80px', opacity: 0.6 }}
                    animate={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.25, delay: 0.05 + i * 0.04, ease: 'easeIn' }}
                    style={{
                      top: `${pos * 100}%`,
                      height: '4px',
                      borderRadius: '2px',
                      background: `linear-gradient(${isLeft ? 'to left' : 'to right'}, ${lockBarBg}, transparent)`,
                      boxShadow: `${lockBarShadow}, 0 0 16px ${isDark ? 'rgba(6,182,212,0.15)' : 'rgba(79,70,229,0.1)'}`,
                    }}
                  />
                ))}

                {/* Corner bolt decorations */}
                {[[16, 16], [16, null], [null, 16], [null, null]].map(([top, left], i) => (
                  <div key={`bolt-${side[0]}-${i}`} className="absolute" style={{
                    top: top != null ? `${top}px` : 'auto',
                    bottom: top == null ? '16px' : 'auto',
                    left: left != null ? `${left}px` : 'auto',
                    right: left == null ? '16px' : 'auto',
                  }}>
                    <div className="w-4 h-4 rounded-full border" style={{ borderColor: boltColor }}>
                      <div className="w-2 h-2 rounded-full m-[3px]" style={{ background: boltInner }} />
                    </div>
                  </div>
                ))}

                {/* Tech readout text */}
                <div className={`absolute ${isLeft ? 'right-8' : 'left-8'} top-1/2 -translate-y-1/2 flex flex-col gap-3 ${isLeft ? 'items-end text-right' : 'items-start text-left'}`}>
                  {[
                    { label: 'CLEARANCE', value: 'GRANTED' },
                    { label: 'AUTH LEVEL', value: 'VERIFIED' },
                    { label: 'PROTOCOL', value: 'SECURE' },
                    { label: 'INTEGRITY', value: '100%' },
                  ].map((item, i) => (
                    <motion.div
                      key={`tech-${side[0]}-${i}`}
                      initial={{ opacity: 0, x: isLeft ? 10 : -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2, delay: 0.02 + i * 0.04 }}
                      className="font-mono"
                    >
                      <div className="text-[8px] tracking-[0.2em] uppercase" style={{ color: techTextColor }}>{item.label}</div>
                      <div className="text-[10px] tracking-[0.15em] font-semibold" style={{ color: isDark ? 'rgba(6,182,212,0.4)' : 'rgba(79,70,229,0.45)' }}>{item.value}</div>
                    </motion.div>
                  ))}
                </div>

                {/* Chevron marks near seam */}
                <div className={`absolute top-1/2 -translate-y-1/2 ${isLeft ? 'right-3' : 'left-3'} flex flex-col gap-1 ${isLeft ? 'items-end' : 'items-start'} opacity-15`}>
                  {[...Array(7)].map((_, i) => (
                    <motion.div
                      key={`ch-${side[0]}-${i}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.1, delay: i * 0.02 }}
                      className={`${chevronClass} text-[10px] font-mono`}
                    >{isLeft ? '\u203A' : '\u2039'}</motion.div>
                  ))}
                </div>

                {/* Warning stripes */}
                <div className="absolute bottom-0 left-0 right-0 h-6"
                  style={{ opacity: stripeOpacity, background: `repeating-linear-gradient(${isLeft ? '135deg' : '45deg'}, #f59e0b 0, #f59e0b 8px, transparent 8px, transparent 16px)` }} />
                <div className="absolute top-0 left-0 right-0 h-6"
                  style={{ opacity: stripeOpacity, background: `repeating-linear-gradient(${isLeft ? '135deg' : '45deg'}, #f59e0b 0, #f59e0b 8px, transparent 8px, transparent 16px)` }} />

                {/* Panel ID label */}
                <div className={`absolute bottom-10 ${isLeft ? 'left-6' : 'right-6'} font-mono text-[8px] tracking-[0.3em] uppercase`}
                  style={{ color: isDark ? 'rgba(99,102,241,0.12)' : 'rgba(99,102,241,0.15)' }}>
                  {isLeft ? 'GATE-L :: SEC-7' : 'GATE-R :: SEC-7'}
                </div>
              </div>
            );
          };

          return (
          <>
            {/* Solid backdrop */}
            <motion.div
              className="fixed inset-0 z-[99]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15 }}
              style={{ background: bg }}
            />

            {/* Ambient particle field behind gates */}
            <div className="fixed inset-0 z-[100] pointer-events-none overflow-hidden">
              {[...Array(40)].map((_, i) => (
                <motion.div
                  key={`p-${i}`}
                  className="absolute rounded-full"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{
                    opacity: [0, 0.9, 0],
                    scale: [0, 1.2, 0.3],
                    x: [0, (Math.random() - 0.5) * 500],
                    y: [0, (Math.random() - 0.5) * 500],
                  }}
                  transition={{ duration: 0.7 + Math.random() * 0.5, delay: 0.1 + Math.random() * 0.35, ease: 'easeOut' }}
                  style={{
                    width: `${1.5 + Math.random() * 3}px`,
                    height: `${1.5 + Math.random() * 3}px`,
                    left: '50%',
                    top: '50%',
                    background: i % 4 === 0 ? (isDark ? '#06b6d4' : '#6366f1') : i % 4 === 1 ? '#6366f1' : i % 4 === 2 ? '#8b5cf6' : (isDark ? '#22d3ee' : '#a78bfa'),
                    boxShadow: `0 0 ${4 + Math.random() * 10}px ${i % 3 === 0 ? (isDark ? 'rgba(6,182,212,0.7)' : 'rgba(99,102,241,0.6)') : 'rgba(99,102,241,0.5)'}`,
                  }}
                />
              ))}
            </div>

            {/* Left gate panel — heavy blast door */}
            <motion.div
              className="fixed top-0 left-0 z-[101] h-full w-1/2"
              initial={{ x: 0 }}
              animate={{ x: '-102%' }}
              transition={{ duration: 0.9, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
              style={{
                background: panelBgL,
                borderRight: `2px solid ${panelBorder}`,
                boxShadow: panelShadowL,
              }}
            >
              <PanelInner side="left" />
            </motion.div>

            {/* Right gate panel — heavy blast door */}
            <motion.div
              className="fixed top-0 right-0 z-[101] h-full w-1/2"
              initial={{ x: 0 }}
              animate={{ x: '102%' }}
              transition={{ duration: 0.9, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
              style={{
                background: panelBgR,
                borderLeft: `2px solid ${panelBorder}`,
                boxShadow: panelShadowR,
              }}
            >
              <PanelInner side="right" />
            </motion.div>

            {/* Flash burst at the moment gates start separating */}
            <motion.div
              className="fixed inset-0 z-[102] pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0.7, 0] }}
              transition={{ duration: 0.35, delay: 0.28, ease: 'easeOut' }}
              style={{ background: isDark
                ? 'radial-gradient(circle at 50% 50%, rgba(99,102,241,0.4) 0%, rgba(6,182,212,0.15) 30%, transparent 65%)'
                : 'radial-gradient(circle at 50% 50%, rgba(99,102,241,0.25) 0%, rgba(79,70,229,0.1) 30%, transparent 65%)' }}
            />

            {/* Center seam glow — bright line where gates meet */}
            <motion.div
              className="fixed top-0 left-1/2 z-[102] -translate-x-1/2 pointer-events-none"
              initial={{ opacity: 1, scaleY: 1 }}
              animate={{ opacity: [1, 1, 0], scaleY: [1, 1, 0.8] }}
              transition={{ duration: 1.0, delay: 0.2, times: [0, 0.5, 1], ease: 'easeInOut' }}
              style={{
                width: '4px',
                height: '100%',
                background: centerSeamBg,
                filter: 'blur(1.5px)',
                boxShadow: centerSeamShadow,
              }}
            />
            {/* Wide glow aura around seam */}
            <motion.div
              className="fixed top-0 left-1/2 z-[100] -translate-x-1/2 pointer-events-none"
              initial={{ opacity: 0.6 }}
              animate={{ opacity: [0.6, 0.3, 0] }}
              transition={{ duration: 1.0, delay: 0.2, ease: 'easeInOut' }}
              style={{
                width: '120px',
                height: '100%',
                background: auraBg,
                filter: 'blur(30px)',
              }}
            />

            {/* Energy ring burst from center */}
            <motion.div
              className="fixed top-1/2 left-1/2 z-[102] -translate-x-1/2 -translate-y-1/2 pointer-events-none rounded-full"
              initial={{ width: 0, height: 0, opacity: 0.9 }}
              animate={{ width: '150vh', height: '150vh', opacity: 0 }}
              transition={{ duration: 0.8, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
              style={{
                border: `2px solid ${ringBorder}`,
                boxShadow: ringShadow,
              }}
            />
            {/* Second ring, delayed */}
            <motion.div
              className="fixed top-1/2 left-1/2 z-[102] -translate-x-1/2 -translate-y-1/2 pointer-events-none rounded-full"
              initial={{ width: 0, height: 0, opacity: 0.6 }}
              animate={{ width: '120vh', height: '120vh', opacity: 0 }}
              transition={{ duration: 0.7, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}
              style={{
                border: `1px solid ${isDark ? 'rgba(99,102,241,0.4)' : 'rgba(79,70,229,0.25)'}`,
                boxShadow: `0 0 20px ${isDark ? 'rgba(99,102,241,0.15)' : 'rgba(79,70,229,0.1)'}`,
              }}
            />
            {/* Third ring — widest, faintest */}
            <motion.div
              className="fixed top-1/2 left-1/2 z-[102] -translate-x-1/2 -translate-y-1/2 pointer-events-none rounded-full"
              initial={{ width: 0, height: 0, opacity: 0.3 }}
              animate={{ width: '180vh', height: '180vh', opacity: 0 }}
              transition={{ duration: 1.0, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
              style={{
                border: `1px solid ${isDark ? 'rgba(6,182,212,0.2)' : 'rgba(99,102,241,0.12)'}`,
              }}
            />

            {/* Central hexagonal shield icon + ACCESS GRANTED */}
            <motion.div
              className="fixed top-1/2 left-1/2 z-[103] -translate-x-1/2 -translate-y-1/2 pointer-events-none flex flex-col items-center"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: [0, 1, 1, 0], scale: [0.5, 1, 1, 1.05] }}
              transition={{ duration: 1.2, delay: 0.05, times: [0, 0.15, 0.75, 1], ease: 'easeOut' }}
            >
              {/* Shield / lock icon */}
              <motion.div
                initial={{ rotate: 0 }}
                animate={{ rotate: [0, 0, 180] }}
                transition={{ duration: 0.8, delay: 0.05, times: [0, 0.3, 1], ease: [0.22, 1, 0.36, 1] }}
                className="mb-5"
              >
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <motion.path
                    d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z"
                    stroke="url(#shield-grad)" strokeWidth="1.5" fill="none"
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 0.5, delay: 0.05, ease: 'easeInOut' }}
                  />
                  <motion.path
                    d="M9 12l2 2 4-4"
                    stroke={isDark ? '#06b6d4' : '#6366f1'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 0.25, delay: 0.35 }}
                  />
                  <defs>
                    <linearGradient id="shield-grad" x1="3" y1="2" x2="21" y2="24">
                      <stop offset="0%" stopColor="#6366f1"/>
                      <stop offset="100%" stopColor={isDark ? '#06b6d4' : '#8b5cf6'}/>
                    </linearGradient>
                  </defs>
                </svg>
              </motion.div>
              {/* Title text */}
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.15 }}
                className="text-center"
              >
                <div className="text-sm font-bold tracking-[0.4em] uppercase"
                  style={{
                    background: isDark
                      ? 'linear-gradient(135deg, #6366f1, #06b6d4)'
                      : 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    filter: isDark
                      ? 'drop-shadow(0 0 12px rgba(99,102,241,0.5))'
                      : 'drop-shadow(0 0 12px rgba(79,70,229,0.3))',
                  }}>
                  Access Granted
                </div>
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.35, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
                  className="mx-auto mt-2 h-[1px] w-40"
                  style={{ background: isDark
                    ? 'linear-gradient(to right, transparent, rgba(6,182,212,0.6), transparent)'
                    : 'linear-gradient(to right, transparent, rgba(99,102,241,0.4), transparent)' }}
                />
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.25, delay: 0.35 }}
                  className="mt-2.5 text-[10px] tracking-[0.25em] uppercase font-medium"
                  style={{ color: subtitleColor }}
                >
                  Initializing Platform
                </motion.div>
                {/* Loading dots */}
                <div className="flex justify-center gap-1.5 mt-3">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={`dot-${i}`}
                      className="w-1 h-1 rounded-full"
                      initial={{ opacity: 0.2 }}
                      animate={{ opacity: [0.2, 1, 0.2] }}
                      transition={{ duration: 0.5, delay: 0.4 + i * 0.1, repeat: 1, ease: 'easeInOut' }}
                      style={{ background: dotBg, boxShadow: dotShadow }}
                    />
                  ))}
                </div>
              </motion.div>
            </motion.div>
          </>
          );
        })()}
      </AnimatePresence>
    </>
  );
}

/* ── Inline SVG icons ──────────────────────────────────── */

function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84Z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" fill="#EA4335" />
    </svg>
  );
}

function GitHubIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.93 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.8c.85.004 1.71.115 2.51.34 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.16.59.67.5A10.02 10.02 0 0 0 22 12c0-5.523-4.477-10-10-10Z" />
    </svg>
  );
}

function MicrosoftIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}
