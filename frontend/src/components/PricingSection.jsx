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
    description: "A complete workout logger for anyone who wants consistent, measurable training.",
    features: ["Unlimited workout logging", "Progress & volume tracking", "Training programs", "Streaks & weekly trends", "No credit card required"],
    cta: "Start free",
  },
  {
    id: "buddy_pro_monthly",
    name: "AI Buddy Pro",
    price: "$9.99",
    period: "/ month",
    description: "Your personal fitness coach layered on top of your real training history.",
    features: ["Everything in Free", "Unlimited AI coaching", "Personalized training guidance", "Profile-aware coaching", "Priority AI access"],
    cta: "Unlock AI Buddy",
    featured: true,
  },
];

export default function PricingSection() {
  const { user } = useAuth();
  const { openAuth } = useAuthUI();
  const [loading, setLoading] = useState(null);
  const [annual, setAnnual] = useState(false);

  const startCheckout = async () => {
    if (!user || typeof user !== "object") {
      openAuth("signup");
      return;
    }
    const planId = annual ? "buddy_pro_yearly" : "buddy_pro_monthly";
    setLoading(planId);
    try {
      const { data } = await api.post("/billing/checkout", { plan_id: planId });
      if (!data.url) throw new Error("Checkout session did not return a URL.");
      window.location.assign(data.url);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(null);
    }
  };

  const displayPrice = annual ? "$79.99" : "$9.99";
  const displayPeriod = annual ? "/ year" : "/ month";

  return (
    <section id="pricing" className="relative py-24 md:py-32 px-6 md:px-10 border-t border-zinc-900" data-testid="pricing-section">
      <div className="max-w-7xl mx-auto">
        <div className="max-w-2xl mb-12">
          <div className="text-xs uppercase tracking-[0.22em] text-[#39FF14] font-medium mb-3">Simple pricing</div>
          <h2 className="font-heading text-4xl md:text-6xl font-semibold tracking-tight text-white">Log for free. Coach with AI.</h2>
          <p className="text-zinc-500 mt-4 text-base md:text-lg">FitCheck stays useful without a subscription. AI Buddy Pro is the premium layer for people who want personalized coaching on top of their training log.</p>
        </div>

        <div className="flex items-center gap-2 mb-6 rounded-full border border-zinc-800 bg-zinc-950 p-1 w-fit" role="group" aria-label="Billing period">
          <button type="button" onClick={() => setAnnual(false)} className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors ${!annual ? "bg-white text-black" : "text-zinc-500 hover:text-white"}`}>Monthly</button>
          <button type="button" onClick={() => setAnnual(true)} className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors ${annual ? "bg-white text-black" : "text-zinc-500 hover:text-white"}`}>Yearly <span className="ml-1 text-[#39FF14]">save ~33%</span></button>
        </div>

        <div className="grid md:grid-cols-2 gap-5 max-w-4xl">
          {PLANS.map((plan) => (
            <div key={plan.id} className={`relative rounded-2xl border p-6 md:p-7 bg-[#090909] ${plan.featured ? "border-[#39FF14]/50 shadow-[0_0_60px_rgba(57,255,20,0.08)]" : "border-zinc-800"}`}>
              {plan.featured && (
                <div className="absolute top-5 right-5 inline-flex items-center gap-1 rounded-full border border-[#39FF14]/30 bg-[#39FF14]/10 px-2.5 py-1 text-[10px] uppercase tracking-wider text-[#39FF14]"><Sparkles size={11} /> Popular</div>
              )}
              <h3 className="font-heading text-xl font-semibold text-white">{plan.name}</h3>
              <div className="mt-5 flex items-end gap-2"><span className="font-heading text-4xl font-semibold text-white">{plan.featured ? displayPrice : plan.price}</span><span className="text-zinc-500 text-sm pb-1">{plan.featured ? displayPeriod : plan.period}</span></div>
              {plan.featured && annual && <div className="text-xs text-[#39FF14] mt-2">Save $39.89 compared with 12 monthly payments.</div>}
              <p className="text-sm text-zinc-500 mt-3 min-h-10">{plan.description}</p>
              <div className="my-6 space-y-3">
                {plan.features.map((feature) => <div key={feature} className="flex items-center gap-2 text-sm text-zinc-300"><Check size={15} className="text-[#39FF14]" />{feature}</div>)}
              </div>
              <button
                type="button"
                onClick={plan.featured ? startCheckout : () => (user && typeof user === "object" ? window.location.assign("/app") : openAuth("signup"))}
                disabled={Boolean(loading)}
                className={`w-full rounded-full px-5 py-3 text-sm font-semibold inline-flex items-center justify-center gap-2 transition-all ${plan.featured ? "bg-[#39FF14] text-black hover:bg-[#32E612]" : "border border-zinc-700 text-white hover:border-zinc-500"}`}
                data-testid={`pricing-cta-${plan.id}`}
              >
                {loading === (annual ? "buddy_pro_yearly" : "buddy_pro_monthly") && <Loader2 size={15} className="animate-spin" />}
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
