import { useEffect, useState } from "react";
import { X, Loader2, Mail, Lock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
function startGoogleAuth() {
  const redirectUrl = window.location.origin + "/";
  window.location.href =
    "https://auth.emergentagent.com/?redirect=" + encodeURIComponent(redirectUrl);
}

export default function AuthModal({ open, mode, onClose, onSwitchMode }) {
  const { register, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setError("");
      setEmail("");
      setPassword("");
    }
  }, [open, mode]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const isSignup = mode === "signup";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);
    const res = isSignup ? await register(email, password) : await login(email, password);
    setLoading(false);
    if (res.ok) {
      toast.success(isSignup ? "Welcome to FitCheck." : "Welcome back.");
      onClose();
    } else {
      setError(res.error || "Something went wrong. Please try again.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      data-testid="auth-modal"
      onClick={onClose}
    >
      <div
        className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl w-full max-w-md p-8 relative shadow-2xl shadow-black"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors"
          aria-label="Close"
          data-testid="auth-modal-close"
        >
          <X size={18} />
        </button>

        <div className="mb-6">
          <div className="text-xs uppercase tracking-[0.18em] text-[#39FF14] font-medium mb-2">
            {isSignup ? "Start training smarter" : "Welcome back"}
          </div>
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-white">
            {isSignup ? "Create your account" : "Log in to FitCheck"}
          </h2>
          <p className="text-sm text-zinc-500 mt-2">
            {isSignup
              ? "Free forever. No credit card required."
              : "Enter your credentials to continue."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" data-testid="auth-form">
          <button
            type="button"
            onClick={startGoogleAuth}
            className="w-full bg-white text-zinc-900 font-semibold py-3 rounded-xl hover:bg-zinc-100 transition-all duration-300 inline-flex items-center justify-center gap-3"
            data-testid="google-auth-btn"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.8.54-1.83.86-3.05.86-2.35 0-4.33-1.58-5.04-3.71H.96v2.33A9 9 0 0 0 9 18z"/>
              <path fill="#FBBC05" d="M3.96 10.71A5.41 5.41 0 0 1 3.68 9c0-.59.1-1.17.28-1.71V4.96H.96A9 9 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3-2.33z"/>
              <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.46 3.44 1.35l2.58-2.58A9 9 0 0 0 9 0 9 9 0 0 0 .96 4.96l3 2.33C4.67 5.16 6.65 3.58 9 3.58z"/>
            </svg>
            {isSignup ? "Sign up with Google" : "Continue with Google"}
          </button>

          <div className="flex items-center gap-3 py-1">
            <span className="flex-1 h-px bg-zinc-800" />
            <span className="text-[10px] uppercase tracking-[0.22em] text-zinc-600">or</span>
            <span className="flex-1 h-px bg-zinc-800" />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
              Email
            </label>
            <div className="relative">
              <Mail
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@fitcheck.app"
                autoComplete="email"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14] transition-all"
                data-testid="auth-email-input"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-2 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600"
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                autoComplete={isSignup ? "new-password" : "current-password"}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#39FF14] focus:border-[#39FF14] transition-all"
                data-testid="auth-password-input"
                required
                minLength={6}
              />
            </div>
          </div>

          {error && (
            <div
              className="text-sm text-red-400 bg-red-950/40 border border-red-900/60 rounded-lg px-3 py-2"
              data-testid="auth-error"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#39FF14] text-black font-semibold py-3 rounded-xl hover:bg-[#32E612] transition-all duration-300 shadow-[0_0_20px_rgba(57,255,20,0.2)] hover:shadow-[0_0_30px_rgba(57,255,20,0.4)] disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
            data-testid="auth-submit-btn"
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {isSignup ? "Create account" : "Log in"}
          </button>
        </form>

        <div className="text-sm text-zinc-500 text-center mt-6">
          {isSignup ? (
            <>
              Already have an account?{" "}
              <button
                className="text-white hover:text-[#39FF14] transition-colors underline-offset-4 hover:underline"
                onClick={() => onSwitchMode("login")}
                data-testid="switch-to-login"
              >
                Log in
              </button>
            </>
          ) : (
            <>
              New to FitCheck?{" "}
              <button
                className="text-white hover:text-[#39FF14] transition-colors underline-offset-4 hover:underline"
                onClick={() => onSwitchMode("signup")}
                data-testid="switch-to-signup"
              >
                Create an account
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
