import { useState } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useAuthUI } from "@/context/AuthUIContext";

const PLANS = [
  {
    id: "free",
    name: "FitCheck Free",
    price: "$0",
    period: "forever",
    description: "Everything you need to build the logging habit.",
    features: ["Unlimited workout logging", "Progress & volume tracking", "Training programs", "Streaks & weekly trends"],
    cta: "Start free",
  },
  {
    id: "buddy_pro_monthly",
    name: "AI Buddy Pro",
    price: "$9.99",
    period: "/ month",
    description: "Your personal coach, available every day.",
    features: ["Everything in Free", "AI Coach conversations", "Personalized training guidance", "Profile-aware coaching", "Priority AI access"],
    cta: "Unlock AI Buddy",
    featured: true,
  },
];

export default function PricingSection() {
  const { user } = useAuth();
  const { openAuth } = useAuthUI();
  const [loading, setLoading] = useState(false);

  const startCheckout = async () => {
    if (!user || typeof user !== "object") {
      openAuth("signup");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/billing/checkout", { plan_id: "buddy_pro_monthly" });
      if (!data.url) throw new Error("Checkout session did not return a URL.");
      window.location.assign(data.url);
    } catch (e) {
      const detail = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="pricing" className="relative py-24 md:py-32 px-6 md:px-10 border-t border-zinc-900" data-testid="pricing-section">
      <div className="max-w-7xl mx-auto">
        <div className="max-w-2xl mb-12">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">Simple pricing</div>
          <h2 className="font-heading text-4xl md:text-6xl font-semibold tracking-tight text-white">Log for free. Coach with AI.</h2>
          <p className="text-zinc-500 mt-4 text-base md:text-lg">FitCheck stays useful without a subscription. AI Buddy is the premium layer for people who want personalized coaching on top of their training log.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-5 max-w-4xl">
          {PLANS.map((plan) => (
            <div key={plan.id} className={`relative rounded-2xl border p-6 md:p-7 bg-[#090909] ${plan.featured ? "border-[#39FF14]/50 shadow-[0_0_60px_rgba(57,255,20,0.08)]" : "border-zinc-800"}`}>
              {plan.featured && (
                <div className="absolute top-5 right-5 inline-flex items-center gap-1 rounded-full border border-[#39FF14]/30 bg-[#39FF14]/10 px-2.5 py-1 text-[10px] uppercase tracking-wider text-[#39FF14]"><Sparkles size={11} /> Popular</div>
              )}
              <h3 className="font-heading text-xl font-semibold text-white">{plan.name}</h3>
              <div className="mt-5 flex items-end gap-2"><span className="font-heading text-4xl font-semibold text-white">{plan.price}</span><span className="text-zinc-500 text-sm pb-1">{plan.period}</span></div>
              <p className="text-sm text-zinc-500 mt-3 min-h-10">{plan.description}</p>
              <div className="my-6 space-y-3">
                {plan.features.map((feature) => <div key={feature} className="flex items-center gap-2 text-sm text-zinc-300"><Check size={15} className="text-[#39FF14]" />{feature}</div>)}
              </div>
              <button
                type="button"
                onClick={plan.featured ? startCheckout : () => (user && typeof user === "object" ? window.location.assign("/app") : openAuth("signup"))}
                disabled={loading && plan.featured}
                className={`w-full rounded-full px-5 py-3 text-sm font-semibold inline-flex items-center justify-center gap-2 transition-all ${plan.featured ? "bg-[#39FF14] text-black hover:bg-[#32E612]" : "border border-zinc-700 text-white hover:border-zinc-500"}`}
                data-testid={`pricing-cta-${plan.id}`}
              >
                {loading && plan.featured && <Loader2 size={15} className="animate-spin" />}
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
