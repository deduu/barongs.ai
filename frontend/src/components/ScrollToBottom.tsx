import { ArrowDownIcon } from "./icons";

interface ScrollToBottomProps {
  onClick: () => void;
}

export default function ScrollToBottom({ onClick }: ScrollToBottomProps) {
  return (
    <button
      className="glass-accent absolute bottom-4 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium transition-all hover:opacity-90 active:scale-[0.97] animate-fade-in-up"
      style={{ color: "var(--text)" }}
      onClick={onClick}
      aria-label="Scroll to bottom"
    >
      <ArrowDownIcon size={14} />
      <span>New messages</span>
    </button>
  );
}
