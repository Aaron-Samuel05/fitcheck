import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatApiErrorDetail } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch (error) {
      const status = error?.response?.status;
      if (status === 401 || status === 404) {
        setUser(false);
        localStorage.removeItem("token");
      }
      // Keep the app in a loading/configuration state for network and server errors.
      return false;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const hasGoogleSession = new URLSearchParams(window.location.hash.replace(/^#/, "")).has("session_id");
    if (hasGoogleSession) return;
    if (!token || token === "undefined" || token === "null") {
      localStorage.removeItem("token");
      setUser(false);
      return;
    }
    fetchMe();
  }, [fetchMe]);

  const register = async (email, password) => {
    try {
      const { data } = await api.post("/auth/register", { email: email.trim(), password });
      if (!data?.access_token) throw new Error("Account created but no session was returned.");
      localStorage.setItem("token", data.access_token);
      const me = await fetchMe();
      if (!me) throw new Error("Account created, but the session could not be loaded. Check the API connection.");
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const login = async (email, password) => {
    try {
      const { data } = await api.post("/auth/login", { email: email.trim(), password });
      if (!data?.access_token) throw new Error("Login succeeded but no access token was returned.");
      localStorage.setItem("token", data.access_token);
      const me = await fetchMe();
      if (!me) throw new Error("Signed in, but the session could not be loaded. Check the API connection.");
      return { ok: true };
    } catch (e) {
      localStorage.removeItem("token");
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch { /* local logout still succeeds */ }
    localStorage.removeItem("token");
    setUser(false);
    window.location.assign("/");
  };

  return <AuthContext.Provider value={{ user, register, login, logout, refresh: fetchMe }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
