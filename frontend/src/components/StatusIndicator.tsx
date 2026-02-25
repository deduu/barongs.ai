interface StatusIndicatorProps {
  message: string;
}

const phases = [
  { key: "searching", label: "Searching" },
  { key: "reading", label: "Reading" },
  { key: "analyzing", label: "Analyzing" },
  { key: "writing", label: "Writing" },
] as const;

function getActivePhase(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("search")) return "searching";
  if (lower.includes("read") || lower.includes("fetch") || lower.includes("crawl")) return "reading";
  if (lower.includes("analy") || lower.includes("think") || lower.includes("process")) return "analyzing";
  return "writing";
}

export default function StatusIndicator({ message }: StatusIndicatorProps) {
  const active = getActivePhase(message);

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
