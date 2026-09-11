import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api, formatApiErrorDetail } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function GoogleCallbackHandler() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const sessionId = params.get("session_id");
    if (!sessionId) return;

    processed.current = true;
    window.history.replaceState({}, "", window.location.pathname + window.location.search);

    (async () => {
      try {
        const { data } = await api.post("/auth/google/exchange", { session_id: sessionId });
        if (!data?.access_token) throw new Error("Google sign-in did not return a session.");
        localStorage.setItem("token", data.access_token);
        const me = await refresh?.();
        if (!me) throw new Error("Google sign-in succeeded but the FitCheck session could not be loaded.");
        toast.success("Signed in with Google.");
        navigate("/app", { replace: true });
      } catch (e) {
        localStorage.removeItem("token");
        toast.error(formatApiErrorDetail(e.response?.data?.detail) || e.message || "Google sign-in failed.");
        navigate("/", { replace: true });
      }
    })();
  }, [refresh, navigate]);

  return null;
}
