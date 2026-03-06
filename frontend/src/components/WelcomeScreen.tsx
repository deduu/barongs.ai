import { useCallback, useRef } from "react";
import { motion } from "framer-motion";
import type { ChatMode } from "../types";
import {
  SendIcon,
  PlusIcon,
  SettingsIcon,
  CodeIcon,
  PenIcon,
  FileIcon,
  GlobeIcon,
  SearchIcon,
  SlackIcon,
  MailIcon,
  CalendarIcon,
  GitHubIcon,
  NotionIcon,
} from "./icons";
import RAGModeToggle from "./RAGModeToggle";

interface WelcomeScreenProps {
  onSend: (text: string) => void;
  chatMode: ChatMode;
  onChatModeChange: (mode: ChatMode) => void;
}

const actionChips = [
  { icon: FileIcon, label: "Create slides" },
  { icon: GlobeIcon, label: "Build website" },
  { icon: CodeIcon, label: "Develop apps" },
  { icon: PenIcon, label: "Design" },
  { icon: SearchIcon, label: "More" },
];

const toolItems = [
  { icon: SlackIcon, color: "#3b82f6", label: "Slack" },
  { icon: MailIcon, color: "#ef4444", label: "Gmail" },
  { icon: CalendarIcon, color: "#f59e0b", label: "Calendar" },
  { icon: GitHubIcon, color: "#10b981", label: "GitHub" },
  { icon: NotionIcon, color: "#8b5cf6", label: "Notion" },
];

export default function WelcomeScreen({ onSend, chatMode, onChatModeChange }: WelcomeScreenProps) {
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
    <div className="flex flex-1 flex-col items-center justify-center gap-8 overflow-y-auto px-5 py-10">
      {/* Heading */}
      <motion.h1
        className="text-center text-3xl font-semibold sm:text-4xl"
        style={{ color: "var(--text)" }}
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        What can I do for you?
      </motion.h1>

      {/* Main input */}
      <motion.div
        className="w-full max-w-2xl"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
      >
        <div
          className="rounded-2xl border"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <div className="px-4 pt-4 pb-2">
            <textarea
              ref={inputRef}
              className="w-full resize-none border-none bg-transparent text-[15px] leading-relaxed outline-none transition-all focus:ring-2 focus:ring-[var(--accent)]/25 rounded-xl placeholder:text-[var(--text-muted)]"
              style={{ color: "var(--text)", minHeight: 60, maxHeight: 160, fontFamily: "inherit" }}
              placeholder={chatMode === "rag" ? "Ask about your documents..." : chatMode === "deep_search" ? "Ask a research question..." : "Ask anything..."}
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
      </motion.div>

      {/* Connect your tools */}
      <motion.div
        className="flex flex-col items-center gap-2"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
      >
        <span className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          Connect your tools to Barongsai
        </span>
        <motion.div
          className="flex items-center gap-2"
          initial="initial"
          whileInView="animate"
          viewport={{ once: true }}
          variants={{ animate: { transition: { staggerChildren: 0.06, delayChildren: 0.25 } } }}
        >
          {toolItems.map(({ icon: Icon, color, label }) => (
            <motion.div
              key={label}
              variants={{ initial: { opacity: 0, scale: 0.8 }, animate: { opacity: 1, scale: 1 } }}
              className="flex h-8 w-8 items-center justify-center rounded-full border transition-colors hover:bg-[var(--surface-2)]"
              style={{ borderColor: "var(--border)", color }}
              title={label}
            >
              <Icon size={15} />
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Action chips */}
      <motion.div
        className="flex flex-wrap justify-center gap-2"
        initial="initial"
        whileInView="animate"
        viewport={{ once: true }}
        variants={{ animate: { transition: { staggerChildren: 0.06, delayChildren: 0.3 } } }}
      >
        {actionChips.map(({ icon: Icon, label }) => (
          <motion.button
            key={label}
            variants={{ initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } }}
            className="flex items-center gap-2 rounded-full border px-4 py-2 text-[13px] transition-all hover:bg-[var(--surface-2)] active:scale-[0.97]"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
            onClick={() => onSend(label)}
          >
            <Icon size={14} />
            <span>{label}</span>
          </motion.button>
        ))}
      </motion.div>

      {/* Promo card */}
      <motion.div
        className="w-full max-w-md rounded-xl border p-4"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: 0.4, ease: "easeOut" }}
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
      </motion.div>
    </div>
  );
}
