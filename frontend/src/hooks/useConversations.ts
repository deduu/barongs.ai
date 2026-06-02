import { useCallback, useEffect, useRef, useState } from "react";
import type { Conversation } from "../types";
import type { ConversationStore } from "./useConversationStore";
import { getItem, setItem } from "../lib/storage";

const MAX_CONVERSATIONS = 50;

function storageKey(userId: string | null): string {
  return userId ? `conversations_${userId}` : "conversations";
}

export function useConversations(
  userId: string | null = null,
  store: ConversationStore,
) {
  const userIdRef = useRef(userId);
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    getItem<Conversation[]>(storageKey(userId), []),
  );
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);

  // Reload conversations when userId changes (login/logout/switch user)
  useEffect(() => {
    if (userIdRef.current === userId) return;
    userIdRef.current = userId;
    const loaded = getItem<Conversation[]>(storageKey(userId), []);
    setConversations(loaded);
    setCurrentConvId(null);
  }, [userId]);

  const persist = useCallback((convs: Conversation[]) => {
    setItem(storageKey(userIdRef.current), convs.slice(0, MAX_CONVERSATIONS));
  }, []);

  const pendingProjectIdRef = useRef<string | null>(null);

  const newChat = useCallback((projectId?: string | null) => {
    const id = `conv-${Date.now()}`;
    setCurrentConvId(id);
    store.updateMessages(id, []);
    pendingProjectIdRef.current = projectId ?? null;
    return id;
  }, [store]);

  const loadConversation = useCallback(
    (id: string) => {
      const conv = conversations.find((c) => c.id === id);
      if (!conv) return;
      setCurrentConvId(id);
      // Only hydrate from localStorage if not already in the live store
      // (preserves in-progress streaming data)
      if (!store.hasMessages(id)) {
        store.updateMessages(id, conv.messages ?? []);
      }
    },
    [conversations, store],
  );

  const togglePin = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.map((c) =>
          c.id === id ? { ...c, pinned: !c.pinned } : c,
        );
        persist(next);
        return next;
      });
    },
    [persist],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      // Abort any active stream before deleting
      const meta = store.getStreamMeta(id);
      if (meta?.isStreaming) {
        meta.abortController?.abort();
        store.clearStreamMeta(id);
      }
      store.removeMessages(id);
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        persist(next);
        if (currentConvId === id) {
          if (next.length) {
            setCurrentConvId(next[0].id);
            if (!store.hasMessages(next[0].id)) {
              store.updateMessages(next[0].id, next[0].messages ?? []);
            }
          } else {
            const newId = `conv-${Date.now()}`;
            setCurrentConvId(newId);
            store.updateMessages(newId, []);
          }
        }
        return next;
      });
    },
    [currentConvId, persist, store],
  );

  const saveConversation = useCallback(
    (convId: string) => {
      const msgs = store.getMessages(convId);
      if (!msgs.length) return;
      const rawTitle =
        msgs.find((m) => m.role === "user")?.content ?? "New chat";
      const title =
        rawTitle.slice(0, 60) + (rawTitle.length > 60 ? "\u2026" : "");

      setConversations((prev) => {
        const existing = prev.find((c) => c.id === convId);
        const projectId =
          existing?.projectId ?? pendingProjectIdRef.current ?? undefined;
        const conv: Conversation = {
          id: convId,
          title,
          messages: msgs,
          updatedAt: Date.now(),
          ...(projectId ? { projectId } : {}),
        };
        const idx = prev.findIndex((c) => c.id === convId);
        const next = [...prev];
        if (idx >= 0) next[idx] = conv;
        else next.unshift(conv);
        persist(next);
        pendingProjectIdRef.current = null;
        return next;
      });
    },
    [persist, store],
  );

  const saveCurrentConversation = useCallback(() => {
    if (!currentConvId) return;
    saveConversation(currentConvId);
  }, [currentConvId, saveConversation]);

  const assignProject = useCallback(
    (conversationId: string, projectId: string | null) => {
      setConversations((prev) => {
        const next = prev.map((c) =>
          c.id === conversationId
            ? { ...c, projectId: projectId ?? undefined }
            : c,
        );
        persist(next);
        return next;
      });
    },
    [persist],
  );

  return {
    conversations,
    currentConvId,
    newChat,
    loadConversation,
    deleteConversation,
    togglePin,
    saveCurrentConversation,
    saveConversation,
    assignProject,
  } as const;
}
