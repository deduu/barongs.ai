import { useCallback, useRef, useState } from "react";
import type { ChatMode, Message, Source } from "../types";
import type { SearchSettings } from "../lib/searchSettings";
import {
  streamSearch,
  confirmOutline,
  type OutlineSection,
  type RAGSourceData,
  type ResearchTask,
  type StreamEvent,
} from "../lib/api";
import { escapeUserHtml, renderFinal, renderStreaming } from "../lib/markdown";

export interface OutlineData {
  sessionId: string;
  query: string;
  researchMode: string;
  sections: OutlineSection[];
  researchTasks: ResearchTask[];
}

interface UseStreamSearchOptions {
  apiKey: string;
  currentConvId: string | null;
  chatMode: ChatMode;
  searchSettings: SearchSettings;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  onComplete: () => void;
}

/** Convert a RAG source event into the frontend Source shape. */
function ragSourceToSource(data: StreamEvent["data"]): Source {
  const title =
    (data.metadata?.title as string) ?? data.id ?? "Knowledge Base";
  return {
    url: `rag://${data.id ?? "doc"}`,
    title,
    snippet: data.content?.slice(0, 200) ?? "",
    content: data.content,
  };
}

export function useStreamSearch({
  apiKey,
  currentConvId,
  chatMode,
  searchSettings,
  setMessages,
  onComplete,
}: UseStreamSearchOptions) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [outlineData, setOutlineData] = useState<OutlineData | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    (query: string) => {
      if (!query.trim() || isStreaming) return;

      const userMsg: Message = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: query,
        renderedHtml: escapeUserHtml(query),
        sources: [],
        status: "done",
        timestamp: Date.now(),
      };
      const assistantId = `msg-${Date.now() + 1}`;
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        renderedHtml: "",
        sources: [],
        status: "streaming",
        timestamp: Date.now() + 1,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setStatusMessage(
        chatMode === "rag"
          ? "Searching knowledge base\u2026"
          : chatMode === "deep_search"
            ? "Planning research\u2026"
            : "Searching\u2026",
      );

      // Accumulate sources in a local ref to avoid stale closures
      const sourcesAccum: Source[] = [];

      const updateAssistant = (
        updater: (msg: Message) => Partial<Message>,
      ) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, ...updater(m) } : m)),
        );
      };

      const handleEvent = (event: StreamEvent) => {
        switch (event.type) {
          case "status":
            setStatusMessage(event.data.message ?? "");
            break;
          case "source": {
            const src =
              chatMode === "rag"
                ? ragSourceToSource(event.data)
                : (event.data as Source);
            sourcesAccum.push(src);
            updateAssistant(() => ({ sources: [...sourcesAccum] }));
            break;
          }
          case "planning":
          case "researching":
          case "reflecting":
          case "synthesizing":
            setStatusMessage(event.data.status ?? event.data.message ?? "Processing\u2026");
            break;
          case "finding": {
            const f = (event.data.finding ?? event.data) as Record<string, unknown>;
            const src: Source = {
              url: (f.source_url as string) ?? "",
              title: (f.finding_id as string) ?? "Research Finding",
              snippet: ((f.content as string) ?? "").slice(0, 200),
            };
            sourcesAccum.push(src);
            updateAssistant(() => ({ sources: [...sourcesAccum] }));
            break;
          }
          case "outline_ready":
            setOutlineData({
              sessionId: event.data.session_id ?? "",
              query: event.data.query ?? "",
              researchMode: event.data.research_mode ?? "general",
              sections: event.data.sections ?? [],
              researchTasks: event.data.research_tasks ?? [],
            });
            setStatusMessage("Waiting for outline confirmation\u2026");
            break;
          case "awaiting_confirmation":
            break;
          case "outline_confirmed":
            setOutlineData(null);
            setStatusMessage("Outline confirmed, starting research\u2026");
            break;
          case "budget_update":
          case "knowledge_graph":
            break;
          case "chunk":
            updateAssistant((m) => {
              const content = m.content + (event.data.text ?? event.data.token ?? "");
              return {
                content,
                renderedHtml: renderStreaming(content),
              };
            });
            break;
          case "done": {
            const doneSources =
              chatMode === "rag"
                ? (event.data.rag_sources as RAGSourceData[] | undefined)?.map(
                    (rs) =>
                      ragSourceToSource({
                        id: rs.id,
                        content: rs.content,
                        score: rs.score,
                        source: rs.source,
                        metadata: rs.metadata,
                      }),
                  )
                : event.data.sources;
            updateAssistant((m) => {
              const content = event.data.response ?? m.content;
              const sources =
                doneSources && doneSources.length > 0 ? doneSources : m.sources;
              return {
                content,
                sources,
                renderedHtml: renderFinal(content),
                status: "done",
              };
            });
            break;
          }
          case "error":
            updateAssistant(() => ({
              content: event.data.message ?? "An error occurred",
              renderedHtml: `<span style="color:#ef4444;">${event.data.message ?? "An error occurred"}</span>`,
              status: "error",
            }));
            break;
        }
      };

      const handleDone = () => {
        // Ensure status is "done" if still streaming
        updateAssistant((m) => {
          if (m.status === "streaming") {
            return {
              status: "done",
              renderedHtml: renderFinal(m.content),
            };
          }
          return {};
        });
        setIsStreaming(false);
        setStatusMessage("");
        abortRef.current = null;
        onComplete();
      };

      const handleError = (err: string) => {
        updateAssistant(() => ({
          content: err,
          renderedHtml: `<span style="color:#ef4444;">${err}</span>`,
          status: "error",
        }));
      };

      const modeSettings = searchSettings[chatMode] as unknown as Record<string, unknown>;
      abortRef.current = streamSearch(
        query,
        currentConvId ?? "default",
        apiKey,
        handleEvent,
        handleDone,
        handleError,
        chatMode,
        modeSettings,
      );
    },
    [isStreaming, apiKey, currentConvId, chatMode, searchSettings, setMessages, onComplete],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const submitOutline = useCallback(
    async (
      sections?: OutlineSection[],
      researchTasks?: ResearchTask[],
    ) => {
      if (!outlineData) return;
      try {
        await confirmOutline(
          outlineData.sessionId,
          apiKey,
          true,
          sections,
          researchTasks,
        );
      } catch (e) {
        console.error("Failed to confirm outline:", e);
      }
    },
    [outlineData, apiKey],
  );

  return { isStreaming, statusMessage, outlineData, send, abort, submitOutline } as const;
}
