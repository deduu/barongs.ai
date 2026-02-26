export type ThemeMode = "dark" | "light" | "system";

export type ChatMode = "search" | "rag";

export interface Source {
  url: string;
  title?: string;
  snippet?: string;
  content?: string;
}

export interface RAGDocument {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
}

export type MessageStatus = "streaming" | "done" | "error";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  renderedHtml: string;
  sources: Source[];
  status: MessageStatus;
  timestamp: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
  pinned?: boolean;
}
