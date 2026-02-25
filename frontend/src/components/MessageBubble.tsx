import { memo, useCallback, useRef } from "react";
import type { Message, Source } from "../types";
import SourceCards from "./SourceCards";
import MessageActions from "./MessageActions";

interface MessageBubbleProps {
  message: Message;
  selectedModel: string;
  onSourceClick: (source: Source) => void;
}

function MessageBubbleInner({ message, selectedModel, onSourceClick }: MessageBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);

  // Handle citation badge clicks + intercept link navigation via event delegation
  const handleBubbleClick = useCallback(
    (e: React.MouseEvent) => {
      // Citation badge → open source panel
      const badge = (e.target as HTMLElement).closest(
        ".cite-badge",
      ) as HTMLElement | null;
      if (badge) {
        e.preventDefault();
        const idx = parseInt(badge.dataset.idx ?? "-1");
        if (idx >= 0 && message.sources[idx]) {
          onSourceClick(message.sources[idx]);
        }
        return;
      }

      // Regular link → force open in new tab (safety net)
      const anchor = (e.target as HTMLElement).closest("a") as HTMLAnchorElement | null;
      if (anchor && anchor.href) {
        e.preventDefault();
        window.open(anchor.href, "_blank", "noopener,noreferrer");
      }
    },
    [message.sources, onSourceClick],
  );

  const timeStr = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (message.role === "user") {
    return (
      <div className="mb-6 flex flex-col items-end gap-1.5 animate-fade-in-up">
        <div className="flex items-center gap-2">
          <span
            className="text-[11px] opacity-0 transition-opacity group-hover:opacity-100"
            style={{ color: "var(--text-muted)" }}
          >
            {timeStr}
          </span>
          <div
            className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold"
            style={{ background: "var(--accent)", color: "var(--bg)" }}
          >
            U
          </div>
        </div>
        <div
          className="glass rounded-2xl rounded-br-md px-4 py-3 text-[15px] leading-[1.75] break-words"
          style={{ maxWidth: "min(600px, 85%)" }}
          dangerouslySetInnerHTML={{ __html: message.renderedHtml }}
        />
      </div>
    );
  }

  // Assistant message
  return (
    <div className="group mb-6 animate-fade-in-up">
      {/* Avatar + model name */}
      <div className="mb-2 flex items-center gap-2">
        <div
          className="flex h-7 flex-shrink-0 items-center justify-center rounded-lg px-2 text-[11px] font-semibold"
          style={{ background: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
        >
          {selectedModel || "AI"}
        </div>
        <span
          className="text-[11px] opacity-0 transition-opacity group-hover:opacity-100"
          style={{ color: "var(--text-muted)" }}
        >
          {timeStr}
        </span>
      </div>

      {/* Inline source cards */}
      <SourceCards sources={message.sources} onSourceClick={onSourceClick} />

      {/* Content */}
      <div
        ref={bubbleRef}
        className={`msg-content text-[15px] leading-[1.75] break-words ${
          message.status === "streaming" ? "streaming-cursor" : ""
        }`}
        onClick={handleBubbleClick}
        dangerouslySetInnerHTML={{ __html: message.renderedHtml }}
      />

      {/* Actions (copy, feedback) */}
      {message.status === "done" && (
        <MessageActions messageId={message.id} rawContent={message.content} />
      )}
    </div>
  );
}

const MessageBubble = memo(MessageBubbleInner);
export default MessageBubble;
