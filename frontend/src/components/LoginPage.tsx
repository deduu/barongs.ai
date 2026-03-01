import { useCallback, useState } from "react";

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
      className="flex min-h-screen items-center justify-center"
      style={{ background: "var(--bg)" }}
    >
      <div
        className="w-full max-w-md rounded-2xl border p-8 shadow-lg"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        {/* Logo */}
        <div className="mb-6 flex flex-col items-center gap-2">
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
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--accent)]"
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
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--accent)]"
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
                className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none transition-colors focus:border-[var(--accent)]"
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
            className="mt-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50"
            style={{ background: "var(--accent)", color: "var(--bg)" }}
          >
            {loading
              ? "Please wait..."
              : tab === "signin"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
