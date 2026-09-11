import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatApiErrorDetail } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = loading, false = logged out, object = logged in
  const [user, setUser] = useState(null);

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch {
      setUser(false);
      return false;
    }
  }, []);

  useEffect(() => {
    const hasSessionId = new URLSearchParams(window.location.hash.replace(/^#/, "")).has("session_id");
    const token = localStorage.getItem("token");

    if (hasSessionId) return;

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
      if (!data.access_token) throw new Error("Account created but no session was returned.");
      localStorage.setItem("token", data.access_token);
      await fetchMe();
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const login = async (email, password) => {
    try {
      const { data } = await api.post("/auth/login", { email: email.trim(), password });
      if (!data.access_token) throw new Error("Login succeeded but no access token was returned.");
      localStorage.setItem("token", data.access_token);
      await fetchMe();
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

  return (
    <AuthContext.Provider value={{ user, register, login, logout, refresh: fetchMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
