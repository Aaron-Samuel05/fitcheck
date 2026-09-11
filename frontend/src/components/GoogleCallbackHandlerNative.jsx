import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function GoogleCallbackHandlerNative() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    const status = new URLSearchParams(location.search).get("google");
    if (!status) return;
    processed.current = true;

    if (status === "error") {
      toast.error("Google sign-in failed. Please try again.");
      navigate("/", { replace: true });
      return;
    }

    (async () => {
      const user = await refresh?.();
      if (!user) {
        toast.error("Google sign-in succeeded, but the FitCheck session could not be loaded.");
        navigate("/", { replace: true });
        return;
      }
      toast.success("Signed in with Google.");
      navigate("/app", { replace: true });
    })();
  }, [location.search, refresh, navigate]);

  return null;
}
