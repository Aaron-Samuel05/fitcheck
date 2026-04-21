import { useEffect, useRef } from "react";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function GoogleCallbackHandler() {
  const { refresh } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) return;
    processed.current = true;

    const sessionId = decodeURIComponent(match[1]);
    // Clear the fragment immediately so a reload/refresh doesn't re-exchange.
    const cleanUrl = window.location.pathname + window.location.search;
    window.history.replaceState({}, "", cleanUrl);

    (async () => {
      try {
        await api.post("/auth/google/exchange", { session_id: sessionId });
        await refresh?.();
        toast.success("Signed in with Google.");
      } catch (e) {
        toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message);
      }
    })();
  }, [refresh]);

  return null;
}
