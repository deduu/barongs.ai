import { useCallback, useEffect, useState } from "react";
import { fetchModels } from "../lib/api";

export function useModels(apiKey: string) {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");

  const refresh = useCallback(async () => {
    const ids = await fetchModels(apiKey);
    setModels(ids);
    if (ids.length && !selectedModel) {
      setSelectedModel(ids[0]);
    }
  }, [apiKey, selectedModel]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { models, selectedModel, setSelectedModel, refreshModels: refresh } as const;
}
