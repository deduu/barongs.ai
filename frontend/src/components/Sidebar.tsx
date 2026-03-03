import { useMemo, useState } from "react";
import type { Conversation, Project } from "../types";
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
  BarongsaiLogo,
  GlobeIcon,
  LayersIcon,
  FolderIcon,
  PenIcon,
} from "./icons";

export type ActivePage = "chat" | "knowledge-base";

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  isMobile: boolean;
  conversations: Conversation[];
  currentConvId: string | null;
  activePage: ActivePage;
  projects: Project[];
  activeProjectId: string | null;
  onNewChat: () => void;
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onTogglePin: (id: string) => void;
  onOpenSettings: () => void;
  onClose: () => void;
  onToggleCollapse: () => void;
  onNavigate: (page: ActivePage) => void;
  onSelectProject: (id: string | null) => void;
  onCreateProject: (name: string) => void;
  onRenameProject: (id: string, name: string) => void;
  onDeleteProject: (id: string) => void;
  onAssignProject: (conversationId: string, projectId: string | null) => void;
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

/* Project list item with inline rename */
function ProjectItem({
  project,
  active,
  count,
  onSelect,
  onRename,
  onDelete,
}: {
  project: Project;
  active: boolean;
  count: number;
  onSelect: () => void;
  onRename: (name: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(project.name);

  if (editing) {
    return (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (editName.trim()) onRename(editName.trim());
          setEditing(false);
        }}
        className="px-2.5 py-1"
      >
        <input
          autoFocus
          className="w-full rounded border bg-transparent px-2 py-1 text-xs outline-none focus:border-[var(--accent)]"
          style={{ borderColor: "var(--border)", color: "var(--text)" }}
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onBlur={() => setEditing(false)}
          onKeyDown={(e) => { if (e.key === "Escape") setEditing(false); }}
        />
      </form>
    );
  }

  return (
    <div
      className="group flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12px] transition-colors hover:bg-[var(--surface-2)]"
      style={{
        color: active ? "var(--text)" : "var(--text-secondary)",
        background: active ? "var(--accent-dim)" : undefined,
      }}
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === "Enter") onSelect(); }}
    >
      <FolderIcon size={13} className="flex-shrink-0 opacity-50" />
      <span className="flex-1 truncate">{project.name}</span>
      <span className="text-[10px] opacity-50">{count}</span>
      <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          className="flex h-5 w-5 items-center justify-center rounded transition-colors hover:bg-[var(--surface-2)]"
          style={{ color: "var(--text-muted)" }}
          onClick={(e) => { e.stopPropagation(); setEditing(true); setEditName(project.name); }}
          title="Rename"
        >
          <PenIcon size={10} />
        </button>
        <button
          className="flex h-5 w-5 items-center justify-center rounded transition-colors hover:text-red-500"
          style={{ color: "var(--text-muted)" }}
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          title="Delete project"
        >
          <TrashIcon size={10} />
        </button>
      </div>
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
  projects,
  activeProjectId,
  onNewChat,
  onLoadConversation,
  onDeleteConversation,
  onTogglePin,
  onOpenSettings,
  onClose,
  onToggleCollapse,
  onNavigate,
  onSelectProject,
  onCreateProject,
  onRenameProject,
  onDeleteProject,
  onAssignProject,
}: SidebarProps) {
  const [search, setSearch] = useState("");
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");

  const filtered = useMemo(() => {
    let result = conversations;
    if (activeProjectId) {
      result = result.filter((c) => c.projectId === activeProjectId);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((c) => c.title.toLowerCase().includes(q));
    }
    return result;
  }, [conversations, search, activeProjectId]);

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

        {/* Nav links */}
        {isExpanded && (
          <div className="px-2.5 pt-3">
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

        {/* Projects section */}
        {isExpanded && (
          <div className="px-2.5 pt-3">
            <div className="flex items-center justify-between px-1.5 pb-1">
              <span
                className="text-[10px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Projects
              </span>
              <button
                className="text-[11px] font-medium transition-colors hover:text-[var(--text)]"
                style={{ color: "var(--text-muted)" }}
                onClick={() => setIsCreatingProject(true)}
              >
                + New
              </button>
            </div>

            {isCreatingProject && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (newProjectName.trim()) {
                    onCreateProject(newProjectName.trim());
                    setNewProjectName("");
                    setIsCreatingProject(false);
                  }
                }}
                className="px-1.5 pb-1"
              >
                <input
                  autoFocus
                  className="w-full rounded border bg-transparent px-2 py-1 text-xs outline-none focus:border-[var(--accent)]"
                  style={{ borderColor: "var(--border)", color: "var(--text)" }}
                  placeholder="Project name..."
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onBlur={() => { setIsCreatingProject(false); setNewProjectName(""); }}
                  onKeyDown={(e) => { if (e.key === "Escape") { setIsCreatingProject(false); setNewProjectName(""); } }}
                />
              </form>
            )}

            {/* "All conversations" filter */}
            <div
              className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-[12px] transition-colors hover:bg-[var(--surface-2)]"
              style={{
                color: activeProjectId === null ? "var(--text)" : "var(--text-secondary)",
                background: activeProjectId === null ? "var(--accent-dim)" : undefined,
              }}
              role="button"
              tabIndex={0}
              onClick={() => onSelectProject(null)}
              onKeyDown={(e) => { if (e.key === "Enter") onSelectProject(null); }}
            >
              <MessageIcon size={13} className="flex-shrink-0 opacity-50" />
              <span className="flex-1">All conversations</span>
              <span className="text-[10px] opacity-50">{conversations.length}</span>
            </div>

            {/* Project items */}
            {projects.map((p) => (
              <ProjectItem
                key={p.id}
                project={p}
                active={p.id === activeProjectId}
                count={conversations.filter((c) => c.projectId === p.id).length}
                onSelect={() => onSelectProject(p.id)}
                onRename={(name) => onRenameProject(p.id, name)}
                onDelete={() => onDeleteProject(p.id)}
              />
            ))}
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

        {/* Conversations section header */}
        {isExpanded && (
          <div className="px-4 pt-3 pb-1">
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-muted)" }}
            >
              {activeProjectId
                ? projects.find((p) => p.id === activeProjectId)?.name ?? "Conversations"
                : "All conversations"}
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
                            {projects.length > 0 && (
                              <select
                                className="h-6 w-6 cursor-pointer appearance-none rounded bg-transparent text-center transition-colors hover:bg-[var(--surface-2)]"
                                style={{ color: "var(--text-muted)", fontSize: "10px" }}
                                value={conv.projectId ?? ""}
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => {
                                  e.stopPropagation();
                                  onAssignProject(conv.id, e.target.value || null);
                                }}
                                title="Move to project"
                                aria-label="Move to project"
                              >
                                <option value="">No project</option>
                                {projects.map((p) => (
                                  <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                              </select>
                            )}
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
