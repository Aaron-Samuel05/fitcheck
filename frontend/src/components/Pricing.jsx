import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Sparkles, Bot, Loader2 } from "lucide-react";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const FREE_FEATURES = [
  "Unlimited workout logging",
  "Progress charts & trends",
  "Starter training plans",
  "Web + mobile access",
];

const PREMIUM_FEATURES = [
  "Everything in Free",
  "AI Buddy — your private fitness coach",
  "Adaptive, goal-aware training plans",
  "Form cues, recovery & nutrition guidance",
  "Priority new features",
];

export default function Pricing({ onRequestAuth }) {
  const { user, refresh } = useAuth();
  const [loading, setLoading] = useState(false);
  const isAuthed = user && typeof user === "object";
  const isPremium = isAuthed && user.is_premium;

  const handleUpgrade = async () => {
    if (!isAuthed) {
      onRequestAuth?.("signup");
      return;
    }
    if (isPremium) {
      toast.success("You're already Premium.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/payments/checkout", {
        plan_id: "premium_monthly",
        origin_url: window.location.origin,
      });
      if (data?.url) {
        window.location.href = data.url;
      } else {
        toast.error("Could not start checkout. Please try again.");
      }
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
      refresh?.();
    }
  };

  return (
    <section
      id="pricing"
      className="relative py-24 md:py-32 border-t border-zinc-900"
      data-testid="pricing-section"
    >
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="max-w-2xl mb-14 md:mb-20">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">
            Pricing
          </div>
          <h2 className="font-heading text-4xl md:text-5xl font-semibold tracking-tight text-white leading-tight">
            Simple pricing.
            <br />
            <span className="text-zinc-500">Serious results.</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
          {/* Free */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="bg-[#0A0A0A] border border-zinc-800 rounded-2xl p-8 md:p-10"
            data-testid="plan-free"
          >
            <div className="text-xs uppercase tracking-[0.2em] text-zinc-500 mb-3">Free</div>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="font-heading text-5xl md:text-6xl font-semibold text-white tracking-tight">$0</span>
              <span className="text-zinc-500 text-sm">/ forever</span>
            </div>
            <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
              Everything you need to log, track, and stay consistent.
            </p>
            <ul className="space-y-3 mb-10">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-3 text-sm text-zinc-300">
                  <Check size={16} className="text-[#39FF14] mt-0.5 shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <button
              onClick={() => (isAuthed ? null : onRequestAuth?.("signup"))}
              disabled={isAuthed}
              className="w-full bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-white font-medium py-3 rounded-xl transition-colors disabled:opacity-60"
              data-testid="plan-free-cta"
            >
              {isAuthed ? "You're on the Free plan" : "Start Free"}
            </button>
          </motion.div>

          {/* Premium */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="relative bg-gradient-to-b from-[#0A0A0A] to-[#070707] border border-[#39FF14]/40 rounded-2xl p-8 md:p-10 overflow-hidden neon-glow"
            data-testid="plan-premium"
          >
            <div
              className="absolute -top-24 -right-24 w-64 h-64 rounded-full blur-3xl pointer-events-none opacity-30"
              style={{ background: "radial-gradient(closest-side, rgba(57,255,20,0.6), transparent 70%)" }}
              aria-hidden="true"
            />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs uppercase tracking-[0.2em] text-[#39FF14] font-medium">Premium</span>
                <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-widest bg-[#39FF14]/15 text-[#39FF14] border border-[#39FF14]/40 rounded-full px-2 py-0.5">
                  <Sparkles size={10} /> AI Buddy
                </span>
              </div>
              <div className="flex items-baseline gap-2 mb-6">
                <span className="font-heading text-5xl md:text-6xl font-semibold text-white tracking-tight neon-text">$9.99</span>
                <span className="text-zinc-500 text-sm">/ month</span>
              </div>
              <p className="text-sm text-zinc-400 mb-8 leading-relaxed">
                Unlock an AI coach that knows your goals, your lifts, and your recovery.
              </p>
              <ul className="space-y-3 mb-10">
                {PREMIUM_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-3 text-sm text-zinc-200">
                    <Check size={16} className="text-[#39FF14] mt-0.5 shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full bg-[#39FF14] text-black font-semibold py-3 rounded-xl hover:bg-[#32E612] transition-all duration-300 shadow-[0_0_20px_rgba(57,255,20,0.25)] hover:shadow-[0_0_40px_rgba(57,255,20,0.5)] disabled:opacity-60 inline-flex items-center justify-center gap-2"
                data-testid="plan-premium-cta"
              >
                {loading && <Loader2 size={16} className="animate-spin" />}
                {isPremium ? (
                  <>
                    <Bot size={16} /> You're Premium
                  </>
                ) : (
                  <>
                    <Sparkles size={16} /> Upgrade to Premium
                  </>
                )}
              </button>
              <p className="text-[11px] text-zinc-600 text-center mt-4">
                Secure checkout by Stripe · Cancel anytime
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
