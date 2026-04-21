import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Activity, LogIn, UserPlus } from "lucide-react";
import AuthModal from "@/components/AuthModal";

export default function Navbar() {
  const { user, logout } = useAuth();
  const [authMode, setAuthMode] = useState(null); // 'signup' | 'login' | null

  return (
    <>
      <header
        className="fixed top-0 left-0 right-0 z-40 backdrop-blur-xl bg-black/60 border-b border-zinc-900"
        data-testid="site-header"
      >
        <nav className="flex justify-between items-center h-16 px-6 md:px-10 max-w-7xl mx-auto">
          <a
            href="#top"
            className="flex items-center gap-2 text-white font-heading font-semibold tracking-tight text-lg"
            data-testid="brand-logo"
          >
            <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-[#39FF14]/10 border border-[#39FF14]/40 text-[#39FF14]">
              <Activity size={16} strokeWidth={2.5} />
            </span>
            FitCheck
          </a>

          <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors" data-testid="nav-features">
              Features
            </a>
            <a href="#how" className="hover:text-white transition-colors" data-testid="nav-how">
              How it works
            </a>
            <a href="#pricing" className="hover:text-white transition-colors" data-testid="nav-pricing">
              Pricing
            </a>
          </div>

          <div className="flex items-center gap-2">
            {user && typeof user === "object" ? (
              <>
                <span
                  className="hidden sm:inline text-xs text-zinc-400 max-w-[180px] truncate"
                  data-testid="user-email"
                >
                  {user.email}
                </span>
                <button
                  onClick={logout}
                  className="text-sm text-white px-4 py-2 rounded-full hover:bg-zinc-900 transition-colors border border-transparent hover:border-zinc-800"
                  data-testid="logout-btn"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setAuthMode("login")}
                  className="text-sm text-white px-4 py-2 rounded-full hover:bg-zinc-900 transition-colors border border-transparent hover:border-zinc-800 inline-flex items-center gap-2"
                  data-testid="open-login-btn"
                >
                  <LogIn size={14} /> Log in
                </button>
                <button
                  onClick={() => setAuthMode("signup")}
                  className="text-sm font-semibold bg-[#39FF14] text-black px-4 py-2 rounded-full hover:bg-[#32E612] transition-all duration-300 shadow-[0_0_20px_rgba(57,255,20,0.15)] hover:shadow-[0_0_30px_rgba(57,255,20,0.35)] hover:-translate-y-0.5 inline-flex items-center gap-2"
                  data-testid="open-signup-btn"
                >
                  <UserPlus size={14} /> Sign up
                </button>
              </>
            )}
          </div>
        </nav>
      </header>

      <AuthModal
        open={authMode !== null}
        mode={authMode || "signup"}
        onClose={() => setAuthMode(null)}
        onSwitchMode={(m) => setAuthMode(m)}
      />
    </>
  );
}
