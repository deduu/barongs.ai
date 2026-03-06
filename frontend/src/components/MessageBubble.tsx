import { memo, useCallback, useRef, useState } from "react";
import type { Message, Source } from "../types";
import SourceCards from "./SourceCards";
import MessageActions from "./MessageActions";
import { CopyIcon, CheckIcon } from "./icons";

interface MessageBubbleProps {
  message: Message;
  selectedModel: string;
  onSourceClick: (source: Source) => void;
  onRegenerate?: () => void;
}

function MessageBubbleInner({ message, selectedModel, onSourceClick, onRegenerate }: MessageBubbleProps) {
  const bubbleRef = useRef<HTMLDivElement>(null);

  const handleBubbleClick = useCallback(
    (e: React.MouseEvent) => {
      const badge = (e.target as HTMLElement).closest(".cite-badge") as HTMLElement | null;
      if (badge) {
        e.preventDefault();
        const badgeUrl = badge.dataset.url;
        const badgeLabel = badge.dataset.label;
        if (badgeUrl) {
          const matched = message.sources.find((source) => source.url === badgeUrl);
          if (matched) {
            onSourceClick(matched);
            return;
          }
          onSourceClick({
            url: badgeUrl,
            title: badgeLabel || badgeUrl,
          });
          return;
        }

        const idx = parseInt(badge.dataset.idx ?? "-1", 10);
        if (idx >= 0 && message.sources[idx]) {
          onSourceClick(message.sources[idx]);
        }
        return;
      }

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

  const [userCopied, setUserCopied] = useState(false);

  const handleUserCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setUserCopied(true);
      setTimeout(() => setUserCopied(false), 2000);
    } catch {
      // Clipboard API failed; ignore.
    }
  }, [message.content]);

  if (message.role === "user") {
    return (
      <div className="group mb-6 flex flex-col items-end gap-1.5 animate-fade-in-up">
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
        <div className="flex justify-end opacity-0 transition-opacity group-hover:opacity-100">
          <button
            className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: userCopied ? "var(--accent)" : "var(--text-muted)" }}
            onClick={handleUserCopy}
            title={userCopied ? "Copied!" : "Copy"}
            aria-label={userCopied ? "Copied to clipboard" : "Copy message"}
          >
            {userCopied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="group mb-6 animate-fade-in-up">
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

      <SourceCards sources={message.sources} onSourceClick={onSourceClick} />

      <div
        ref={bubbleRef}
        className={`msg-content text-[15px] leading-[1.75] break-words ${
          message.status === "streaming" ? "streaming-cursor" : ""
        }`}
        onClick={handleBubbleClick}
        dangerouslySetInnerHTML={{ __html: message.renderedHtml }}
      />

      {(message.status === "done" || message.status === "error") && (
        <MessageActions messageId={message.id} rawContent={message.content} onRegenerate={onRegenerate} />
      )}
    </div>
  );
}

const MessageBubble = memo(MessageBubbleInner);
export default MessageBubble;
