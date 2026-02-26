import type { RAGDocument } from "../types";
import DocumentUpload from "./DocumentUpload";
import { TrashIcon, BookIcon } from "./icons";

interface KnowledgeBaseProps {
  documents: RAGDocument[];
  isLoading: boolean;
  isIngesting: boolean;
  error: string | null;
  onUploadFile: (file: File, title: string) => Promise<unknown>;
  onUploadText: (content: string, title: string) => Promise<unknown>;
  onDelete: (docId: string) => void;
  onRefresh: () => void;
}

export default function KnowledgeBase({
  documents,
  isLoading,
  isIngesting,
  error,
  onUploadFile,
  onUploadText,
  onDelete,
  onRefresh,
}: KnowledgeBaseProps) {
  // Group documents by their doc_id_prefix (e.g. "doc-abcd1234-0" -> "doc-abcd1234")
  const grouped = new Map<string, RAGDocument[]>();
  for (const doc of documents) {
    const prefix = doc.id.replace(/-\d+$/, "");
    const arr = grouped.get(prefix) ?? [];
    arr.push(doc);
    grouped.set(prefix, arr);
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between border-b px-6 py-4"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <BookIcon size={20} />
          <h2 className="text-lg font-semibold" style={{ color: "var(--text)" }}>
            Knowledge Base
          </h2>
          <span
            className="rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
          >
            {documents.length} chunks
          </span>
        </div>
        <button
          className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--surface-2)]"
          style={{ color: "var(--text-secondary)" }}
          onClick={onRefresh}
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Upload section */}
          <DocumentUpload
            isIngesting={isIngesting}
            onUploadFile={onUploadFile}
            onUploadText={onUploadText}
          />

          {/* Error */}
          {error && (
            <p className="text-center text-sm" style={{ color: "#ef4444" }}>
              {error}
            </p>
          )}

          {/* Document list */}
          {isLoading ? (
            <p
              className="py-8 text-center text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              Loading documents...
            </p>
          ) : grouped.size === 0 ? (
            <p
              className="py-8 text-center text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              No documents yet. Upload a file or paste text above.
            </p>
          ) : (
            <div className="space-y-2">
              <h3
                className="text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--text-muted)" }}
              >
                Indexed Documents
              </h3>
              {[...grouped.entries()].map(([prefix, chunks]) => {
                const title =
                  (chunks[0]?.metadata?.title as string) ?? prefix;
                return (
                  <div
                    key={prefix}
                    className="group flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors hover:bg-[var(--surface-2)]"
                    style={{ borderColor: "var(--border)" }}
                  >
                    <BookIcon
                      size={16}
                      className="flex-shrink-0 opacity-40"
                    />
                    <div className="min-w-0 flex-1">
                      <div
                        className="truncate text-sm font-medium"
                        style={{ color: "var(--text)" }}
                      >
                        {title}
                      </div>
                      <div
                        className="text-[11px]"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {chunks.length} chunk{chunks.length !== 1 && "s"} &middot; ID: {prefix}
                      </div>
                    </div>
                    <button
                      className="flex h-7 w-7 items-center justify-center rounded-md opacity-0 transition-all hover:text-red-500 group-hover:opacity-100"
                      style={{ color: "var(--text-muted)" }}
                      onClick={() => {
                        for (const chunk of chunks) {
                          onDelete(chunk.id);
                        }
                      }}
                      title="Delete document"
                      aria-label={`Delete ${title}`}
                    >
                      <TrashIcon size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
