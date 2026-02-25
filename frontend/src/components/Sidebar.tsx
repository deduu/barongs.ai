import type { Conversation } from "../types";

interface SidebarProps {
  open: boolean;
  isMobile: boolean;
  conversations: Conversation[];
  currentConvId: string | null;
  onNewChat: () => void;
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onOpenSettings: () => void;
  onClose: () => void;
}

export default function Sidebar({
  open,
  isMobile,
  conversations,
  currentConvId,
  onNewChat,
  onLoadConversation,
  onDeleteConversation,
  onOpenSettings,
  onClose,
}: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isMobile && open && (
        <div
          className="fixed inset-0 z-[15] bg-black/55"
          onClick={onClose}
        />
      )}

      <aside
        className="z-20 flex flex-shrink-0 flex-col overflow-hidden border-r transition-transform duration-[var(--dur)]"
        style={{
          width: "var(--sidebar-w)",
          background: "var(--surface)",
          borderColor: "var(--border)",
          transitionTimingFunction: "var(--ease)",
          ...(isMobile
            ? {
                position: "fixed",
                top: 0,
                left: 0,
                height: "100vh",
                zIndex: 50,
                transform: open ? "translateX(0)" : "translateX(-100%)",
              }
            : {}),
        }}
      >
        {/* Header */}
        <div
          className="flex h-[var(--header-h)] flex-shrink-0 items-center justify-between border-b px-4"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-2 text-base font-bold">
            <div
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg text-[13px] font-extrabold text-white"
              style={{
                background:
                  "linear-gradient(135deg, var(--accent), var(--accent-hover))",
              }}
            >
              B
            </div>
            <span>Barongsai</span>
          </div>
        </div>

        {/* New chat */}
        <button
          className="mx-3 mt-3 flex flex-shrink-0 items-center gap-2 rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors hover:bg-[rgba(99,102,241,0.2)]"
          style={{
            background: "var(--accent-dim)",
            color: "var(--accent)",
            borderColor: "rgba(99, 102, 241, 0.2)",
          }}
          onClick={onNewChat}
        >
          <span className="text-lg leading-none">+</span> New chat
        </button>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 py-1">
          {conversations.length === 0 ? (
            <p
              className="px-2.5 py-2 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              No conversations yet
            </p>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className="group flex cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-2 text-[13px] transition-colors hover:bg-[var(--surface-2)]"
                style={{
                  color:
                    conv.id === currentConvId
                      ? "var(--text)"
                      : "var(--text-secondary)",
                  background:
                    conv.id === currentConvId ? "var(--accent-dim)" : undefined,
                }}
                onClick={() => onLoadConversation(conv.id)}
              >
                <span className="flex-shrink-0 text-[13px] opacity-50">
                  &#128172;
                </span>
                <span className="flex-1 truncate">
                  {conv.title || "Untitled"}
                </span>
                <button
                  className="rounded px-1 py-0.5 text-xs opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                  style={{ color: "var(--text-muted)" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  title="Delete"
                >
                  &#10005;
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div
          className="flex-shrink-0 border-t p-3"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            className="flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-[13px] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
            }}
            onClick={onOpenSettings}
          >
            <span>&#9881;</span>
            <span>Settings</span>
          </button>
        </div>
      </aside>
    </>
  );
}
