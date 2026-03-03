import { useState } from "react";
import type { ChatMode } from "../types";
import type { SearchSettings, PresetName, ParamMeta } from "../lib/searchSettings";
import { PARAM_META } from "../lib/searchSettings";
import { GlobeIcon, LayersIcon, BookIcon } from "./icons";

interface SearchSettingsPanelProps {
  chatMode: ChatMode;
  settings: SearchSettings;
  onUpdate: <M extends ChatMode>(mode: M, partial: Partial<SearchSettings[M]>) => void;
  onApplyPreset: (mode: ChatMode, preset: PresetName) => void;
  onReset: (mode: ChatMode) => void;
  getActivePreset: (mode: ChatMode) => PresetName | null;
}

const MODE_TABS: { mode: ChatMode; label: string; Icon: typeof GlobeIcon }[] = [
  { mode: "search", label: "Web", Icon: GlobeIcon },
  { mode: "deep_search", label: "Deep", Icon: LayersIcon },
  { mode: "rag", label: "KB", Icon: BookIcon },
];

const PRESET_NAMES: PresetName[] = ["quick", "balanced", "thorough"];
const PRESET_LABELS: Record<PresetName, string> = {
  quick: "Quick",
  balanced: "Balanced",
  thorough: "Thorough",
};

export default function SearchSettingsPanel({
  chatMode,
  settings,
  onUpdate,
  onApplyPreset,
  onReset,
  getActivePreset,
}: SearchSettingsPanelProps) {
  const [editMode, setEditMode] = useState<ChatMode>(chatMode);
  const activePreset = getActivePreset(editMode);
  const modeSettings = settings[editMode];
  const meta = PARAM_META[editMode] as Record<string, ParamMeta>;
  const paramKeys = Object.keys(meta);

  return (
    <div className="animate-fade-in">
      {/* Mode sub-tabs */}
      <div className="mb-4 flex gap-1 rounded-xl p-1" style={{ background: "var(--surface-2)" }}>
        {MODE_TABS.map(({ mode, label, Icon }) => (
          <button
            key={mode}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[13px] font-medium transition-all"
            style={{
              background: editMode === mode ? "var(--surface)" : "transparent",
              color: editMode === mode ? "var(--text)" : "var(--text-muted)",
              boxShadow: editMode === mode ? "0 1px 3px rgba(0,0,0,.1)" : "none",
            }}
            onClick={() => setEditMode(mode)}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Preset buttons */}
      <div className="mb-4 flex gap-2">
        {PRESET_NAMES.map((preset) => (
          <button
            key={preset}
            className="flex-1 rounded-lg border py-1.5 text-[12px] font-medium transition-all"
            style={{
              background: activePreset === preset ? "var(--accent-dim)" : "var(--surface-2)",
              borderColor: activePreset === preset ? "var(--accent)" : "var(--border)",
              color: activePreset === preset ? "var(--accent)" : "var(--text-secondary)",
            }}
            onClick={() => onApplyPreset(editMode, preset)}
          >
            {PRESET_LABELS[preset]}
          </button>
        ))}
      </div>

      {/* Parameter controls */}
      <div className="flex flex-col gap-3">
        {paramKeys.map((key) => (
          <ParamControl
            key={key}
            paramKey={key}
            meta={meta[key]}
            value={(modeSettings as unknown as Record<string, unknown>)[key]}
            onChange={(val) => onUpdate(editMode, { [key]: val } as Partial<SearchSettings[typeof editMode]>)}
          />
        ))}
      </div>

      {/* Reset link */}
      <button
        className="mt-4 text-[12px] font-medium transition-colors hover:underline"
        style={{ color: "var(--text-muted)" }}
        onClick={() => onReset(editMode)}
      >
        Reset to defaults
      </button>
    </div>
  );
}

/* ── Generic parameter control ─────────────────────────── */

interface ParamControlProps {
  paramKey: string;
  meta: ParamMeta;
  value: unknown;
  onChange: (value: unknown) => void;
}

function ParamControl({ paramKey, meta, value, onChange }: ParamControlProps) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <label
          className="text-[13px] font-medium"
          style={{ color: "var(--text-secondary)" }}
          htmlFor={`param-${paramKey}`}
        >
          {meta.label}
        </label>
        {meta.type === "slider" && (
          <span className="text-[12px] font-mono" style={{ color: "var(--text-muted)" }}>
            {typeof value === "number" ? (meta.step < 1 ? value.toFixed(1) : value) : String(value)}
          </span>
        )}
      </div>

      {meta.type === "slider" && (
        <input
          id={`param-${paramKey}`}
          type="range"
          className="mt-1 w-full accent-[var(--accent)]"
          min={meta.min}
          max={meta.max}
          step={meta.step}
          value={value as number}
          onChange={(e) => onChange(parseFloat(e.target.value))}
        />
      )}

      {meta.type === "select" && (
        <select
          id={`param-${paramKey}`}
          className="mt-1 w-full rounded-lg border px-2 py-1.5 text-[13px] outline-none"
          style={{
            background: "var(--surface-2)",
            borderColor: "var(--border)",
            color: "var(--text)",
          }}
          value={value as string}
          onChange={(e) => onChange(e.target.value)}
        >
          {meta.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      {meta.type === "toggle" && (
        <button
          id={`param-${paramKey}`}
          role="switch"
          aria-checked={value as boolean}
          className="mt-1 relative h-6 w-11 rounded-full transition-colors"
          style={{
            background: (value as boolean) ? "var(--accent)" : "var(--surface-3)",
          }}
          onClick={() => onChange(!(value as boolean))}
        >
          <span
            className="absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform"
            style={{
              transform: (value as boolean) ? "translateX(20px)" : "translateX(0)",
            }}
          />
        </button>
      )}

      <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
        {meta.description}
      </p>
    </div>
  );
}
