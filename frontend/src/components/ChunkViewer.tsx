import { useEffect, useState } from "react";
import type { RAGDocument } from "../types";
import { getDocumentChunks } from "../lib/api";
import { CopyIcon, CheckIcon, XIcon } from "./icons";

interface ChunkViewerProps {
  docPrefix: string;
  title: string;
  apiKey: string;
  onClose: () => void;
}

export default function ChunkViewer({
  docPrefix,
  title,
  apiKey,
  onClose,
}: ChunkViewerProps) {
  const [chunks, setChunks] = useState<RAGDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDocumentChunks(docPrefix, apiKey).then((data) => {
      if (!cancelled) {
        setChunks(data);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [docPrefix, apiKey]);

  const copyChunk = async (id: string, content: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={onClose}
    >
      <div
        className="mx-4 flex max-h-[80vh] w-full max-w-2xl flex-col rounded-xl border shadow-xl"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between border-b px-5 py-3"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="min-w-0 flex-1">
            <h3
              className="truncate text-sm font-semibold"
              style={{ color: "var(--text)" }}
            >
              {title}
            </h3>
            <p
              className="text-[11px]"
              style={{ color: "var(--text-muted)" }}
            >
              {loading ? "Loading..." : `${chunks.length} chunk${chunks.length !== 1 ? "s" : ""}`}
            </p>
          </div>
          <button
            className="ml-3 flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--surface-2)]"
            style={{ color: "var(--text-muted)" }}
            onClick={onClose}
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Chunk list */}
        <div className="flex-1 overflow-y-auto px-5 py-3">
          {loading ? (
            <p
              className="py-8 text-center text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              Loading chunks...
            </p>
          ) : chunks.length === 0 ? (
            <p
              className="py-8 text-center text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              No chunks found.
            </p>
          ) : (
            <div className="space-y-3">
              {chunks.map((chunk, idx) => (
                <div
                  key={chunk.id}
                  className="rounded-lg border p-3"
                  style={{ borderColor: "var(--border)" }}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span
                      className="text-[11px] font-medium"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Chunk {idx + 1} &middot; {chunk.content.length} chars
                    </span>
                    <button
                      className="flex h-6 w-6 items-center justify-center rounded transition-colors hover:bg-[var(--surface-2)]"
                      style={{ color: "var(--text-muted)" }}
                      onClick={() => copyChunk(chunk.id, chunk.content)}
                      title="Copy chunk text"
                    >
                      {copiedId === chunk.id ? (
                        <CheckIcon size={12} />
                      ) : (
                        <CopyIcon size={12} />
                      )}
                    </button>
                  </div>
                  <pre
                    className="max-h-40 overflow-auto whitespace-pre-wrap text-xs leading-relaxed"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    {chunk.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
