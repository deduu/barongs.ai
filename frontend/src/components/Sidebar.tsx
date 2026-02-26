import { useMemo, useState } from "react";
import type { Conversation } from "../types";
import { groupConversations } from "../lib/dates";
import {
  PlusIcon,
  SearchIcon,
  SettingsIcon,
  PinIcon,
  TrashIcon,
  MessageIcon,
  SidebarIcon,
  XIcon,
  SparklesIcon,
  BarongsaiLogo,
  GlobeIcon,
  LayersIcon,
} from "./icons";

export type ActivePage = "chat" | "knowledge-base";

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  isMobile: boolean;
  conversations: Conversation[];
  currentConvId: string | null;
  activePage: ActivePage;
  onNewChat: () => void;
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onTogglePin: (id: string) => void;
  onOpenSettings: () => void;
  onClose: () => void;
  onToggleCollapse: () => void;
  onNavigate: (page: ActivePage) => void;
}

/* Simple nav link */
function NavLink({
  icon: Icon,
  label,
  badge,
  collapsed,
  active,
  onClick,
}: {
  icon: React.ComponentType<{ size: number; className?: string }>;
  label: string;
  badge?: string;
  collapsed: boolean;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition-colors hover:bg-[var(--surface-2)]"
      style={{
        color: active ? "var(--text)" : "var(--text-secondary)",
        background: active ? "var(--accent-dim)" : undefined,
      }}
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === "Enter" && onClick) onClick(); }}
    >
      <Icon size={16} className="flex-shrink-0" />
      {!collapsed && (
        <>
          <span className="flex-1">{label}</span>
          {badge && (
            <span
              className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
              style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
            >
              {badge}
            </span>
          )}
        </>
      )}
    </div>
  );
}

export default function Sidebar({
  open,
  collapsed,
  isMobile,
  conversations,
  currentConvId,
  activePage,
  onNewChat,
  onLoadConversation,
  onDeleteConversation,
  onTogglePin,
  onOpenSettings,
  onClose,
  onToggleCollapse,
  onNavigate,
}: SidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter(
      (c) => c.title.toLowerCase().includes(q),
    );
  }, [conversations, search]);

  const groups = useMemo(() => groupConversations(filtered), [filtered]);

  const sidebarWidth = collapsed && !isMobile ? "var(--sidebar-rail)" : "var(--sidebar-w)";
  const isExpanded = !collapsed || isMobile;

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && open && (
        <div
          className="fixed inset-0 z-[15] bg-black/40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className="z-20 flex flex-shrink-0 flex-col overflow-hidden border-r transition-all"
        style={{
          width: sidebarWidth,
          background: "var(--surface)",
          borderColor: "var(--border)",
          transitionDuration: "var(--dur)",
          transitionTimingFunction: "var(--ease)",
          ...(isMobile
            ? {
                position: "fixed",
                top: 0,
                left: 0,
                height: "100vh",
                width: "var(--sidebar-w)",
                zIndex: 50,
                transform: open ? "translateX(0)" : "translateX(-100%)",
              }
            : {}),
        }}
        role="navigation"
        aria-label="Sidebar"
      >
        {/* Header */}
        <div
          className="flex h-[var(--header-h)] flex-shrink-0 items-center justify-between border-b px-3"
          style={{ borderColor: "var(--border)" }}
        >
          {isExpanded ? (
            <div className="flex items-center gap-2.5 text-base font-bold">
              <BarongsaiLogo size={28} className="flex-shrink-0" />
              <span style={{ color: "var(--text)" }}>Barongsai</span>
            </div>
          ) : (
            <BarongsaiLogo size={28} className="mx-auto" />
          )}

          {!isMobile && (
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text-secondary)" }}
              onClick={onToggleCollapse}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <SidebarIcon size={16} />
            </button>
          )}

          {isMobile && (
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text-secondary)" }}
              onClick={onClose}
              aria-label="Close sidebar"
            >
              <XIcon size={16} />
            </button>
          )}
        </div>

        {/* New chat button — outlined style */}
        <div className="px-2.5 pt-3">
          <button
            className="flex w-full items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-all hover:bg-[var(--surface-2)] active:scale-[0.98]"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
            onClick={onNewChat}
            title="New chat (Ctrl+K)"
            aria-label="New chat"
          >
            <PlusIcon size={16} />
            {isExpanded && <span>New chat</span>}
          </button>
        </div>

        {/* Nav links (placeholder) */}
        {isExpanded && (
          <div className="px-2.5 pt-3">
            <NavLink icon={SparklesIcon} label="Agents" badge="3" collapsed={false} />
            <NavLink
              icon={GlobeIcon}
              label="Search"
              collapsed={false}
              active={activePage === "chat"}
              onClick={() => onNavigate("chat")}
            />
            <NavLink
              icon={LayersIcon}
              label="Library"
              collapsed={false}
              active={activePage === "knowledge-base"}
              onClick={() => onNavigate("knowledge-base")}
            />
          </div>
        )}

        {/* Projects section header */}
        {isExpanded && (
          <div className="flex items-center justify-between px-4 pt-4 pb-1">
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              Projects
            </span>
            <button
              className="text-[11px] font-medium transition-colors hover:text-[var(--text)]"
              style={{ color: "var(--text-muted)" }}
            >
              + New
            </button>
          </div>
        )}

        {/* Search (expanded only) */}
        {isExpanded && (
          <div className="px-2.5 pt-2">
            <div
              className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5 transition-colors focus-within:border-[var(--accent)]"
              style={{
                background: "var(--surface-2)",
                borderColor: "var(--border)",
              }}
            >
              <SearchIcon size={14} className="flex-shrink-0 opacity-40" />
              <input
                type="text"
                className="flex-1 border-none bg-transparent text-xs outline-none placeholder:text-[var(--text-muted)]"
                style={{ color: "var(--text)" }}
                placeholder="Search conversations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search conversations"
              />
            </div>
          </div>
        )}

        {/* "All tasks" section header */}
        {isExpanded && (
          <div className="px-4 pt-3 pb-1">
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              All tasks
            </span>
          </div>
        )}

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 py-1">
          {groups.length === 0 ? (
            <p
              className="px-2.5 py-3 text-center text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              {search ? "No matches" : "No conversations yet"}
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-2">
                {isExpanded && (
                  <div
                    className="px-2.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {group.label}
                  </div>
                )}
                {group.conversations.map((conv) => {
                  const isActive = conv.id === currentConvId;
                  return (
                    <div
                      key={conv.id}
                      className="group relative flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] transition-all"
                      style={{
                        color: isActive ? "var(--text)" : "var(--text-secondary)",
                        background: isActive ? "var(--accent-dim)" : undefined,
                      }}
                      onClick={() => onLoadConversation(conv.id)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter") onLoadConversation(conv.id); }}
                      aria-current={isActive ? "true" : undefined}
                    >
                      <MessageIcon
                        size={14}
                        className="flex-shrink-0 opacity-40"
                      />
                      {isExpanded && (
                        <>
                          <span className="flex-1 truncate">
                            {conv.title || "Untitled"}
                          </span>
                          <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                            <button
                              className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:bg-[var(--surface-2)]"
                              style={{ color: conv.pinned ? "var(--accent)" : "var(--text-muted)" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                onTogglePin(conv.id);
                              }}
                              title={conv.pinned ? "Unpin" : "Pin"}
                              aria-label={conv.pinned ? "Unpin conversation" : "Pin conversation"}
                            >
                              <PinIcon size={12} />
                            </button>
                            <button
                              className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:text-red-500"
                              style={{ color: "var(--text-muted)" }}
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeleteConversation(conv.id);
                              }}
                              title="Delete"
                              aria-label="Delete conversation"
                            >
                              <TrashIcon size={12} />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div
          className="flex flex-shrink-0 items-center justify-between border-t px-3 py-2.5"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-secondary)" }}
            onClick={onOpenSettings}
            title="Settings (Ctrl+,)"
            aria-label="Settings"
          >
            <SettingsIcon size={16} />
            {isExpanded && <span>Settings</span>}
          </button>
          {isExpanded && (
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-medium"
              style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
            >
              v1.0
            </span>
          )}
        </div>
      </aside>
    </>
  );
}
