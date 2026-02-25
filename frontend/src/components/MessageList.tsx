import { useEffect, useRef } from "react";
import type { Message, Source } from "../types";
import MessageBubble from "./MessageBubble";

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
  statusMessage: string;
  onSourceClick: (source: Source) => void;
  onQuickSend: (text: string) => void;
}

export default function MessageList({
  messages,
  isStreaming,
  statusMessage,
  onSourceClick,
  onQuickSend,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isStreaming]);

  return (
    <>
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-6"
        style={{ scrollBehavior: "smooth" }}
      >
        {messages.length === 0 ? (
          <div className="flex min-h-[70%] flex-col items-center justify-center gap-3.5 text-center px-5 animate-fade-in">
            <div
              className="flex h-16 w-16 items-center justify-center rounded-[18px] text-[28px] mb-1"
              style={{
                background:
                  "linear-gradient(135deg, var(--accent), var(--accent-hover))",
              }}
            >
              &#128269;
            </div>
            <h1 className="text-[26px] font-bold">
              What would you like to know?
            </h1>
            <p
              className="max-w-[420px] text-[15px]"
              style={{ color: "var(--text-secondary)" }}
            >
              Ask anything &mdash; I'll search the web and give you a cited,
              synthesized answer.
            </p>
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              {[
                ["Latest developments in AI agents", "Latest AI agents"],
                ["How does quantum computing work?", "Quantum computing"],
                [
                  "What is the current state of fusion energy?",
                  "Fusion energy",
                ],
                ["Python async best practices 2025", "Python async"],
              ].map(([query, label]) => (
                <button
                  key={label}
                  className="rounded-full border px-4 py-2 text-[13px] transition-colors hover:border-[var(--accent)] hover:text-[var(--text)]"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--text-secondary)",
                  }}
                  onClick={() => onQuickSend(query)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onSourceClick={onSourceClick}
            />
          ))
        )}
      </div>

      {/* Status bar */}
      <div
        className="flex min-h-[28px] flex-shrink-0 items-center gap-2.5 px-5 text-[13px]"
        style={{ color: "var(--text-secondary)" }}
      >
        {isStreaming && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <span
                className="h-[5px] w-[5px] rounded-full animate-bounce-dot"
                style={{ background: "var(--accent)" }}
              />
              <span
                className="h-[5px] w-[5px] rounded-full animate-bounce-dot-2"
                style={{ background: "var(--accent)" }}
              />
              <span
                className="h-[5px] w-[5px] rounded-full animate-bounce-dot-3"
                style={{ background: "var(--accent)" }}
              />
            </div>
            <span>{statusMessage}</span>
          </div>
        )}
      </div>
    </>
  );
}
