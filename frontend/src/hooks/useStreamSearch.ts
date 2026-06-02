import { useCallback } from "react";
import type { ChatMode, Message, Source } from "../types";
import type { SearchSettings } from "../lib/searchSettings";
import type { ConversationStore } from "./useConversationStore";
import {
  streamSearch,
  confirmOutline,
  confirmDisambiguation,
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

export interface DisambiguationData {
  sessionId: string;
  entityName: string;
  message: string;
}

interface UseStreamSearchOptions {
  apiKey: string;
  currentConvId: string | null;
  chatMode: ChatMode;
  searchSettings: SearchSettings;
  store: ConversationStore;
  onComplete: (convId: string) => void;
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
  store,
  onComplete,
}: UseStreamSearchOptions) {
  const currentMeta = store.getStreamMeta(currentConvId);
  const isStreaming = currentMeta?.isStreaming ?? false;
  const statusMessage = currentMeta?.statusMessage ?? "";
  const streamStartedAt = currentMeta?.streamStartedAt ?? null;
  const lastEventAt = currentMeta?.lastEventAt ?? null;
  const eventCount = currentMeta?.eventCount ?? 0;
  const outlineData = currentMeta?.outlineData ?? null;
  const disambiguationData = currentMeta?.disambiguationData ?? null;

  const send = useCallback(
    (query: string): boolean => {
      const trimmedQuery = query.trim();
      const convId = currentConvId;
      console.debug("[send]", {
        convId,
        query: trimmedQuery.slice(0, 30),
        meta: store.getStreamMeta(convId),
      });
      if (!convId || !trimmedQuery) return false;

      // Check if THIS conversation is already streaming
      if (store.getStreamMeta(convId)?.isStreaming) return false;

      const userMsg: Message = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: trimmedQuery,
        renderedHtml: escapeUserHtml(trimmedQuery),
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

      store.updateMessages(convId, (prev) => [...prev, userMsg, assistantMsg]);
      const startedAt = Date.now();
      store.setStreamMeta(convId, {
        isStreaming: true,
        statusMessage:
          chatMode === "rag"
            ? "Searching knowledge base\u2026"
            : chatMode === "deep_search"
              ? "Planning research\u2026"
              : "Searching\u2026",
        streamStartedAt: startedAt,
        lastEventAt: startedAt,
        eventCount: 0,
        outlineData: null,
        disambiguationData: null,
        abortController: null,
      });

      // Accumulate sources in a local ref to avoid stale closures
      const sourcesAccum: Source[] = [];
      const streamSessionId = chatMode === "deep_search" ? assistantId : (convId ?? "default");

      const updateAssistant = (
        updater: (msg: Message) => Partial<Message>,
      ) => {
        store.updateMessages(convId, (prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, ...updater(m) } : m)),
        );
      };

      const handleEvent = (event: StreamEvent) => {
        const prevMeta = store.getStreamMeta(convId);
        store.setStreamMeta(convId, {
          lastEventAt: Date.now(),
          eventCount: (prevMeta?.eventCount ?? 0) + 1,
        });
        if (chatMode === "deep_search" && event.type !== "chunk") {
          console.info("[deep-search:event]", event.type, event.data);
        }
        switch (event.type) {
          case "status":
            store.setStreamMeta(convId, {
              statusMessage: event.data.status ?? event.data.message ?? "",
            });
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
            store.setStreamMeta(convId, {
              statusMessage: event.data.status ?? event.data.message ?? "Processing\u2026",
            });
            break;
          case "disambiguation_required":
            store.setStreamMeta(convId, {
              disambiguationData: {
                sessionId: event.data.session_id ?? "",
                entityName: event.data.entity_name ?? "",
                message: event.data.message ?? "Clarify which entity you mean before research continues.",
              },
              statusMessage: "Waiting for clarification\u2026",
            });
            break;
          case "disambiguation_confirmed":
            store.setStreamMeta(convId, {
              disambiguationData: null,
              statusMessage: event.data.message ?? "Clarification received\u2026",
            });
            break;
          case "finding": {
            const f = (event.data.finding ?? event.data) as Record<string, unknown>;
            const citations = Array.isArray(f.citations) ? f.citations : [];
            const src: Source = {
              url: (f.source_url as string) ?? "",
              title: (citations[0] as string) ?? (f.finding_id as string) ?? "Research Finding",
              snippet: ((f.content as string) ?? "").slice(0, 200),
            };
            sourcesAccum.push(src);
            updateAssistant(() => ({ sources: [...sourcesAccum] }));
            break;
          }
          case "outline_ready":
            store.setStreamMeta(convId, {
              outlineData: {
                sessionId: event.data.session_id ?? "",
                query: event.data.query ?? "",
                researchMode: event.data.research_mode ?? "general",
                sections: event.data.sections ?? [],
                researchTasks: event.data.research_tasks ?? [],
              },
              statusMessage: "Waiting for outline confirmation\u2026",
            });
            break;
          case "awaiting_confirmation":
            break;
          case "outline_confirmed":
            store.setStreamMeta(convId, {
              outlineData: null,
              statusMessage: "Outline confirmed, starting research\u2026",
            });
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
            console.error("[stream:error]", event.data);
            updateAssistant(() => ({
              content: event.data.error ?? event.data.message ?? "An error occurred",
              renderedHtml: `<span style="color:#ef4444;">${event.data.error ?? event.data.message ?? "An error occurred"}</span>`,
              status: "error",
            }));
            break;
        }
      };

      const handleDone = () => {
        if (chatMode === "deep_search") {
          console.info("[deep-search:event]", "done");
        }
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
        store.clearStreamMeta(convId);
        onComplete(convId);
      };

      const handleError = (err: string) => {
        console.error("[stream:error]", err);
        updateAssistant(() => ({
          content: err,
          renderedHtml: `<span style="color:#ef4444;">${err}</span>`,
          status: "error",
        }));
      };

      const modeSettings = searchSettings[chatMode] as unknown as Record<string, unknown>;
      const controller = streamSearch(
        trimmedQuery,
        streamSessionId,
        apiKey,
        handleEvent,
        handleDone,
        handleError,
        chatMode,
        modeSettings,
      );
      store.setStreamMeta(convId, { abortController: controller });
      return true;
    },
    [currentConvId, apiKey, chatMode, searchSettings, store, onComplete],
  );

  const abort = useCallback(() => {
    if (!currentConvId) return;
    const meta = store.getStreamMeta(currentConvId);
    meta?.abortController?.abort();
    store.clearStreamMeta(currentConvId);
  }, [currentConvId, store]);

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

  const submitDisambiguation = useCallback(
    async (clarification: string) => {
      if (!disambiguationData) return;
      try {
        await confirmDisambiguation(
          disambiguationData.sessionId,
          apiKey,
          clarification,
        );
      } catch (e) {
        console.error("Failed to confirm disambiguation:", e);
      }
    },
    [disambiguationData, apiKey],
  );

  const regenerate = useCallback(() => {
    if (!currentConvId) return;
    if (store.getStreamMeta(currentConvId)?.isStreaming) return;
    let query = "";
    store.updateMessages(currentConvId, (prev) => {
      // Find last user message from the end
      for (let i = prev.length - 1; i >= 0; i--) {
        if (prev[i].role === "user") {
          query = prev[i].content;
          // Remove the user message and everything after it
          return prev.slice(0, i);
        }
      }
      return prev;
    });
    // send() will re-add the user message + a new assistant message
    if (query) setTimeout(() => send(query), 0);
  }, [currentConvId, store, send]);

  return {
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
  } as const;
}
