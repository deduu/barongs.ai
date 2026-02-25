import { useCallback, useRef, useState } from "react";
import type { Conversation, Message } from "../types";
import { getItem, setItem } from "../lib/storage";

const MAX_CONVERSATIONS = 50;

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    getItem<Conversation[]>("conversations", []),
  );
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const persist = useCallback((convs: Conversation[]) => {
    setItem("conversations", convs.slice(0, MAX_CONVERSATIONS));
  }, []);

  const newChat = useCallback(() => {
    const id = `conv-${Date.now()}`;
    setCurrentConvId(id);
    setMessages([]);
    return id;
  }, []);

  const loadConversation = useCallback(
    (id: string) => {
      const conv = conversations.find((c) => c.id === id);
      if (!conv) return;
      setCurrentConvId(id);
      setMessages(conv.messages ?? []);
    },
    [conversations],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        persist(next);
        if (currentConvId === id) {
          if (next.length) {
            setCurrentConvId(next[0].id);
            setMessages(next[0].messages ?? []);
          } else {
            const newId = `conv-${Date.now()}`;
            setCurrentConvId(newId);
            setMessages([]);
          }
        }
        return next;
      });
    },
    [currentConvId, persist],
  );

  const saveCurrentConversation = useCallback(() => {
    const msgs = messagesRef.current;
    if (!msgs.length) return;
    const rawTitle =
      msgs.find((m) => m.role === "user")?.content ?? "New chat";
    const title =
      rawTitle.slice(0, 60) + (rawTitle.length > 60 ? "\u2026" : "");

    setConversations((prev) => {
      const conv: Conversation = {
        id: currentConvId!,
        title,
        messages: msgs,
        updatedAt: Date.now(),
      };
      const idx = prev.findIndex((c) => c.id === currentConvId);
      const next = [...prev];
      if (idx >= 0) next[idx] = conv;
      else next.unshift(conv);
      persist(next);
      return next;
    });
  }, [currentConvId, persist]);

  return {
    conversations,
    currentConvId,
    messages,
    setMessages,
    newChat,
    loadConversation,
    deleteConversation,
    saveCurrentConversation,
  } as const;
}
