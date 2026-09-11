import { useEffect } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function BillingReturnHandler() {
  const { refresh } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("billing");
    if (!result) return;

    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, "", cleanUrl);

    if (result === "cancelled") {
      toast.message("Checkout cancelled. Your FitCheck account is unchanged.");
      return;
    }

    if (result !== "success") return;

    let cancelled = false;
    const verify = async () => {
      for (let attempt = 0; attempt < 8 && !cancelled; attempt += 1) {
        try {
          const { data } = await api.get("/billing/status");
          if (data?.paid) {
            await refresh?.();
            if (!cancelled) toast.success("AI Buddy Pro is now active.");
            return;
          }
        } catch {
          // The webhook can arrive a moment after Stripe redirects the customer.
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      if (!cancelled) toast.message("Payment received. Your Pro access may take a moment to activate.");
    };

    verify();
    return () => { cancelled = true; };
  }, [refresh]);

  return null;
}
