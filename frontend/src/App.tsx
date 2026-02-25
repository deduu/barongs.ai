import { useCallback, useEffect, useState } from "react";
import type { Source } from "./types";
import { getString, setItem } from "./lib/storage";
import { useTheme } from "./hooks/useTheme";
import { useConversations } from "./hooks/useConversations";
import { useModels } from "./hooks/useModels";
import { useStreamSearch } from "./hooks/useStreamSearch";
import Sidebar from "./components/Sidebar";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import SourcePanel from "./components/SourcePanel";
import SettingsModal from "./components/SettingsModal";

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

  /* ── Streaming ─────────────────────────────────────────────── */
  const { isStreaming, statusMessage, send } = useStreamSearch({
    apiKey,
    currentConvId,
    setMessages,
    onComplete: saveCurrentConversation,
  });

  /* ── Mobile detection ──────────────────────────────────────── */
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth >= 768);

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

  /* ── Settings modal ────────────────────────────────────────── */
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleSaveApiKey = useCallback(
    (key: string) => {
      saveApiKey(key);
      refreshModels();
    },
    [saveApiKey, refreshModels],
  );

  /* ── Quick send (welcome chips) ────────────────────────────── */
  const handleQuickSend = useCallback(
    (text: string) => {
      send(text);
    },
    [send],
  );

  /* ── Render ────────────────────────────────────────────────── */
  return (
    <div className="app-glow relative flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        isMobile={isMobile}
        conversations={conversations}
        currentConvId={currentConvId}
        onNewChat={() => {
          newChat();
          if (isMobile) setSidebarOpen(false);
        }}
        onLoadConversation={(id) => {
          loadConversation(id);
          if (isMobile) setSidebarOpen(false);
        }}
        onDeleteConversation={deleteConversation}
        onOpenSettings={() => setSettingsOpen(true)}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main area */}
      <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header
          className="flex h-[var(--header-h)] flex-shrink-0 items-center justify-between border-b px-5"
          style={{ borderColor: "var(--border)", zIndex: 5 }}
        >
          <div className="flex items-center gap-2.5">
            {/* Hamburger (mobile) */}
            <button
              className="items-center rounded-lg border-none p-1.5 text-lg md:hidden"
              style={{ color: "var(--text-secondary)", display: isMobile ? "flex" : "none" }}
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title="Toggle sidebar"
            >
              &#9776;
            </button>

            {/* Model select */}
            {models.length > 0 ? (
              <select
                className="rounded-lg border px-2.5 py-1.5 text-[13px] outline-none transition-colors hover:border-[var(--accent)] focus:border-[var(--accent)]"
                style={{
                  background: "var(--surface-2)",
                  borderColor: "var(--border)",
                  color: "var(--text)",
                }}
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <span
                className="text-[13px]"
                style={{ color: "var(--text-muted)" }}
              >
                Barongsai
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              className="flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-sm transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
              }}
              onClick={cycleTheme}
              title={`Theme: ${theme}`}
            >
              <span>
                {theme === "dark"
                  ? "\uD83C\uDF19"
                  : theme === "light"
                    ? "\u2600\uFE0F"
                    : "\uD83D\uDDA5\uFE0F"}
              </span>
              <span className="text-xs">
                {theme.charAt(0).toUpperCase() + theme.slice(1)}
              </span>
            </button>
            <button
              className="flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-sm transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              style={{
                borderColor: "var(--border)",
                color: "var(--text-secondary)",
              }}
              onClick={() => setSettingsOpen(true)}
              title="Settings"
            >
              &#9881;
            </button>
          </div>
        </header>

        {/* Messages */}
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          statusMessage={statusMessage}
          onSourceClick={openSource}
          onQuickSend={handleQuickSend}
        />

        {/* Input */}
        <ChatInput disabled={isStreaming} onSend={send} />
      </main>

      {/* Source panel */}
      <SourcePanel
        open={sourcePanelOpen}
        source={selectedSource}
        onClose={closeSourcePanel}
      />

      {/* Settings modal */}
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
