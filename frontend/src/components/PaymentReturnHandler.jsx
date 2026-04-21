import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const MAX_ATTEMPTS = 6;
const POLL_MS = 2500;

export default function PaymentReturnHandler() {
  const { user, refresh } = useAuth();
  const handledRef = useRef(false);

  const poll = useCallback(
    async (sessionId, attempt = 0) => {
      if (attempt >= MAX_ATTEMPTS) {
        toast.error("Still processing. Refresh this page in a moment.");
        return;
      }
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (data?.payment_status === "paid") {
          toast.success("Welcome to FitCheck Premium.");
          await refresh?.();
          return;
        }
        if (data?.status === "expired") {
          toast.error("Checkout session expired.");
          return;
        }
      } catch (e) {
        toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
        return;
      }
      setTimeout(() => poll(sessionId, attempt + 1), POLL_MS);
    },
    [refresh]
  );

  useEffect(() => {
    if (handledRef.current) return;
    // Wait for auth check to finish (user is null while checking)
    if (user === null) return;

    const url = new URL(window.location.href);
    const payment = url.searchParams.get("payment");
    const sessionId = url.searchParams.get("session_id");

    if (payment === "cancelled") {
      handledRef.current = true;
      toast.message("Checkout cancelled. No charge made.");
      url.searchParams.delete("payment");
      window.history.replaceState({}, "", url.pathname + (url.search || ""));
      return;
    }

    if (payment === "success" && sessionId) {
      handledRef.current = true;
      url.searchParams.delete("payment");
      url.searchParams.delete("session_id");
      window.history.replaceState({}, "", url.pathname + (url.search || ""));

      if (user === false) {
        toast.message("Please log in to finalize your Premium upgrade.");
        return;
      }
      toast.message("Finalizing your Premium access…");
      poll(sessionId);
    }
  }, [user, poll]);

  return null;
}
