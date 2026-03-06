import type { ChatMode } from "../types";
import { GlobeIcon, LayersIcon, BookIcon } from "./icons";

interface RAGModeToggleProps {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
  disabled?: boolean;
}

function ToggleButton({
  active,
  onClick,
  label,
  ariaLabel,
  disabled = false,
  children,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  ariaLabel: string;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] font-medium transition-all disabled:cursor-not-allowed disabled:opacity-45"
      style={{
        background: active ? "var(--surface)" : "transparent",
        color: active ? "var(--text)" : "var(--text-muted)",
        boxShadow: active ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
      }}
      onClick={onClick}
      disabled={disabled}
      role="radio"
      aria-checked={active}
      aria-label={ariaLabel}
    >
      {children}
      <span>{label}</span>
    </button>
  );
}

export default function RAGModeToggle({
  mode,
  onChange,
  disabled = false,
}: RAGModeToggleProps) {
  return (
    <div
      className="inline-flex items-center rounded-lg border p-0.5"
      style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
      role="radiogroup"
      aria-label="Chat mode"
      aria-disabled={disabled}
    >
      <ToggleButton
        active={mode === "search"}
        onClick={() => onChange("search")}
        label="Web"
        ariaLabel="Web Search mode"
        disabled={disabled}
      >
        <GlobeIcon size={13} />
      </ToggleButton>
      <ToggleButton
        active={mode === "deep_search"}
        onClick={() => onChange("deep_search")}
        label="Deep"
        ariaLabel="Deep Research mode"
        disabled={disabled}
      >
        <LayersIcon size={13} />
      </ToggleButton>
      <ToggleButton
        active={mode === "rag"}
        onClick={() => onChange("rag")}
        label="KB"
        ariaLabel="Knowledge Base mode"
        disabled={disabled}
      >
        <BookIcon size={13} />
      </ToggleButton>
    </div>
  );
}
