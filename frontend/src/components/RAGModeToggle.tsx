import type { ChatMode } from "../types";
import { GlobeIcon, BookIcon } from "./icons";

interface RAGModeToggleProps {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
}

export default function RAGModeToggle({ mode, onChange }: RAGModeToggleProps) {
  return (
    <div
      className="inline-flex items-center rounded-lg border p-0.5"
      style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}
      role="radiogroup"
      aria-label="Chat mode"
    >
      <button
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] font-medium transition-all"
        style={{
          background: mode === "search" ? "var(--surface)" : "transparent",
          color: mode === "search" ? "var(--text)" : "var(--text-muted)",
          boxShadow: mode === "search" ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
        }}
        onClick={() => onChange("search")}
        role="radio"
        aria-checked={mode === "search"}
        aria-label="Web Search mode"
      >
        <GlobeIcon size={13} />
        <span>Web</span>
      </button>
      <button
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] font-medium transition-all"
        style={{
          background: mode === "rag" ? "var(--surface)" : "transparent",
          color: mode === "rag" ? "var(--text)" : "var(--text-muted)",
          boxShadow: mode === "rag" ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
        }}
        onClick={() => onChange("rag")}
        role="radio"
        aria-checked={mode === "rag"}
        aria-label="Knowledge Base mode"
      >
        <BookIcon size={13} />
        <span>KB</span>
      </button>
    </div>
  );
}
