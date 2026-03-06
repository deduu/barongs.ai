import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMode, Message, Source } from "../types";
import MessageBubble from "./MessageBubble";
import StatusIndicator from "./StatusIndicator";
import ScrollToBottom from "./ScrollToBottom";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  statusMessage: string;
  streamStartedAt: number | null;
  lastEventAt: number | null;
  eventCount: number;
  selectedModel: string;
  chatMode: ChatMode;
  onSourceClick: (source: Source) => void;
  onRegenerate?: () => void;
}

export default function MessageList({
  messages,
  isStreaming,
  statusMessage,
  streamStartedAt,
  lastEventAt,
  eventCount,
  selectedModel,
  chatMode,
  onSourceClick,
  onRegenerate,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      setIsAtBottom(true);
    }
  }, []);

  // Track scroll position
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handler = () => {
      const threshold = 80;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
      setIsAtBottom(atBottom);
    };
    el.addEventListener("scroll", handler, { passive: true });
    return () => el.removeEventListener("scroll", handler);
  }, []);

  // Auto-scroll to bottom when new messages arrive (if already at bottom)
  useEffect(() => {
    if (isAtBottom) scrollToBottom();
  }, [messages, isStreaming, isAtBottom, scrollToBottom]);

  return (
    <div className="relative flex-1 overflow-hidden">
      <div
        ref={scrollRef}
        className="h-full overflow-y-auto px-4 py-6"
        style={{ scrollBehavior: "smooth" }}
        role="log"
        aria-live="polite"
        aria-busy={isStreaming}
      >
        <div className="mx-auto max-w-3xl">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} selectedModel={selectedModel} onSourceClick={onSourceClick} onRegenerate={onRegenerate} />
          ))}

          {/* Status indicator during streaming */}
          {isStreaming && (
            <StatusIndicator
              message={statusMessage || "Processing request\u2026"}
              chatMode={chatMode}
              startedAt={streamStartedAt}
              lastEventAt={lastEventAt}
              eventCount={eventCount}
            />
          )}
        </div>
      </div>

      {/* Scroll to bottom button */}
      {!isAtBottom && (
        <ScrollToBottom onClick={scrollToBottom} />
      )}
    </div>
  );
}
