import type { Source } from "../types";
import { XIcon, ExternalLinkIcon } from "./icons";

function getFaviconUrl(url: string): string {
  try {
    return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=16`;
  } catch {
    return "";
  }
}

interface SourcePanelProps {
  open: boolean;
  source: Source | null;
  onClose: () => void;
}

export default function SourcePanel({ open, source, onClose }: SourcePanelProps) {
  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 z-[90] bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className="fixed right-0 top-0 z-[100] flex h-screen flex-col overflow-hidden border-l transition-transform"
        style={{
          width: "var(--source-w)",
          maxWidth: "100vw",
          background: "var(--surface)",
          borderColor: "var(--border)",
          transform: open ? "translateX(0)" : "translateX(100%)",
          transitionDuration: "var(--dur)",
          transitionTimingFunction: "var(--ease)",
        }}
        aria-label="Source detail"
      >
        {/* Header */}
        <div
          className="flex h-[var(--header-h)] flex-shrink-0 items-center justify-between border-b px-5"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-sm font-semibold">Source</span>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-secondary)" }}
            onClick={onClose}
            aria-label="Close source panel"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {source && (
            <div className="animate-fade-in">
              <div className="mb-4 flex items-start gap-2.5">
                <img
                  className="mt-0.5 h-5 w-5 flex-shrink-0 rounded"
                  src={getFaviconUrl(source.url)}
                  alt=""
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
                <div className="min-w-0">
                  <div className="text-base font-semibold leading-snug">
                    {source.title || "Untitled"}
                  </div>
                  <div
                    className="mt-0.5 break-all text-xs"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {source.url}
                  </div>
                </div>
              </div>

              {source.snippet && (
                <div
                  className="mb-4 rounded-lg border-l-2 border-l-[var(--accent)] px-3.5 py-3 text-[13px] leading-relaxed"
                  style={{
                    background: "var(--surface-2)",
                    color: "var(--text-secondary)",
                  }}
                >
                  {source.snippet}
                </div>
              )}

              {source.content && (
                <div>
                  <div
                    className="mb-2 text-[11px] font-semibold uppercase tracking-wide"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Content excerpt
                  </div>
                  <div
                    className="max-h-[280px] overflow-y-auto text-[13px] leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {source.content.slice(0, 1500)}
                    {source.content.length > 1500 ? "\u2026" : ""}
                  </div>
                </div>
              )}

              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-[13px] font-medium transition-all hover:opacity-90 active:scale-[0.97]"
                style={{ background: "var(--accent)", color: "var(--bg)" }}
              >
                <ExternalLinkIcon size={14} />
                Open in new tab
              </a>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
