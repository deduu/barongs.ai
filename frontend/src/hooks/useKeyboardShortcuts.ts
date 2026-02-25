import { useEffect } from "react";

interface ShortcutHandlers {
  onNewChat?: () => void;
  onOpenSettings?: () => void;
  onCloseModal?: () => void;
}

export function useKeyboardShortcuts({ onNewChat, onOpenSettings, onCloseModal }: ShortcutHandlers) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const ctrl = e.ctrlKey || e.metaKey;

      if (ctrl && e.key === "k") {
        e.preventDefault();
        onNewChat?.();
      }

      if (ctrl && e.key === ",") {
        e.preventDefault();
        onOpenSettings?.();
      }

      if (e.key === "Escape") {
        onCloseModal?.();
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onNewChat, onOpenSettings, onCloseModal]);
}
