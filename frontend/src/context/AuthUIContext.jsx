import { createContext, useCallback, useContext, useState } from "react";
import AuthModal from "@/components/AuthModal";

const AuthUIContext = createContext(null);

export function AuthUIProvider({ children }) {
  const [mode, setMode] = useState(null); // 'signup' | 'login' | null

  const openAuth = useCallback((m = "signup") => setMode(m), []);
  const closeAuth = useCallback(() => setMode(null), []);

  return (
    <AuthUIContext.Provider value={{ openAuth, closeAuth }}>
      {children}
      <AuthModal
        open={mode !== null}
        mode={mode || "signup"}
        onClose={closeAuth}
        onSwitchMode={(m) => setMode(m)}
      />
    </AuthUIContext.Provider>
  );
}

export function useAuthUI() {
  const ctx = useContext(AuthUIContext);
  if (!ctx) throw new Error("useAuthUI must be used within AuthUIProvider");
  return ctx;
}
