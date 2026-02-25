import { useCallback, useRef } from "react";
import {
  SendIcon,
  PlusIcon,
  SettingsIcon,
  CodeIcon,
  PenIcon,
  FileIcon,
  GlobeIcon,
  SearchIcon,
} from "./icons";

interface WelcomeScreenProps {
  onSend: (text: string) => void;
}

const actionChips = [
  { icon: FileIcon, label: "Create slides" },
  { icon: GlobeIcon, label: "Build website" },
  { icon: CodeIcon, label: "Develop apps" },
  { icon: PenIcon, label: "Design" },
  { icon: SearchIcon, label: "More" },
];

const toolDots = [
  { color: "#3b82f6", label: "Slack" },
  { color: "#ef4444", label: "Gmail" },
  { color: "#f59e0b", label: "Calendar" },
  { color: "#10b981", label: "GitHub" },
  { color: "#8b5cf6", label: "Notion" },
];

export default function WelcomeScreen({ onSend }: WelcomeScreenProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const val = inputRef.current?.value.trim();
    if (!val) return;
    onSend(val);
    if (inputRef.current) inputRef.current.value = "";
  }, [onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 px-5 py-10">
      {/* Heading */}
      <h1
        className="text-center text-3xl font-semibold sm:text-4xl animate-fade-in"
        style={{ color: "var(--text)" }}
      >
        What can I do for you?
      </h1>

      {/* Main input */}
      <div className="w-full max-w-2xl animate-fade-in-up stagger-1">
        <div
          className="rounded-2xl border"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <div className="px-4 pt-4 pb-2">
            <textarea
              ref={inputRef}
              className="w-full resize-none border-none bg-transparent text-[15px] leading-relaxed outline-none placeholder:text-[var(--text-muted)]"
              style={{ color: "var(--text)", minHeight: 60, maxHeight: 160, fontFamily: "inherit" }}
              placeholder="Ask anything..."
              rows={2}
              onKeyDown={handleKeyDown}
              onInput={() => {
                const ta = inputRef.current;
                if (!ta) return;
                ta.style.height = "60px";
                ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
              }}
              aria-label="Search query"
            />
          </div>
          {/* Bottom toolbar */}
          <div
            className="flex items-center justify-between border-t px-3 py-2"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex items-center gap-1">
              <button
                className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
                style={{ color: "var(--text-muted)" }}
                title="Attach file"
                aria-label="Attach file"
              >
                <PlusIcon size={18} />
              </button>
              <button
                className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
                style={{ color: "var(--text-muted)" }}
                title="Tools"
                aria-label="Tools"
              >
                <SettingsIcon size={16} />
              </button>
            </div>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-all hover:opacity-90 active:scale-95"
              style={{ background: "var(--accent)", color: "var(--bg)" }}
              onClick={handleSubmit}
              aria-label="Send"
            >
              <SendIcon size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Connect your tools */}
      <div className="flex flex-col items-center gap-2 animate-fade-in-up stagger-2">
        <span className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Connect your tools to Barongsai
        </span>
        <div className="flex items-center gap-2">
          {toolDots.map(({ color, label }) => (
            <div
              key={label}
              className="flex h-7 w-7 items-center justify-center rounded-full border"
              style={{ borderColor: "var(--border)" }}
              title={label}
            >
              <div
                className="h-3 w-3 rounded-full"
                style={{ background: color }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Action chips */}
      <div className="flex flex-wrap justify-center gap-2 animate-fade-in-up stagger-3">
        {actionChips.map(({ icon: Icon, label }) => (
          <button
            key={label}
            className="flex items-center gap-2 rounded-full border px-4 py-2 text-[13px] transition-all hover:bg-[var(--surface-2)] active:scale-[0.97]"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            onClick={() => onSend(label)}
          >
            <Icon size={14} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Promo card */}
      <div
        className="w-full max-w-md rounded-xl border p-4 animate-fade-in-up stagger-4"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="flex items-start gap-3">
          <div className="flex gap-1 pt-1">
            <div className="h-2 w-2 rounded-full bg-blue-500" />
            <div className="h-2 w-2 rounded-full bg-amber-500" />
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <div>
            <div className="text-[14px] font-medium" style={{ color: "var(--text)" }}>
              Web Search & Analysis
            </div>
            <p className="mt-1 text-[12px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Search the web, analyze results, and get cited answers — powered by multiple AI models.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
