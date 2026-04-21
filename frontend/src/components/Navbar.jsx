import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useAuthUI } from "@/context/AuthUIContext";
import { Activity, LogIn, UserPlus, Sparkles } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { openAuth } = useAuthUI();
  const [menuOpen, setMenuOpen] = useState(false);
  const isAuthed = user && typeof user === "object";

  return (
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
          <a href="#features" className="hover:text-white transition-colors" data-testid="nav-features">Features</a>
          <a href="#how" className="hover:text-white transition-colors" data-testid="nav-how">How it works</a>
          <a href="#pricing" className="hover:text-white transition-colors" data-testid="nav-pricing">Pricing</a>
          <a href="#contact" className="hover:text-white transition-colors" data-testid="nav-contact">Contact</a>
        </div>

        <div className="flex items-center gap-2">
          {isAuthed ? (
            <>
              {user.is_premium && (
                <span
                  className="hidden sm:inline-flex items-center gap-1 text-[10px] uppercase tracking-widest font-semibold bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/40 rounded-full px-2.5 py-1"
                  data-testid="premium-badge"
                >
                  <Sparkles size={10} /> Premium
                </span>
              )}
              <button
                className="text-sm text-zinc-300 px-3 py-2 rounded-full hover:bg-zinc-900 transition-colors hidden sm:block max-w-[180px] truncate"
                onClick={() => setMenuOpen((v) => !v)}
                data-testid="user-email"
                aria-haspopup="menu"
              >
                {user.email}
              </button>
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
                onClick={() => openAuth("login")}
                className="text-sm text-white px-4 py-2 rounded-full hover:bg-zinc-900 transition-colors border border-transparent hover:border-zinc-800 inline-flex items-center gap-2"
                data-testid="open-login-btn"
              >
                <LogIn size={14} /> Log in
              </button>
              <button
                onClick={() => openAuth("signup")}
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
  );
}
