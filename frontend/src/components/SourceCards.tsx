import { useState } from "react";
import type { Source } from "../types";
import { ChevronDownIcon } from "./icons";

function getFaviconUrl(url: string): string {
  try {
    return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=16`;
  } catch {
    return "";
  }
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

interface SourceCardsProps {
  sources: Source[];
  onSourceClick: (source: Source) => void;
}

export default function SourceCards({ sources, onSourceClick }: SourceCardsProps) {
  const [showAll, setShowAll] = useState(false);

  if (sources.length === 0) return null;

  const visibleCount = showAll ? sources.length : Math.min(4, sources.length);
  const visible = sources.slice(0, visibleCount);
  const remaining = sources.length - 4;

  return (
    <div className="mb-3">
      {/* Horizontal scrollable row */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {visible.map((src, i) => (
          <button
            key={i}
            className="glass flex flex-shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left text-xs transition-all hover:border-[var(--accent)] active:scale-[0.98]"
            style={{ maxWidth: 220 }}
            onClick={() => onSourceClick(src)}
            aria-label={`Source: ${src.title || getDomain(src.url)}`}
          >
            <img
              src={getFaviconUrl(src.url)}
              alt=""
              className="h-4 w-4 flex-shrink-0 rounded"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium" style={{ color: "var(--text)" }}>
                {src.title || getDomain(src.url)}
              </div>
              <div className="truncate" style={{ color: "var(--text-muted)" }}>
                {getDomain(src.url)}
              </div>
            </div>
          </button>
        ))}

        {/* +N more button */}
        {remaining > 0 && !showAll && (
          <button
            className="glass flex flex-shrink-0 items-center gap-1 rounded-lg px-3 py-2 text-xs transition-all hover:border-[var(--accent)]"
            style={{ color: "var(--text-secondary)" }}
            onClick={() => setShowAll(true)}
            aria-label={`Show ${remaining} more sources`}
          >
            <span>+{remaining}</span>
            <ChevronDownIcon size={12} />
          </button>
        )}
      </div>
    </div>
  );
}
