import { useCallback, useState } from "react";
import { motion } from "framer-motion";

type Tab = "signin" | "signup";

interface LoginPageProps {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string) => Promise<void>;
}

export default function LoginPage({ onLogin, onRegister }: LoginPageProps) {
  const [tab, setTab] = useState<Tab>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError("");

      if (!email || !password) {
        setError("Email and password are required");
        return;
      }

      if (tab === "signup") {
        if (password !== confirmPassword) {
          setError("Passwords do not match");
          return;
        }
        if (password.length < 8) {
          setError("Password must be at least 8 characters");
          return;
        }
      }

      setLoading(true);
      try {
        if (tab === "signin") {
          await onLogin(email, password);
        } else {
          await onRegister(email, password);
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [tab, email, password, confirmPassword, onLogin, onRegister],
  );

  return (
    <div
      className="flex min-h-screen"
      style={{ background: "var(--bg)" }}
    >
      {/* Left column — branding */}
      <motion.div
        className="hidden flex-col items-center justify-center gap-6 px-12 md:flex md:w-1/2"
        style={{ background: "var(--surface)" }}
        initial={{ opacity: 0, x: -24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <img
          src="/assets/logo.png"
          alt="Barongsai"
          className="h-20 w-20 rounded-2xl object-contain"
        />
        <h1 className="text-3xl font-bold" style={{ color: "var(--text)" }}>
          Barongsai
        </h1>
        <p
          className="max-w-sm text-center text-[15px] leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          AI-powered search engine that finds, analyzes, and synthesizes information from across the web with cited sources.
        </p>
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-blue-500" />
          <div className="h-2 w-2 rounded-full bg-amber-500" />
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
        </div>
      </motion.div>

      {/* Right column — form */}
      <motion.div
        className="flex flex-1 items-center justify-center px-6"
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
      >
      <div
        className="w-full max-w-md rounded-2xl border p-8 shadow-lg"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        {/* Logo — visible only on mobile where left column is hidden */}
        <div className="mb-6 flex flex-col items-center gap-2 md:hidden">
          <img
            src="/assets/logo.png"
            alt="Barongsai"
            className="h-12 w-12 rounded-xl object-contain"
          />
          <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
            Barongsai
          </h1>
        </div>

        {/* Tabs */}
        <div
          className="mb-6 flex rounded-xl border"
          style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
        >
          {(["signin", "signup"] as Tab[]).map((t) => (
            <button
              key={t}
              className="flex-1 rounded-xl py-2.5 text-sm font-medium transition-all"
              style={{
                background: tab === t ? "var(--accent)" : "transparent",
                color: tab === t ? "var(--bg)" : "var(--text-secondary)",
              }}
              onClick={() => {
                setTab(t);
                setError("");
              }}
            >
              {t === "signin" ? "Sign In" : "Sign Up"}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              className="mb-1.5 block text-[13px] font-medium"
              style={{ color: "var(--text-secondary)" }}
            >
              Email
            </label>
            <input
              type="email"
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/25"
              style={{
                background: "var(--surface-2)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              autoFocus
            />
          </div>

          <div>
            <label
              className="mb-1.5 block text-[13px] font-medium"
              style={{ color: "var(--text-secondary)" }}
            >
              Password
            </label>
            <input
              type="password"
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/25"
              style={{
                background: "var(--surface-2)",
                borderColor: "var(--border)",
                color: "var(--text)",
              }}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={tab === "signup" ? "Min. 8 characters" : "Enter password"}
              autoComplete={tab === "signin" ? "current-password" : "new-password"}
            />
          </div>

          {tab === "signup" && (
            <div>
              <label
                className="mb-1.5 block text-[13px] font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                Confirm Password
              </label>
              <input
                type="password"
                className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/25"
                style={{
                  background: "var(--surface-2)",
                  borderColor: "var(--border)",
                  color: "var(--text)",
                }}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat password"
                autoComplete="new-password"
              />
            </div>
          )}

          {error && (
            <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "#ef44441a", color: "#ef4444" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50"
            style={{ background: "var(--accent)", color: "var(--bg)" }}
          >
            {loading && (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {loading
              ? "Signing in..."
              : tab === "signin"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>
      </div>
      </motion.div>
    </div>
  );
}
