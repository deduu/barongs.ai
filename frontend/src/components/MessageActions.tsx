import { useCallback, useState } from "react";
import { CopyIcon, CheckIcon, ThumbsUpIcon, ThumbsDownIcon, RotateCcwIcon } from "./icons";
import { getItem, setItem } from "../lib/storage";

interface MessageActionsProps {
  messageId: string;
  rawContent: string;
  onRegenerate?: () => void;
}

export default function MessageActions({ messageId, rawContent, onRegenerate }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const feedbackKey = `feedback_${messageId}`;
  const [feedback, setFeedback] = useState<"up" | "down" | null>(
    () => getItem<"up" | "down" | null>(feedbackKey, null),
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(rawContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API failed — silently ignore
    }
  }, [rawContent]);

  const handleFeedback = useCallback(
    (value: "up" | "down") => {
      const next = feedback === value ? null : value;
      setFeedback(next);
      setItem(feedbackKey, next);
    },
    [feedback, feedbackKey],
  );

  return (
    <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
      <button
        className="flex h-7 items-center gap-1 rounded-md px-2 text-xs transition-colors hover:bg-[var(--surface-2)]"
        style={{ color: copied ? "var(--accent)" : "var(--text-muted)" }}
        onClick={handleCopy}
        title={copied ? "Copied!" : "Copy"}
        aria-label={copied ? "Copied to clipboard" : "Copy response"}
      >
        {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
        <span>{copied ? "Copied!" : "Copy"}</span>
      </button>

      <button
        className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
        style={{ color: feedback === "up" ? "var(--accent)" : "var(--text-muted)" }}
        onClick={() => handleFeedback("up")}
        title="Helpful"
        aria-label="Mark as helpful"
        aria-pressed={feedback === "up"}
      >
        <ThumbsUpIcon size={14} />
      </button>

      <button
        className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
        style={{ color: feedback === "down" ? "#ef4444" : "var(--text-muted)" }}
        onClick={() => handleFeedback("down")}
        title="Not helpful"
        aria-label="Mark as not helpful"
        aria-pressed={feedback === "down"}
      >
        <ThumbsDownIcon size={14} />
      </button>

      {onRegenerate && (
        <button
          className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
          style={{ color: "var(--text-muted)" }}
          onClick={onRegenerate}
          title="Regenerate"
          aria-label="Regenerate response"
        >
          <RotateCcwIcon size={14} />
        </button>
      )}
    </div>
  );
}
