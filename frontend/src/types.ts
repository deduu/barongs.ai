export type ThemeMode = "dark" | "light" | "system";

export interface Source {
  url: string;
  title?: string;
  snippet?: string;
  content?: string;
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
}
