import { motion } from "framer-motion";
import { ArrowRight, Sparkles, LayoutDashboard } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useAuthUI } from "@/context/AuthUIContext";

export default function Hero() {
  const { user } = useAuth();
  const { openAuth } = useAuthUI();
  const isAuthed = user && typeof user === "object";

  return (
    <section
      id="top"
      className="relative overflow-hidden pt-36 pb-28 md:pt-44 md:pb-36"
      data-testid="hero-section"
    >
      <div className="absolute inset-0 hero-grid pointer-events-none" aria-hidden="true" />

      <motion.div
        initial={{ opacity: 0.2, scale: 0.9 }}
        animate={{ opacity: [0.25, 0.45, 0.25], scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 w-[620px] h-[620px] rounded-full blur-3xl pointer-events-none"
        style={{ background: "radial-gradient(closest-side, rgba(57,255,20,0.28), rgba(57,255,20,0) 70%)" }}
        aria-hidden="true"
      />

      <div className="relative max-w-5xl mx-auto px-6 md:px-10 flex flex-col items-center text-center gap-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-[0.22em] text-zinc-400 bg-zinc-900/60 border border-zinc-800 rounded-full px-4 py-2"
          data-testid="hero-eyebrow"
        >
          <Sparkles size={12} className="text-[#39FF14]" />
          AI Buddy included · 100% free
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="font-heading font-semibold tracking-[-0.035em] text-white text-5xl md:text-7xl lg:text-8xl leading-[0.95]"
          data-testid="hero-headline"
        >
          Train with intention.
          <br />
          <span className="text-zinc-500">Progress with </span>
          <motion.span
            className="text-[#39FF14] neon-text inline-block"
            animate={{
              textShadow: [
                "0 0 20px rgba(57,255,20,0.35)",
                "0 0 40px rgba(57,255,20,0.6)",
                "0 0 20px rgba(57,255,20,0.35)",
              ],
            }}
            transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
          >
            proof
          </motion.span>
          <span className="text-zinc-500">.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="max-w-2xl text-base md:text-lg text-zinc-400 leading-relaxed"
          data-testid="hero-subheadline"
        >
          FitCheck turns every rep, run, and rest day into signal. Log workouts,
          track progress, and follow plans built around how you actually move.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="flex flex-col sm:flex-row items-center gap-3 mt-2"
        >
          {isAuthed ? (
            <Link
              to="/app"
              className="group bg-[#39FF14] text-black font-semibold px-7 py-4 rounded-full hover:bg-[#32E612] transition-all duration-300 shadow-[0_0_24px_rgba(57,255,20,0.25)] hover:shadow-[0_0_48px_rgba(57,255,20,0.5)] hover:-translate-y-0.5 inline-flex items-center gap-2"
              data-testid="hero-cta-open-dashboard"
            >
              <LayoutDashboard size={16} /> Open your dashboard
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          ) : (
            <button
              onClick={() => openAuth("signup")}
              className="group bg-[#39FF14] text-black font-semibold px-7 py-4 rounded-full hover:bg-[#32E612] transition-all duration-300 shadow-[0_0_24px_rgba(57,255,20,0.25)] hover:shadow-[0_0_48px_rgba(57,255,20,0.5)] hover:-translate-y-0.5 inline-flex items-center gap-2"
              data-testid="hero-cta-get-started"
            >
              Get Started Free
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
            </button>
          )}

          <a
            href="#features"
            className="text-sm text-zinc-300 font-medium px-5 py-3 rounded-full hover:bg-zinc-900 transition-colors border border-transparent hover:border-zinc-800"
            data-testid="hero-cta-learn-more"
          >
            See features →
          </a>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-xs text-zinc-600 tracking-wide"
        >
          Free forever · No credit card · Built for iPhone, iPad, and the web
        </motion.p>
      </div>
    </section>
  );
}
