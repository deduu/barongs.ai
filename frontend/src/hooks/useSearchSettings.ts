import { useCallback, useState } from "react";
import type { ChatMode } from "../types";
import type { SearchSettings, PresetName } from "../lib/searchSettings";
import { DEFAULT_SETTINGS, PRESETS, findActivePreset } from "../lib/searchSettings";
import { getItem, setItem } from "../lib/storage";

const STORAGE_KEY = "search_settings";

/** Merge stored settings with defaults so new fields get default values. */
function migrateSettings(stored: SearchSettings): SearchSettings {
  return {
    search: { ...DEFAULT_SETTINGS.search, ...stored.search },
    deep_search: { ...DEFAULT_SETTINGS.deep_search, ...stored.deep_search },
    rag: { ...DEFAULT_SETTINGS.rag, ...stored.rag },
  };
}

export function useSearchSettings() {
  const [settings, setSettings] = useState<SearchSettings>(() => {
    const stored = getItem<SearchSettings>(STORAGE_KEY, DEFAULT_SETTINGS);
    const merged = migrateSettings(stored);
    setItem(STORAGE_KEY, merged);
    return merged;
  });

  const updateModeSettings = useCallback(
    <M extends ChatMode>(mode: M, partial: Partial<SearchSettings[M]>) => {
      setSettings((prev) => {
        const next: SearchSettings = {
          ...prev,
          [mode]: { ...prev[mode], ...partial },
        };
        setItem(STORAGE_KEY, next);
        return next;
      });
    },
    [],
  );

  const applyPreset = useCallback((mode: ChatMode, preset: PresetName) => {
    setSettings((prev) => {
      const presetValues = PRESETS[mode][preset];
      const next: SearchSettings = { ...prev, [mode]: { ...presetValues } };
      setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  const resetMode = useCallback((mode: ChatMode) => {
    setSettings((prev) => {
      const next: SearchSettings = { ...prev, [mode]: { ...DEFAULT_SETTINGS[mode] } };
      setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  const getActivePreset = useCallback(
    (mode: ChatMode): PresetName | null => {
      return findActivePreset(mode, settings[mode]);
    },
    [settings],
  );

  return { settings, updateModeSettings, applyPreset, resetMode, getActivePreset } as const;
}
