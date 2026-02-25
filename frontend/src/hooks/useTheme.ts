import { useCallback, useEffect, useState } from "react";
import type { ThemeMode } from "../types";
import { getString, setItem } from "../lib/storage";

function resolveTheme(mode: ThemeMode): "dark" | "light" {
  if (mode === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return mode;
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeMode>(
    () => getString("theme", "light") as ThemeMode,
  );

  const apply = useCallback((mode: ThemeMode) => {
    const resolved = resolveTheme(mode);
    document.documentElement.className = resolved;
    setItem("theme", mode);
  }, []);

  const setTheme = useCallback(
    (mode: ThemeMode) => {
      setThemeState(mode);
      apply(mode);
    },
    [apply],
  );

  const cycleTheme = useCallback(() => {
    const order: ThemeMode[] = ["dark", "light", "system"];
    setTheme(order[(order.indexOf(theme) + 1) % order.length]);
  }, [theme, setTheme]);

  // Apply on mount + listen for system changes
  useEffect(() => {
    apply(theme);
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (theme === "system") apply("system");
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [theme, apply]);

  const resolvedTheme = resolveTheme(theme);

  return { theme, resolvedTheme, setTheme, cycleTheme } as const;
}
