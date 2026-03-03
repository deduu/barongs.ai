import type { ChatMode } from "../types";

interface StatusIndicatorProps {
  message: string;
  chatMode?: ChatMode;
}

const webPhases = [
  { key: "searching", label: "Searching" },
  { key: "reading", label: "Reading" },
  { key: "analyzing", label: "Analyzing" },
  { key: "writing", label: "Writing" },
] as const;

const deepPhases = [
  { key: "planning", label: "Planning" },
  { key: "researching", label: "Researching" },
  { key: "reflecting", label: "Reflecting" },
  { key: "synthesizing", label: "Synthesizing" },
] as const;

function getWebPhase(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("search")) return "searching";
  if (lower.includes("read") || lower.includes("fetch") || lower.includes("crawl")) return "reading";
  if (lower.includes("analy") || lower.includes("think") || lower.includes("process")) return "analyzing";
  return "writing";
}

function getDeepPhase(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("plan")) return "planning";
  if (lower.includes("research") || lower.includes("finding")) return "researching";
  if (lower.includes("reflect") || lower.includes("check") || lower.includes("verif")) return "reflecting";
  if (lower.includes("synth") || lower.includes("report") || lower.includes("generat")) return "synthesizing";
  return "planning";
}

export default function StatusIndicator({ message, chatMode = "search" }: StatusIndicatorProps) {
  const phases = chatMode === "deep_search" ? deepPhases : webPhases;
  const active = chatMode === "deep_search" ? getDeepPhase(message) : getWebPhase(message);

  return (
    <div className="mb-4 flex items-center gap-2 animate-fade-in" role="status" aria-label={message}>
      <div className="flex items-center gap-1.5">
        {phases.map(({ key, label }) => {
          const isActive = key === active;
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-all"
              style={{
                background: isActive ? "var(--accent)" : "var(--surface-2)",
                color: isActive ? "var(--bg)" : "var(--text-muted)",
              }}
            >
              {isActive && (
                <span
                  className="h-1.5 w-1.5 rounded-full animate-pulse-glow"
                  style={{ background: "currentColor" }}
                />
              )}
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}
