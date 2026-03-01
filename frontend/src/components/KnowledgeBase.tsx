import { useState } from "react";
import type { RAGDocument } from "../types";
import { formatBytes, formatDate, getFileTypeLabel } from "../lib/format";
import DocumentUpload from "./DocumentUpload";
import ChunkViewer from "./ChunkViewer";
import {
  BookIcon,
  TrashIcon,
  FileIcon,
  FilePdfIcon,
  FileSpreadsheetIcon,
  FilePresentationIcon,
  ImageIcon,
  EyeIcon,
  DownloadIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from "./icons";

interface KnowledgeBaseProps {
  documents: RAGDocument[];
  isLoading: boolean;
  isIngesting: boolean;
  error: string | null;
  apiKey: string;
  onUploadFile: (file: File, title: string) => Promise<unknown>;
  onUploadText: (content: string, title: string) => Promise<unknown>;
  onDelete: (docId: string) => void;
  onRefresh: () => void;
}

function getFileIcon(ext: string, size = 16) {
  switch (ext) {
    case ".pdf":
      return <FilePdfIcon size={size} />;
    case ".xlsx":
      return <FileSpreadsheetIcon size={size} />;
    case ".pptx":
      return <FilePresentationIcon size={size} />;
    case ".png":
    case ".jpg":
    case ".jpeg":
    case ".gif":
    case ".webp":
      return <ImageIcon size={size} />;
    default:
      return <FileIcon size={size} />;
  }
}

interface GroupedDoc {
  prefix: string;
  title: string;
  chunks: RAGDocument[];
  metadata: Record<string, unknown>;
}

export default function KnowledgeBase({
  documents,
  isLoading,
  isIngesting,
  error,
  apiKey,
  onUploadFile,
  onUploadText,
  onDelete,
  onRefresh,
}: KnowledgeBaseProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [viewingChunks, setViewingChunks] = useState<GroupedDoc | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // Group documents by their doc_id_prefix (e.g. "doc-abcd1234-0" -> "doc-abcd1234")
  const grouped: GroupedDoc[] = [];
  const groupMap = new Map<string, RAGDocument[]>();
  for (const doc of documents) {
    const prefix = doc.id.replace(/-\d+$/, "");
    const arr = groupMap.get(prefix) ?? [];
    arr.push(doc);
    groupMap.set(prefix, arr);
  }
  for (const [prefix, chunks] of groupMap) {
    const meta = chunks[0]?.metadata ?? {};
    grouped.push({
      prefix,
      title: (meta.title as string) ?? prefix,
      chunks,
      metadata: meta,
    });
  }

  const handleDelete = (doc: GroupedDoc) => {
    if (confirmDelete === doc.prefix) {
      for (const chunk of doc.chunks) {
        onDelete(chunk.id);
      }
      setConfirmDelete(null);
    } else {
      setConfirmDelete(doc.prefix);
      setTimeout(() => setConfirmDelete(null), 3000);
    }
  };

  const handleDownloadText = (doc: GroupedDoc) => {
    const text = doc.chunks.map((c) => c.content).join("\n\n---\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${doc.title.replace(/[^a-zA-Z0-9._-]/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
            {grouped.length} document{grouped.length !== 1 ? "s" : ""}
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
          ) : grouped.length === 0 ? (
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
              {grouped.map((doc) => {
                const meta = doc.metadata;
                const fileType = meta.file_type as string | undefined;
                const fileSize = meta.file_size as number | undefined;
                const uploadedAt = meta.uploaded_at as string | undefined;
                const sourceType = (meta.source_type as string) ?? "text";
                const isExpanded = expandedId === doc.prefix;
                const preview = doc.chunks[0]?.content ?? "";

                return (
                  <div
                    key={doc.prefix}
                    className="rounded-lg border transition-colors"
                    style={{ borderColor: "var(--border)" }}
                  >
                    {/* Card header */}
                    <div className="flex items-start gap-3 px-3 py-2.5">
                      <div
                        className="mt-0.5 flex-shrink-0 opacity-50"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        {fileType ? getFileIcon(fileType) : (
                          sourceType === "text" ? <FileIcon size={16} /> : <FileIcon size={16} />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div
                          className="truncate text-sm font-medium"
                          style={{ color: "var(--text)" }}
                        >
                          {doc.title}
                        </div>
                        <div
                          className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px]"
                          style={{ color: "var(--text-muted)" }}
                        >
                          {fileType && (
                            <span
                              className="rounded px-1.5 py-0.5"
                              style={{ background: "var(--surface-2)" }}
                            >
                              {getFileTypeLabel(fileType)}
                            </span>
                          )}
                          {fileSize != null && (
                            <span>{formatBytes(fileSize)}</span>
                          )}
                          <span>
                            {doc.chunks.length} chunk{doc.chunks.length !== 1 ? "s" : ""}
                          </span>
                          {uploadedAt && (
                            <span>{formatDate(uploadedAt)}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expandable preview */}
                    {preview && (
                      <div className="px-3 pb-1">
                        <button
                          className="flex items-center gap-1 text-[11px] transition-colors hover:underline"
                          style={{ color: "var(--text-muted)" }}
                          onClick={() =>
                            setExpandedId(isExpanded ? null : doc.prefix)
                          }
                        >
                          {isExpanded ? (
                            <ChevronDownIcon size={12} />
                          ) : (
                            <ChevronRightIcon size={12} />
                          )}
                          Preview
                        </button>
                        {isExpanded && (
                          <p
                            className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap text-xs leading-relaxed"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            {preview.slice(0, 500)}
                            {preview.length > 500 && "..."}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div
                      className="flex items-center gap-1 border-t px-3 py-1.5"
                      style={{ borderColor: "var(--border)" }}
                    >
                      <button
                        className="flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors hover:bg-[var(--surface-2)]"
                        style={{ color: "var(--text-muted)" }}
                        onClick={() => setViewingChunks(doc)}
                        title="View chunks"
                      >
                        <EyeIcon size={12} />
                        Chunks
                      </button>
                      <button
                        className="flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors hover:bg-[var(--surface-2)]"
                        style={{ color: "var(--text-muted)" }}
                        onClick={() => handleDownloadText(doc)}
                        title="Download extracted text"
                      >
                        <DownloadIcon size={12} />
                        Download
                      </button>
                      <div className="flex-1" />
                      <button
                        className="flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors hover:bg-[var(--surface-2)]"
                        style={{
                          color: confirmDelete === doc.prefix ? "#ef4444" : "var(--text-muted)",
                        }}
                        onClick={() => handleDelete(doc)}
                        title={
                          confirmDelete === doc.prefix
                            ? "Click again to confirm"
                            : "Delete document"
                        }
                      >
                        <TrashIcon size={12} />
                        {confirmDelete === doc.prefix ? "Confirm?" : "Delete"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Chunk viewer modal */}
      {viewingChunks && (
        <ChunkViewer
          docPrefix={viewingChunks.prefix}
          title={viewingChunks.title}
          apiKey={apiKey}
          onClose={() => setViewingChunks(null)}
        />
      )}
    </div>
  );
}
