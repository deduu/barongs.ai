import { useEffect, useMemo, useState } from "react";
import type { ChatMode } from "../types";

interface StatusIndicatorProps {
  message: string;
  chatMode?: ChatMode;
  startedAt?: number | null;
  lastEventAt?: number | null;
  eventCount?: number;
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

function formatDuration(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  if (mins <= 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export default function StatusIndicator({
  message,
  chatMode = "search",
  startedAt = null,
  lastEventAt = null,
  eventCount = 0,
}: StatusIndicatorProps) {
  const phases = chatMode === "deep_search" ? deepPhases : webPhases;
  const active = chatMode === "deep_search" ? getDeepPhase(message) : getWebPhase(message);
  const [expanded, setExpanded] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const elapsedSeconds = useMemo(() => {
    if (!startedAt) return 0;
    return Math.max(0, Math.floor((now - startedAt) / 1000));
  }, [startedAt, now]);

  const sinceLastEventSeconds = useMemo(() => {
    if (!lastEventAt) return 0;
    return Math.max(0, Math.floor((now - lastEventAt) / 1000));
  }, [lastEventAt, now]);

  const isStale = sinceLastEventSeconds >= 12;

  return (
    <div
      className="mb-4 animate-fade-in rounded-xl border p-3"
      style={{
        borderColor: isStale ? "rgba(245, 158, 11, 0.55)" : "var(--border)",
        background: "var(--surface)",
      }}
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-semibold" style={{ background: "var(--surface-2)", color: "var(--text)" }}>
          <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: isStale ? "#f59e0b" : "#22c55e" }} />
          Agent Working
        </div>
        <span className="min-w-0 flex-1 truncate text-right text-[11px]" style={{ color: "var(--text-secondary)" }}>
          {message}
        </span>
      </div>

      <div className="mt-2 flex items-center justify-between text-[11px]" style={{ color: "var(--text-secondary)" }}>
        <div className="flex flex-wrap items-center gap-3">
          <span>Elapsed {formatDuration(elapsedSeconds)}</span>
          <span>Last update {formatDuration(sinceLastEventSeconds)} ago</span>
        </div>
        <button
          type="button"
          className="rounded-md px-2 py-1 font-medium transition-colors hover:bg-[var(--surface-2)]"
          style={{ color: "var(--text)" }}
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={expanded ? "Hide progress details" : "Show progress details"}
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
      </div>

      {expanded && (
        <>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
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

          <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]" style={{ color: "var(--text-secondary)" }}>
            <span>Events {eventCount}</span>
            {isStale && (
              <span style={{ color: "#f59e0b" }}>
                Slow step detected, still processing
              </span>
            )}
          </div>

          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--surface-2)" }}>
            <div
              className="animate-stream-track h-full w-[35%] rounded-full"
              style={{ background: "var(--accent)" }}
            />
          </div>
        </>
      )}
    </div>
  );
}
