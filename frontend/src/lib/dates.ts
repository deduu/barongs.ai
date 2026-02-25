import type { Conversation } from "../types";

export interface ConversationGroup {
  label: string;
  conversations: Conversation[];
}

export function groupConversations(conversations: Conversation[]): ConversationGroup[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const pinned: Conversation[] = [];
  const todayList: Conversation[] = [];
  const yesterdayList: Conversation[] = [];
  const weekList: Conversation[] = [];
  const older: Conversation[] = [];

  const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  for (const conv of sorted) {
    if (conv.pinned) {
      pinned.push(conv);
      continue;
    }
    const d = new Date(conv.updatedAt);
    if (d >= today) {
      todayList.push(conv);
    } else if (d >= yesterday) {
      yesterdayList.push(conv);
    } else if (d >= weekAgo) {
      weekList.push(conv);
    } else {
      older.push(conv);
    }
  }

  const groups: ConversationGroup[] = [];
  if (pinned.length) groups.push({ label: "Pinned", conversations: pinned });
  if (todayList.length) groups.push({ label: "Today", conversations: todayList });
  if (yesterdayList.length) groups.push({ label: "Yesterday", conversations: yesterdayList });
  if (weekList.length) groups.push({ label: "Previous 7 Days", conversations: weekList });
  if (older.length) groups.push({ label: "Older", conversations: older });

  return groups;
}
