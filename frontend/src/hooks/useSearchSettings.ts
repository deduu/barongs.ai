import { useCallback, useState } from "react";
import type { ChatMode } from "../types";
import type { SearchSettings, PresetName } from "../lib/searchSettings";
import { DEFAULT_SETTINGS, PRESETS, findActivePreset } from "../lib/searchSettings";
import { getItem, setItem } from "../lib/storage";

const STORAGE_KEY = "search_settings";

export function useSearchSettings() {
  const [settings, setSettings] = useState<SearchSettings>(() =>
    getItem<SearchSettings>(STORAGE_KEY, DEFAULT_SETTINGS),
  );

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
