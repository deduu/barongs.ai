import { useCallback, useRef, useState } from "react";
import type { ChatMode, ThemeMode } from "../types";
import type { AuthMode } from "../hooks/useAuth";
import type { SearchSettings, PresetName } from "../lib/searchSettings";
import { useFocusTrap } from "../hooks/useFocusTrap";
import { XIcon, MoonIcon, SunIcon, MonitorIcon, CheckIcon } from "./icons";
import SearchSettingsPanel from "./SearchSettingsPanel";

interface SettingsModalProps {
  open: boolean;
  apiKey: string;
  theme: ThemeMode;
  authMode: AuthMode;
  userEmail: string | null;
  chatMode: ChatMode;
  searchSettings: SearchSettings;
  onUpdateSettings: <M extends ChatMode>(mode: M, partial: Partial<SearchSettings[M]>) => void;
  onApplyPreset: (mode: ChatMode, preset: PresetName) => void;
  onResetSettings: (mode: ChatMode) => void;
  getActivePreset: (mode: ChatMode) => PresetName | null;
  onSetTheme: (t: ThemeMode) => void;
  onSaveApiKey: (key: string) => void;
  onLogout: () => void;
  onClose: () => void;
}

type Tab = "general" | "search" | "appearance" | "about";

export default function SettingsModal({
  open,
  apiKey,
  theme,
  authMode,
  userEmail,
  chatMode,
  searchSettings,
  onUpdateSettings,
  onApplyPreset,
  onResetSettings,
  getActivePreset,
  onSetTheme,
  onSaveApiKey,
  onLogout,
  onClose,
}: SettingsModalProps) {
  const [keyInput, setKeyInput] = useState(apiKey);
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const [keyValid, setKeyValid] = useState<boolean | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const trapRef = useFocusTrap(open);

  const handleSave = useCallback(() => {
    setIsSaving(true);
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      onSaveApiKey(keyInput || "changeme");
      setIsSaving(false);
      onClose();
    }, 400);
  }, [keyInput, onSaveApiKey, onClose]);

  const handleKeyBlur = useCallback(() => {
    setKeyValid(keyInput.length >= 4);
  }, [keyInput]);

  if (!open) return null;

  const tabs: { id: Tab; label: string }[] = [
    { id: "general", label: "General" },
    { id: "search", label: "Search" },
    { id: "appearance", label: "Appearance" },
    { id: "about", label: "About" },
  ];

  const themes: { value: ThemeMode; icon: typeof MoonIcon; label: string }[] = [
    { value: "dark", icon: MoonIcon, label: "Dark" },
    { value: "light", icon: SunIcon, label: "Light" },
    { value: "system", icon: MonitorIcon, label: "System" },
  ];

  const isJwtAuth = authMode === "jwt";

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
    >
      <div
        ref={trapRef}
        className="w-[480px] max-w-[calc(100vw-32px)] max-h-[calc(100vh-64px)] flex flex-col rounded-2xl border p-0 shadow-lg animate-scale-in"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-lg font-bold">Settings</h2>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-secondary)" }}
            onClick={onClose}
            aria-label="Close settings"
          >
            <XIcon size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6" style={{ borderColor: "var(--border)" }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`relative px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id ? "" : ""
              }`}
              style={{
                color: activeTab === tab.id ? "var(--accent)" : "var(--text-secondary)",
              }}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              aria-selected={activeTab === tab.id}
            >
              {tab.label}
              {activeTab === tab.id && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto min-h-0 flex-1">
          {activeTab === "general" && (
            <div className="animate-fade-in">
              {isJwtAuth ? (
                /* Logged in via JWT — show user info + logout */
                <div className="flex flex-col gap-4">
                  <div>
                    <label
                      className="mb-1.5 block text-[13px] font-medium"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      Logged in as
                    </label>
                    <div
                      className="rounded-xl border px-3 py-2.5 text-sm"
                      style={{
                        background: "var(--surface-2)",
                        borderColor: "var(--border)",
                        color: "var(--text)",
                      }}
                    >
                      {userEmail}
                    </div>
                  </div>
                  <button
                    className="self-start rounded-xl border px-4 py-2 text-sm font-medium transition-all hover:bg-[var(--surface-2)]"
                    style={{
                      borderColor: "#ef4444",
                      color: "#ef4444",
                    }}
                    onClick={() => {
                      onLogout();
                      onClose();
                    }}
                  >
                    Log out
                  </button>
                </div>
              ) : (
                /* API-key mode — show API key input */
                <>
                  <label
                    className="mb-1.5 block text-[13px] font-medium"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    API Key
                  </label>
                  <div className="relative">
                    <input
                      type="password"
                      className="w-full rounded-xl border px-3 py-2.5 pr-10 font-mono text-sm outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/25"
                      style={{
                        background: "var(--surface-2)",
                        borderColor: keyValid === false ? "#ef4444" : keyValid === true ? "#22c55e" : "var(--border)",
                        color: "var(--text)",
                      }}
                      value={keyInput}
                      onChange={(e) => {
                        setKeyInput(e.target.value);
                        setKeyValid(null);
                      }}
                      onBlur={handleKeyBlur}
                      placeholder="Enter your API key"
                      autoComplete="off"
                      aria-label="API key"
                    />
                    {keyValid !== null && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2">
                        {keyValid ? (
                          <CheckIcon size={16} className="text-green-500" />
                        ) : (
                          <XIcon size={16} className="text-red-500" />
                        )}
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
                    Used for authenticating with the Barongsai API.
                  </p>
                </>
              )}
            </div>
          )}

          {activeTab === "search" && (
            <SearchSettingsPanel
              chatMode={chatMode}
              settings={searchSettings}
              onUpdate={onUpdateSettings}
              onApplyPreset={onApplyPreset}
              onReset={onResetSettings}
              getActivePreset={getActivePreset}
            />
          )}

          {activeTab === "appearance" && (
            <div className="animate-fade-in">
              <label
                className="mb-3 block text-[13px] font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                Theme
              </label>
              <div className="grid grid-cols-3 gap-3">
                {themes.map((t) => {
                  const Icon = t.icon;
                  const isActive = theme === t.value;
                  return (
                    <button
                      key={t.value}
                      className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition-all ${
                        isActive ? "" : "hover:border-[var(--accent)]"
                      }`}
                      style={{
                        background: isActive ? "var(--accent-dim)" : "var(--surface-2)",
                        borderColor: isActive ? "var(--accent)" : "var(--border)",
                      }}
                      onClick={() => onSetTheme(t.value)}
                      aria-pressed={isActive}
                    >
                      <Icon
                        size={20}
                        className={isActive ? "text-[var(--accent)]" : ""}
                      />
                      <span
                        className="text-[13px] font-medium"
                        style={{
                          color: isActive ? "var(--accent)" : "var(--text-secondary)",
                        }}
                      >
                        {t.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "about" && (
            <div className="flex flex-col items-center gap-4 py-4 animate-fade-in">
              <div
                className="flex h-14 w-14 items-center justify-center rounded-2xl text-xl font-extrabold"
                style={{ background: "var(--accent)", color: "var(--bg)" }}
              >
                B
              </div>
              <div className="text-center">
                <h3 className="text-lg font-bold">Barongsai</h3>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  v1.0.0
                </p>
              </div>
              <p
                className="max-w-sm text-center text-[13px] leading-relaxed"
                style={{ color: "var(--text-secondary)" }}
              >
                An AI-powered search engine that finds, analyzes, and synthesizes
                information from across the web with cited sources.
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div
          className="flex justify-end gap-2 border-t px-6 py-4"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            className="rounded-xl border px-5 py-2 text-sm font-medium transition-all hover:bg-[var(--surface-2)]"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
            onClick={onClose}
          >
            Cancel
          </button>
          {!isJwtAuth && (
            <button
              className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-medium transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50"
              style={{ background: "var(--accent)", color: "var(--bg)" }}
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving && (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
              {isSaving ? "Saving..." : "Save"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
