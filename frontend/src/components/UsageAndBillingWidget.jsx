import { useEffect, useState } from "react";
import { Loader2, CreditCard, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";

export default function UsageAndBillingWidget() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get("/billing/status");
      setStatus(data);
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => { load(); }, []);

  const checkout = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/billing/checkout", { plan_id: "buddy_pro_monthly" });
      if (!data?.url) throw new Error("Checkout could not be started.");
      window.location.assign(data.url);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  const portal = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/billing/portal");
      if (!data?.url) throw new Error("Billing portal could not be opened.");
      window.location.assign(data.url);
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!status) return null;

  const paid = status.paid;
  return (
    <div className="mb-8 rounded-2xl border border-zinc-800 bg-[#090909] p-4 md:p-5" data-testid="billing-status-card">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="w-10 h-10 rounded-xl bg-black border border-[#39FF14]/30 flex items-center justify-center text-[#39FF14]"><Sparkles size={17} /></span>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">AI Buddy</div>
            <div className="text-sm font-semibold text-white">{paid ? "Pro is active" : "Free plan"}</div>
            <div className="text-xs text-zinc-500 mt-1">{paid ? "Unlimited AI coaching is enabled." : "You have a limited daily AI preview. Upgrade for unlimited coaching."}</div>
          </div>
        </div>
        {paid ? (
          <button type="button" onClick={portal} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-full border border-zinc-700 px-4 py-2.5 text-xs font-semibold text-white hover:border-zinc-500 disabled:opacity-50"><CreditCard size={14} /> Manage subscription</button>
        ) : (
          <button type="button" onClick={checkout} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-full bg-[#39FF14] px-4 py-2.5 text-xs font-semibold text-black hover:bg-[#32E612] disabled:opacity-50">{loading && <Loader2 size={14} className="animate-spin" />} Upgrade to Pro</button>
        )}
      </div>
    </div>
  );
}
