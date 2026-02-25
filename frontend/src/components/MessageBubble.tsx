import { memo, useCallback, useEffect, useRef } from "react";
import type { Message, Source } from "../types";

function getFaviconUrl(url: string): string {
  try {
    return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=16`;
  } catch {
    return "";
  }
}

function truncateUrl(url: string, max = 35): string {
  try {
    const u = new URL(url);
    const s = u.hostname + u.pathname;
    return s.length > max ? s.slice(0, max) + "\u2026" : s;
  } catch {
    return url.slice(0, max);
  }
}

interface MessageBubbleProps {
  message: Message;
  onSourceClick: (source: Source) => void;
}

function MessageBubbleInner({ message, onSourceClick }: MessageBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);

  // Handle citation badge clicks via event delegation
  const handleBubbleClick = useCallback(
    (e: React.MouseEvent) => {
      const badge = (e.target as HTMLElement).closest(
        ".cite-badge",
      ) as HTMLElement | null;
      if (!badge) return;
      const idx = parseInt(badge.dataset.idx ?? "-1");
      if (idx >= 0 && message.sources[idx]) {
        onSourceClick(message.sources[idx]);
      }
    },
    [message.sources, onSourceClick],
  );

  // Auto-scroll kept in parent; this component just renders
  useEffect(() => {
    // no-op — scroll is handled by MessageList
  }, []);

  if (message.role === "user") {
    return (
      <div className="flex flex-col items-end gap-1 mb-6 animate-slide-up">
        <div className="text-xs font-medium" style={{ color: "var(--accent)" }}>
          You
        </div>
        <div
          className="rounded-xl border px-4 py-3 text-[15px] leading-[1.75] break-words"
          style={{
            maxWidth: "min(700px, 88%)",
            background: "var(--user-bubble)",
            borderColor: "rgba(99, 102, 241, 0.15)",
            borderBottomRightRadius: 4,
          }}
          dangerouslySetInnerHTML={{ __html: message.renderedHtml }}
        />
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex flex-col items-start gap-1.5 mb-6 animate-slide-up">
      <div
        className="flex items-center gap-1.5 text-xs font-medium"
        style={{ color: "var(--text-muted)" }}
      >
        <div
          className="flex h-5 w-5 items-center justify-center rounded-[5px] text-[10px] font-extrabold text-white"
          style={{
            background: "linear-gradient(135deg, var(--accent), var(--accent-hover))",
          }}
        >
          B
        </div>
        Barongsai
      </div>

      {/* Source chips */}
      {message.sources.length > 0 && (
        <div
          className="flex flex-wrap gap-1.5 mb-2"
          style={{ maxWidth: "min(780px, 92%)" }}
        >
          {message.sources.map((src, i) => (
            <button
              key={i}
              className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
                maxWidth: 210,
                overflow: "hidden",
              }}
              onClick={() => onSourceClick(src)}
            >
              <img
                src={getFaviconUrl(src.url)}
                alt=""
                className="h-3 w-3 flex-shrink-0"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
              <span className="truncate">
                {src.title || truncateUrl(src.url)}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div
        ref={bubbleRef}
        className={`msg-content text-[15px] leading-[1.75] break-words ${message.status === "streaming" ? "streaming-cursor" : ""}`}
        style={{ maxWidth: "min(780px, 92%)" }}
        onClick={handleBubbleClick}
        dangerouslySetInnerHTML={{ __html: message.renderedHtml }}
      />
    </div>
  );
}

const MessageBubble = memo(MessageBubbleInner);
export default MessageBubble;
