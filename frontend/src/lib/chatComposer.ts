const BASE_TEXTAREA_CLASS_NAME =
  "w-full resize-none border-none bg-transparent text-[15px] leading-relaxed outline-none transition-all focus:ring-2 focus:ring-[var(--accent)]/25 rounded-xl placeholder:text-[var(--text-muted)]";

export const CHAT_TEXTAREA_MIN_HEIGHT = 44;
export const CHAT_TEXTAREA_MAX_HEIGHT = 200;
export const WELCOME_TEXTAREA_MIN_HEIGHT = 76;
export const WELCOME_TEXTAREA_MAX_HEIGHT = 160;

export const CHAT_TEXTAREA_CLASS_NAME = `${BASE_TEXTAREA_CLASS_NAME} box-border px-3 py-2.5`;
export const WELCOME_TEXTAREA_CLASS_NAME = `${BASE_TEXTAREA_CLASS_NAME} box-border px-4 py-3`;

export type ConversationBootstrapAction = "none" | "load-first" | "new-chat";

export function getAutoResizeHeight(
  scrollHeight: number,
  minHeight: number,
  maxHeight: number,
): number {
  return Math.max(minHeight, Math.min(scrollHeight, maxHeight));
}

export function getConversationBootstrapAction(
  currentConvId: string | null,
  conversationCount: number,
): ConversationBootstrapAction {
  if (currentConvId) return "none";
  return conversationCount > 0 ? "load-first" : "new-chat";
}
