import { useCallback, useRef, useState } from "react";
import type { ChatMode, Message, Source } from "../types";
import type { SearchSettings } from "../lib/searchSettings";
import { streamSearch, type RAGSourceData, type StreamEvent } from "../lib/api";
import { escapeUserHtml, renderFinal, renderStreaming } from "../lib/markdown";

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

      const modeSettings = searchSettings[chatMode] as Record<string, unknown>;
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

  return { isStreaming, statusMessage, send, abort } as const;
}
