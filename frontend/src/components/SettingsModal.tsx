import { useCallback, useState } from "react";
import type { ThemeMode } from "../types";

interface SettingsModalProps {
  open: boolean;
  apiKey: string;
  theme: ThemeMode;
  onSetTheme: (t: ThemeMode) => void;
  onSaveApiKey: (key: string) => void;
  onClose: () => void;
}

export default function SettingsModal({
  open,
  apiKey,
  theme,
  onSetTheme,
  onSaveApiKey,
  onClose,
}: SettingsModalProps) {
  const [keyInput, setKeyInput] = useState(apiKey);

  const handleSave = useCallback(() => {
    onSaveApiKey(keyInput || "changeme");
    onClose();
  }, [keyInput, onSaveApiKey, onClose]);

  if (!open) return null;

  const themes: { value: ThemeMode; icon: string; label: string }[] = [
    { value: "dark", icon: "\uD83C\uDF19", label: "Dark" },
    { value: "light", icon: "\u2600\uFE0F", label: "Light" },
    { value: "system", icon: "\uD83D\uDDA5\uFE0F", label: "System" },
  ];

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="w-[420px] max-w-[calc(100vw-32px)] rounded-xl border p-7"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-5 text-lg font-bold">Settings</h2>

        {/* API Key */}
        <div className="mb-4">
          <label
            className="mb-1.5 block text-[13px] font-medium"
            style={{ color: "var(--text-secondary)" }}
          >
            API Key
          </label>
          <input
            type="password"
            className="w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none transition-colors focus:border-[var(--accent)]"
            style={{
              background: "var(--surface-2)",
              borderColor: "var(--border)",
              color: "var(--text)",
            }}
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="changeme"
            autoComplete="off"
          />
        </div>

        {/* Theme */}
        <div className="mb-4">
          <label
            className="mb-1.5 block text-[13px] font-medium"
            style={{ color: "var(--text-secondary)" }}
          >
            Theme
          </label>
          <div className="flex gap-2">
            {themes.map((t) => (
              <button
                key={t.value}
                className="flex-1 rounded-lg border py-2 text-center text-[13px] transition-all"
                style={{
                  background:
                    theme === t.value
                      ? "var(--accent-dim)"
                      : "var(--surface-2)",
                  borderColor:
                    theme === t.value ? "var(--accent)" : "var(--border)",
                  color:
                    theme === t.value
                      ? "var(--accent)"
                      : "var(--text-secondary)",
                }}
                onClick={() => onSetTheme(t.value)}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-2">
          <button
            className="rounded-lg border px-5 py-2 text-sm font-medium transition-all hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="rounded-lg border-none px-5 py-2 text-sm font-medium text-white transition-all"
            style={{ background: "var(--accent)" }}
            onClick={handleSave}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
