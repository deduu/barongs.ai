import { useCallback, useRef, useState } from "react";
import type { ChatMode } from "../types";
import { SendIcon, PlusIcon } from "./icons";
import RAGModeToggle from "./RAGModeToggle";

interface ChatInputProps {
  disabled: boolean;
  chatMode: ChatMode;
  onChatModeChange: (mode: ChatMode) => void;
  onSend: (text: string) => void;
}

export default function ChatInput({
  disabled,
  chatMode,
  onChatModeChange,
  onSend,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [charCount, setCharCount] = useState(0);

  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "44px";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
    setCharCount(ta.value.length);
  }, []);

  const handleSend = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const text = ta.value.trim();
    if (!text || disabled) return;
    onSend(text);
    ta.value = "";
    ta.style.height = "44px";
    setCharCount(0);
  }, [disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="flex-shrink-0 px-4 pb-4 pt-2">
      <div className="mx-auto max-w-3xl">
        <div
          className="rounded-2xl border"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <div className="px-4 pt-3 pb-2">
            <textarea
              ref={textareaRef}
              className="w-full resize-none border-none bg-transparent text-[15px] leading-relaxed outline-none placeholder:text-[var(--text-muted)]"
              style={{ color: "var(--text)", minHeight: 44, maxHeight: 200, fontFamily: "inherit" }}
              placeholder={
                chatMode === "rag"
                  ? "Ask about your documents..."
                  : "Ask anything..."
              }
              rows={1}
              disabled={disabled}
              onInput={autoResize}
              onKeyDown={handleKeyDown}
              aria-label="Message input"
            />
          </div>
          {/* Bottom toolbar */}
          <div
            className="flex items-center justify-between border-t px-3 py-2"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex items-center gap-2">
              <button
                className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
                style={{ color: "var(--text-muted)" }}
                title="Attach file"
                aria-label="Attach file"
              >
                <PlusIcon size={18} />
              </button>
              <RAGModeToggle mode={chatMode} onChange={onChatModeChange} />
              {charCount > 100 && (
                <span
                  className="text-[10px] tabular-nums"
                  style={{ color: "var(--text-muted)" }}
                >
                  {charCount}
                </span>
              )}
            </div>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-all hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-35"
              style={{ background: "var(--accent)", color: "var(--bg)" }}
              onClick={handleSend}
              disabled={disabled}
              title="Send (Enter)"
              aria-label="Send message"
            >
              <SendIcon size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
