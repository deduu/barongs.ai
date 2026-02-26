import { useCallback, useEffect, useState } from "react";
import type { ChatMode, Source } from "./types";
import { getString, setItem } from "./lib/storage";
import { useTheme } from "./hooks/useTheme";
import { useConversations } from "./hooks/useConversations";
import { useModels } from "./hooks/useModels";
import { useStreamSearch } from "./hooks/useStreamSearch";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useRAG } from "./hooks/useRAG";
import Sidebar, { type ActivePage } from "./components/Sidebar";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import SourcePanel from "./components/SourcePanel";
import SettingsModal from "./components/SettingsModal";
import WelcomeScreen from "./components/WelcomeScreen";
import KnowledgeBase from "./components/KnowledgeBase";
import {
  MenuIcon,
  MoonIcon,
  SunIcon,
  MonitorIcon,
  SettingsIcon,
  BellIcon,
} from "./components/icons";

export default function App() {
  /* ── Theme ─────────────────────────────────────────────────── */
  const { theme, setTheme, cycleTheme } = useTheme();

  /* ── API key ───────────────────────────────────────────────── */
  const [apiKey, setApiKeyState] = useState(() =>
    getString("api_key", "changeme"),
  );
  const saveApiKey = useCallback((key: string) => {
    setApiKeyState(key);
    setItem("api_key", key);
  }, []);

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
  } = useConversations();

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
    useModels(apiKey);

  /* ── Chat mode (search / rag) ──────────────────────────────── */
  const [chatMode, setChatMode] = useState<ChatMode>("search");

  /* ── Streaming ─────────────────────────────────────────────── */
  const { isStreaming, statusMessage, send } = useStreamSearch({
    apiKey,
    currentConvId,
    chatMode,
    setMessages,
    onComplete: saveCurrentConversation,
  });

  /* ── RAG document management ────────────────────────────────── */
  const rag = useRAG({ apiKey });

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
      newChat();
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
        onNewChat={() => {
          newChat();
          setActivePage("chat");
          if (isMobile) setSidebarOpen(false);
        }}
        onLoadConversation={(id) => {
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
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-[var(--surface-2)]"
              style={{ color: "var(--text-secondary)" }}
              title="Notifications"
              aria-label="Notifications"
            >
              <BellIcon size={16} />
            </button>
            <span
              className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
              style={{ background: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
            >
              300
            </span>
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
            <div
              className="flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold"
              style={{ background: "var(--surface-3)", color: "var(--text-secondary)" }}
            >
              U
            </div>
          </div>
        </header>

        {activePage === "knowledge-base" ? (
          <KnowledgeBase
            documents={rag.documents}
            isLoading={rag.isLoading}
            isIngesting={rag.isIngesting}
            error={rag.error}
            onUploadFile={rag.uploadFile}
            onUploadText={rag.uploadText}
            onDelete={rag.removeDocument}
            onRefresh={rag.refresh}
          />
        ) : showWelcome ? (
          <WelcomeScreen onSend={handleQuickSend} chatMode={chatMode} onChatModeChange={setChatMode} />
        ) : (
          <>
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              statusMessage={statusMessage}
              selectedModel={selectedModel}
              onSourceClick={openSource}
            />
            <ChatInput
              disabled={isStreaming}
              chatMode={chatMode}
              onChatModeChange={setChatMode}
              onSend={send}
            />
          </>
        )}
      </main>

      <SourcePanel
        open={sourcePanelOpen}
        source={selectedSource}
        onClose={closeSourcePanel}
      />

      <SettingsModal
        open={settingsOpen}
        apiKey={apiKey}
        theme={theme}
        onSetTheme={setTheme}
        onSaveApiKey={handleSaveApiKey}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}
