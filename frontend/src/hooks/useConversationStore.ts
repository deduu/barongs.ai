import { useCallback, useMemo, useRef, useState } from "react";
import type { Message } from "../types";
import type { OutlineData, DisambiguationData } from "./useStreamSearch";

export interface StreamMeta {
  isStreaming: boolean;
  statusMessage: string;
  streamStartedAt: number | null;
  lastEventAt: number | null;
  eventCount: number;
  outlineData: OutlineData | null;
  disambiguationData: DisambiguationData | null;
  abortController: AbortController | null;
}

const EMPTY_MESSAGES: Message[] = [];

const DEFAULT_STREAM_META: StreamMeta = {
  isStreaming: false,
  statusMessage: "",
  streamStartedAt: null,
  lastEventAt: null,
  eventCount: 0,
  outlineData: null,
  disambiguationData: null,
  abortController: null,
};

export function useConversationStore() {
  // Using refs for the actual data to avoid re-renders on every stream event
  // for non-active conversations. A version counter triggers re-renders.
  const [, setVersion] = useState(0);
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  const messagesRef = useRef<Record<string, Message[]>>({});
  const streamMetaRef = useRef<Record<string, StreamMeta>>({});

  const getMessages = useCallback(
    (convId: string | null): Message[] => {
      if (!convId) return EMPTY_MESSAGES;
      return messagesRef.current[convId] ?? EMPTY_MESSAGES;
    },
    [],
  );

  const hasMessages = useCallback(
    (convId: string): boolean => convId in messagesRef.current,
    [],
  );

  const updateMessages = useCallback(
    (
      convId: string,
      updater: Message[] | ((prev: Message[]) => Message[]),
    ) => {
      const prev = messagesRef.current[convId] ?? [];
      const next = typeof updater === "function" ? updater(prev) : updater;
      messagesRef.current[convId] = next;
      bump();
    },
    [bump],
  );

  const removeMessages = useCallback(
    (convId: string) => {
      delete messagesRef.current[convId];
      bump();
    },
    [bump],
  );

  const getStreamMeta = useCallback(
    (convId: string | null): StreamMeta | null => {
      if (!convId) return null;
      return streamMetaRef.current[convId] ?? null;
    },
    [],
  );

  const setStreamMeta = useCallback(
    (convId: string, partial: Partial<StreamMeta>) => {
      const prev = streamMetaRef.current[convId] ?? { ...DEFAULT_STREAM_META };
      streamMetaRef.current[convId] = { ...prev, ...partial };
      bump();
    },
    [bump],
  );

  const clearStreamMeta = useCallback(
    (convId: string) => {
      delete streamMetaRef.current[convId];
      bump();
    },
    [bump],
  );

  const getStreamingConvIds = useCallback((): string[] => {
    return Object.entries(streamMetaRef.current)
      .filter(([, meta]) => meta.isStreaming)
      .map(([id]) => id);
  }, []);

  return useMemo(
    () => ({
      getMessages,
      hasMessages,
      updateMessages,
      removeMessages,
      getStreamMeta,
      setStreamMeta,
      clearStreamMeta,
      getStreamingConvIds,
    }),
    [
      getMessages,
      hasMessages,
      updateMessages,
      removeMessages,
      getStreamMeta,
      setStreamMeta,
      clearStreamMeta,
      getStreamingConvIds,
    ],
  );
}

export type ConversationStore = ReturnType<typeof useConversationStore>;
