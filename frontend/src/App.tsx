import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import type { ChatMode, Source } from "./types";
import { getString, setItem } from "./lib/storage";
import { useTheme } from "./hooks/useTheme";
import { useAuth } from "./hooks/useAuth";
import { useConversations } from "./hooks/useConversations";
import { useProjects } from "./hooks/useProjects";
import { useModels } from "./hooks/useModels";
import { useStreamSearch } from "./hooks/useStreamSearch";
import { useSearchSettings } from "./hooks/useSearchSettings";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useRAG } from "./hooks/useRAG";
import Sidebar, { type ActivePage } from "./components/Sidebar";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import SourcePanel from "./components/SourcePanel";
import SettingsModal from "./components/SettingsModal";
import WelcomeScreen from "./components/WelcomeScreen";
import KnowledgeBase from "./components/KnowledgeBase";
import LoginPage from "./components/LoginPage";
import PageTransition from "./components/PageTransition";
import OutlineEditor from "./components/OutlineEditor";
import DisambiguationDialog from "./components/DisambiguationDialog";
import {
  MenuIcon,
  MoonIcon,
  SunIcon,
  MonitorIcon,
  SettingsIcon,
} from "./components/icons";

function formatDuration(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  if (mins <= 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export default function App() {
  /* ── Theme ─────────────────────────────────────────────────── */
  const { theme, setTheme, cycleTheme } = useTheme();

  /* ── Auth ────────────────────────────────────────────────────── */
  const auth = useAuth();

  /* ── API key (fallback for api_key mode) ─────────────────────── */
  const [apiKey, setApiKeyState] = useState(() =>
    getString("api_key", "changeme"),
  );
  const saveApiKey = useCallback((key: string) => {
    setApiKeyState(key);
    setItem("api_key", key);
  }, []);

  // The effective bearer token: JWT when in jwt mode, API key otherwise
  const bearerToken = auth.mode === "jwt" ? auth.token : apiKey;

  /* ── Conversations ─────────────────────────────────────────── */
  const {
    conversations,
    currentConvId,
    messages,
    setMessages,
    newChat,
    loadConversation,
    deleteConversation,
    togglePin,
    saveCurrentConversation,
    assignProject,
  } = useConversations(auth.user?.id ?? null);

  /* ── Projects ────────────────────────────────────────────── */
  const {
    projects,
    activeProjectId,
    setActiveProjectId,
    createProject,
    renameProject,
    deleteProject,
  } = useProjects();

  /* ── Auto-load first conversation or create new ────────────── */
  useEffect(() => {
    if (currentConvId) return;
    if (conversations.length) {
      loadConversation(conversations[0].id);
    } else {
      newChat();
    }
    // Only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Models ────────────────────────────────────────────────── */
  const { models, selectedModel, setSelectedModel, refreshModels } =
    useModels(bearerToken);

  /* ── Chat mode (search / rag) ──────────────────────────────── */
  const [chatMode, setChatMode] = useState<ChatMode>("search");

  /* ── Search settings ──────────────────────────────────────── */
  const { settings: searchSettings, updateModeSettings, applyPreset, resetMode, getActivePreset } = useSearchSettings();

  /* ── Streaming ─────────────────────────────────────────────── */
  const {
    isStreaming,
    statusMessage,
    streamStartedAt,
    lastEventAt,
    eventCount,
    outlineData,
    disambiguationData,
    send,
    abort,
    submitOutline,
    submitDisambiguation,
    regenerate,
  } = useStreamSearch({
    apiKey: bearerToken,
    currentConvId,
    chatMode,
    searchSettings,
    setMessages,
    onComplete: saveCurrentConversation,
  });
  const [streamNow, setStreamNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isStreaming) return;
    setStreamNow(Date.now());
    const id = window.setInterval(() => setStreamNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isStreaming]);

  const streamElapsedSeconds = streamStartedAt
    ? Math.max(0, Math.floor((streamNow - streamStartedAt) / 1000))
    : 0;
  const streamLastUpdateSeconds = lastEventAt
    ? Math.max(0, Math.floor((streamNow - lastEventAt) / 1000))
    : 0;
  const streamIsStale = isStreaming && streamLastUpdateSeconds >= 12;
  const conversationLockReason = "Finish or stop the current run before starting or switching chats.";

  /* ── RAG document management ────────────────────────────────── */
  const rag = useRAG({ apiKey: bearerToken });

  /* ── Page navigation ─────────────────────────────────────────── */
  const [activePage, setActivePage] = useState<ActivePage>("chat");

  /* ── Mobile detection ──────────────────────────────────────── */
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const handler = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (!mobile) setSidebarOpen(true);
    };
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  /* ── Source panel ──────────────────────────────────────────── */
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);

  const openSource = useCallback((source: Source) => {
    setSelectedSource(source);
    setSourcePanelOpen(true);
  }, []);

  const closeSourcePanel = useCallback(() => {
    setSourcePanelOpen(false);
    setTimeout(() => setSelectedSource(null), 280);
  }, []);

  /* ── Settings modal ──────────────────────────────────────── */
  const [settingsOpen, setSettingsOpen] = useState(false);

  /* ── Avatar dropdown ────────────────────────────────────── */
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false);
  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!avatarMenuOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) {
        setAvatarMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [avatarMenuOpen]);

  const handleSaveApiKey = useCallback(
    (key: string) => {
      saveApiKey(key);
      refreshModels();
    },
    [saveApiKey, refreshModels],
  );

  /* ── Keyboard shortcuts ──────────────────────────────────── */
  useKeyboardShortcuts({
    onNewChat: () => {
      if (isStreaming) return;
      newChat(activeProjectId);
      setActivePage("chat");
      if (isMobile) setSidebarOpen(false);
    },
    onOpenSettings: () => setSettingsOpen(true),
    onCloseModal: () => {
      if (settingsOpen) setSettingsOpen(false);
    },
  });

  /* ── Quick send (welcome chips) ──────────────────────────── */
  const handleQuickSend = useCallback(
    (text: string) => {
      send(text);
    },
    [send],
  );

  const handleNavigate = useCallback(
    (page: ActivePage) => {
      setActivePage(page);
      if (isMobile) setSidebarOpen(false);
    },
    [isMobile],
  );

  const showWelcome = messages.length === 0 && activePage === "chat";

  /* ── Loading state ──────────────────────────────────────────── */
  if (auth.mode === "loading") {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ background: "var(--bg)" }}
      >
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Loading...
        </span>
      </div>
    );
  }

  /* ── Login gate (JWT mode, not authenticated) ───────────────── */
  if (auth.mode === "jwt" && !auth.isAuthenticated) {
    return <LoginPage onLogin={auth.login} onRegister={auth.register} />;
  }

  /* ── Render ────────────────────────────────────────────────── */
  return (
    <div className="relative flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        isMobile={isMobile}
        conversations={conversations}
        currentConvId={currentConvId}
        activePage={activePage}
        projects={projects}
        activeProjectId={activeProjectId}
        isConversationLocked={isStreaming}
        conversationLockReason={conversationLockReason}
        onNewChat={() => {
          if (isStreaming) return;
          newChat(activeProjectId);
          setActivePage("chat");
          if (isMobile) setSidebarOpen(false);
        }}
        onLoadConversation={(id) => {
          if (isStreaming) return;
          loadConversation(id);
          setActivePage("chat");
          if (isMobile) setSidebarOpen(false);
        }}
        onDeleteConversation={deleteConversation}
        onTogglePin={togglePin}
        onOpenSettings={() => setSettingsOpen(true)}
        onClose={() => setSidebarOpen(false)}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNavigate={handleNavigate}
        onSelectProject={setActiveProjectId}
        onCreateProject={createProject}
        onRenameProject={renameProject}
        onDeleteProject={(id) => {
          conversations
            .filter((c) => c.projectId === id)
            .forEach((c) => assignProject(c.id, null));
          deleteProject(id);
        }}
        onAssignProject={assignProject}
      />

      {/* Main area */}
      <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header
          className="flex h-[var(--header-h)] flex-shrink-0 items-center justify-between border-b px-4"
          style={{ zIndex: 5, borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <div className="flex items-center gap-2.5">
            {isMobile && (
              <button
                className="flex items-center justify-center rounded-lg p-2 transition-colors hover:bg-[var(--surface-2)]"
                style={{ color: "var(--text-secondary)" }}
                onClick={() => setSidebarOpen(!sidebarOpen)}
                aria-label="Toggle sidebar"
              >
                <MenuIcon size={20} />
              </button>
            )}

            {models.length > 0 ? (
              <select
                className="rounded-lg border px-3 py-1.5 text-[13px] font-medium outline-none transition-colors hover:bg-[var(--surface-2)]"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  color: "var(--text)",
                }}
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                aria-label="Select model"
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                Barongsai
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {isStreaming && (
              <>
                <div
                  className="mr-1 inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium"
                  style={{
                    borderColor: streamIsStale ? "rgba(245, 158, 11, 0.55)" : "var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--text-secondary)",
                  }}
                  aria-live="polite"
                  aria-label={`Agent running. Elapsed ${formatDuration(streamElapsedSeconds)}. Last update ${formatDuration(streamLastUpdateSeconds)} ago.`}
                >
                  <span
                    className="h-2 w-2 rounded-full animate-pulse"
                    style={{ background: streamIsStale ? "#f59e0b" : "#22c55e" }}
                  />
                  <span className="hidden sm:inline">
                    {streamIsStale ? "No recent update" : "Agent running"}
                  </span>
                  <span>{formatDuration(streamElapsedSeconds)}</span>
                </div>
                <button
                  className="mr-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-[var(--surface-2)]"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--surface)",
                    color: "var(--text-secondary)",
                  }}
                  onClick={abort}
                  title="Stop the current run"
                  aria-label="Stop the current run"
                >
                  Stop
                </button>
              </>
            )}
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text-secondary)" }}
              onClick={cycleTheme}
              title={`Theme: ${theme}`}
              aria-label={`Switch theme, current: ${theme}`}
            >
              {theme === "dark" ? (
                <MoonIcon size={16} />
              ) : theme === "light" ? (
                <SunIcon size={16} />
              ) : (
                <MonitorIcon size={16} />
              )}
            </button>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text-secondary)" }}
              onClick={() => setSettingsOpen(true)}
              title="Settings (Ctrl+,)"
              aria-label="Open settings"
            >
              <SettingsIcon size={16} />
            </button>
            <div ref={avatarRef} className="relative">
              <button
                className="flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold transition-opacity hover:opacity-80"
                style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}
                onClick={() => setAvatarMenuOpen((v) => !v)}
                title="Account"
                aria-label="Account menu"
                aria-expanded={avatarMenuOpen}
              >
                {auth.user?.email?.[0]?.toUpperCase() ?? "U"}
              </button>
              {avatarMenuOpen && (
                <div
                  className="absolute right-0 top-9 z-50 min-w-[180px] rounded-xl py-1 shadow-lg"
                  style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}
                >
                  {auth.user?.email && (
                    <div
                      className="truncate px-3 py-2 text-[11px]"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {auth.user.email}
                    </div>
                  )}
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-[13px] transition-colors hover:bg-[var(--surface-3)]"
                    style={{ color: "var(--text)" }}
                    onClick={() => { setSettingsOpen(true); setAvatarMenuOpen(false); }}
                  >
                    <SettingsIcon size={13} />
                    Settings
                  </button>
                  {auth.mode === "jwt" && (
                    <button
                      className="flex w-full items-center gap-2 px-3 py-2 text-[13px] transition-colors hover:bg-[var(--surface-3)]"
                      style={{ color: "#ef4444" }}
                      onClick={() => { auth.logout(); setAvatarMenuOpen(false); }}
                    >
                      Logout
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </header>

        <AnimatePresence mode="wait">
          {activePage === "knowledge-base" ? (
            <PageTransition pageKey="knowledge-base">
              <KnowledgeBase
                documents={rag.documents}
                isLoading={rag.isLoading}
                isIngesting={rag.isIngesting}
                error={rag.error}
                apiKey={bearerToken}
                onUploadFile={rag.uploadFile}
                onUploadText={rag.uploadText}
                onDelete={rag.removeDocument}
                onRefresh={rag.refresh}
              />
            </PageTransition>
          ) : showWelcome ? (
            <PageTransition pageKey="welcome">
              <WelcomeScreen onSend={handleQuickSend} chatMode={chatMode} onChatModeChange={setChatMode} />
            </PageTransition>
          ) : (
            <PageTransition pageKey="chat">
              <MessageList
                messages={messages}
                isStreaming={isStreaming}
                statusMessage={statusMessage}
                streamStartedAt={streamStartedAt}
                lastEventAt={lastEventAt}
                eventCount={eventCount}
                selectedModel={selectedModel}
                chatMode={chatMode}
                onSourceClick={openSource}
                onRegenerate={regenerate}
              />
              <ChatInput
                disabled={isStreaming}
                chatMode={chatMode}
                onChatModeChange={setChatMode}
                onSend={send}
              />
            </PageTransition>
          )}
        </AnimatePresence>
      </main>

      <SourcePanel
        open={sourcePanelOpen}
        source={selectedSource}
        onClose={closeSourcePanel}
      />

      {disambiguationData && (
        <DisambiguationDialog
          data={disambiguationData}
          onConfirm={submitDisambiguation}
        />
      )}

      {outlineData && (
        <div className="fixed inset-0 z-[115] flex items-center justify-center bg-black/50 p-4">
          <div
            className="flex max-h-[calc(100vh-32px)] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border p-5 shadow-xl"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <OutlineEditor outline={outlineData} onConfirm={submitOutline} />
          </div>
        </div>
      )}

      <SettingsModal
        open={settingsOpen}
        apiKey={apiKey}
        theme={theme}
        authMode={auth.mode}
        userEmail={auth.user?.email ?? null}
        chatMode={chatMode}
        searchSettings={searchSettings}
        onUpdateSettings={updateModeSettings}
        onApplyPreset={applyPreset}
        onResetSettings={resetMode}
        getActivePreset={getActivePreset}
        onSetTheme={setTheme}
        onSaveApiKey={handleSaveApiKey}
        onLogout={auth.logout}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}
