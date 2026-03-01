import { useCallback, useEffect, useState } from "react";
import {
  login as apiLogin,
  register as apiRegister,
  fetchMe,
  type AuthUser,
} from "../lib/auth";
import { getString, setItem, removeItem } from "../lib/storage";

export type AuthMode = "jwt" | "api_key" | "loading";

interface AuthState {
  mode: AuthMode;
  user: AuthUser | null;
  token: string;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    mode: "loading",
    user: null,
    token: getString("auth_token", ""),
  });

  // On mount: probe /api/auth/me to determine if user auth is active
  useEffect(() => {
    const savedToken = getString("auth_token", "");

    if (!savedToken) {
      // No saved JWT — try to see if the server even has user auth
      fetch("/api/auth/me", { headers: {} })
        .then((resp) => {
          if (resp.status === 404) {
            // Server has no /api/auth route → API-key mode
            setState({ mode: "api_key", user: null, token: getString("api_key", "changeme") });
          } else {
            // Server has user auth but no token → need login
            setState({ mode: "jwt", user: null, token: "" });
          }
        })
        .catch(() => {
          // Network error or server down — assume API-key mode
          setState({ mode: "api_key", user: null, token: getString("api_key", "changeme") });
        });
      return;
    }

    // We have a saved token — validate it
    fetchMe(savedToken)
      .then((user) => {
        setState({ mode: "jwt", user, token: savedToken });
      })
      .catch(() => {
        // Token invalid — check if server even supports user auth
        fetch("/api/auth/me", { headers: {} })
          .then((resp) => {
            if (resp.status === 404) {
              setState({ mode: "api_key", user: null, token: getString("api_key", "changeme") });
            } else {
              removeItem("auth_token");
              setState({ mode: "jwt", user: null, token: "" });
            }
          })
          .catch(() => {
            setState({ mode: "api_key", user: null, token: getString("api_key", "changeme") });
          });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiLogin(email, password);
    setItem("auth_token", result.access_token);
    setState({ mode: "jwt", user: result.user, token: result.access_token });
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const result = await apiRegister(email, password);
    setItem("auth_token", result.access_token);
    setState({ mode: "jwt", user: result.user, token: result.access_token });
  }, []);

  const logout = useCallback(() => {
    removeItem("auth_token");
    setState({ mode: "jwt", user: null, token: "" });
  }, []);

  const isAuthenticated = state.mode === "api_key" || (state.mode === "jwt" && state.user !== null);

  return {
    mode: state.mode,
    user: state.user,
    token: state.token,
    isAuthenticated,
    login,
    register,
    logout,
  } as const;
}
