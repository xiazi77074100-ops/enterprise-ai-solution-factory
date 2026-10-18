import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, setCsrfToken, type Schemas } from "../api/client";

type SessionInfo = Schemas["SessionInfo"];

type Auth = {
  session: SessionInfo | null;
  loading: boolean;
  login: (loginId: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const apply = useCallback((info: SessionInfo | null) => {
    setCsrfToken(info?.csrf_token ?? null);
    setSession(info);
  }, []);

  useEffect(() => {
    api<SessionInfo>("GET", "/api/v1/session")
      .then(apply)
      .catch(() => apply(null))
      .finally(() => setLoading(false));
  }, [apply]);

  const login = useCallback(
    async (loginId: string, password: string) => {
      apply(await api<SessionInfo>("POST", "/api/v1/session", { body: { login_id: loginId, password } }));
    },
    [apply],
  );

  const logout = useCallback(async () => {
    try {
      await api<undefined>("DELETE", "/api/v1/session");
    } finally {
      apply(null);
    }
  }, [apply]);

  const value = useMemo(() => ({ session, loading, login, logout }), [session, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider is missing");
  return ctx;
}
