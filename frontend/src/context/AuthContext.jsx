import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatApiErrorDetail } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = loading, false = logged out, object = logged in
  const [user, setUser] = useState(null);

  // ✅ Fetch current user using token
  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setUser(false);
      return;
    }

    fetchMe();
  }, [fetchMe]);

  // ✅ REGISTER
  const register = async (email, password) => {
    try {
      const { data } = await api.post("/auth/register", { email, password });

      // If backend later returns token → handle it
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        await fetchMe();
        window.location.href = "/app";
      }

      return { ok: true };
    } catch (e) {
      return {
        ok: false,
        error: formatApiErrorDetail(e.response?.data?.detail) || e.message
      };
    }
  };

  // ✅ LOGIN (FIXED)
  const login = async (email, password) => {
    try {
      const { data } = await api.post("/auth/login", { email, password });

      // 🔥 CRITICAL FIX
      localStorage.setItem("token", data.access_token);

      // Fetch real user
      await fetchMe();

      // Redirect to dashboard
      window.location.href = "/app";

      return { ok: true };
    } catch (e) {
      return {
        ok: false,
        error: formatApiErrorDetail(e.response?.data?.detail) || e.message
      };
    }
  };

  // ✅ LOGOUT
  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // ignore
    }

    localStorage.removeItem("token");
    setUser(false);
    window.location.href = "/";
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
