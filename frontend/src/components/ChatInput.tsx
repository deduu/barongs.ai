import { useCallback, useRef } from "react";

interface ChatInputProps {
  disabled: boolean;
  onSend: (text: string) => void;
}

export default function ChatInput({ disabled, onSend }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "44px";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, []);

  const handleSend = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const text = ta.value.trim();
    if (!text || disabled) return;
    onSend(text);
    ta.value = "";
    ta.style.height = "44px";
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
    <div
      className="flex-shrink-0 border-t px-5 pb-4 pt-2.5"
      style={{
        borderColor: "var(--border)",
        background: "var(--surface)",
      }}
    >
      <div
        className="flex items-end gap-2.5 rounded-xl border px-3 py-2 transition-colors focus-within:border-[var(--accent)]"
        style={{
          background: "var(--surface-2)",
          borderColor: "var(--border)",
        }}
      >
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none border-none bg-transparent text-[15px] leading-relaxed outline-none placeholder:text-[var(--text-muted)]"
          style={{ color: "var(--text)", minHeight: 44, maxHeight: 200, fontFamily: "inherit" }}
          placeholder="Ask anything\u2026"
          rows={1}
          disabled={disabled}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
        />
        <button
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-white transition-colors disabled:cursor-not-allowed disabled:opacity-35"
          style={{ background: "var(--accent)" }}
          onClick={handleSend}
          disabled={disabled}
          title="Send (Enter)"
        >
          &#10148;
        </button>
      </div>
      <p className="mt-1 text-center text-[11px]" style={{ color: "var(--text-muted)" }}>
        Enter to send &nbsp;&middot;&nbsp; Shift+Enter for new line
      </p>
    </div>
  );
}
