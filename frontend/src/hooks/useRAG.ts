import { useCallback, useEffect, useState } from "react";
import type { RAGDocument } from "../types";
import { deleteDocument, ingestFile, ingestText, listDocuments } from "../lib/api";

interface UseRAGOptions {
  apiKey: string;
}

export function useRAG({ apiKey }: UseRAGOptions) {
  const [documents, setDocuments] = useState<RAGDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await listDocuments(apiKey);
      setDocuments(docs);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, [apiKey]);

  // Load documents on mount
  useEffect(() => {
    refresh();
  }, [refresh]);

  const uploadText = useCallback(
    async (content: string, title: string) => {
      setIsIngesting(true);
      setError(null);
      try {
        const result = await ingestText(content, title, apiKey);
        await refresh();
        return result;
      } catch (e) {
        setError((e as Error).message);
        throw e;
      } finally {
        setIsIngesting(false);
      }
    },
    [apiKey, refresh],
  );

  const uploadFile = useCallback(
    async (file: File, title: string) => {
      setIsIngesting(true);
      setError(null);
      try {
        const result = await ingestFile(file, title, apiKey);
        await refresh();
        return result;
      } catch (e) {
        setError((e as Error).message);
        throw e;
      } finally {
        setIsIngesting(false);
      }
    },
    [apiKey, refresh],
  );

  const removeDocument = useCallback(
    async (docId: string) => {
      setError(null);
      try {
        await deleteDocument(docId, apiKey);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [apiKey],
  );

  return {
    documents,
    isLoading,
    isIngesting,
    error,
    uploadText,
    uploadFile,
    removeDocument,
    refresh,
  } as const;
}
