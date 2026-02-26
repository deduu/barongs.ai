import { useCallback, useRef, useState } from "react";
import { UploadIcon, FileIcon } from "./icons";

interface DocumentUploadProps {
  isIngesting: boolean;
  onUploadFile: (file: File, title: string) => Promise<unknown>;
  onUploadText: (content: string, title: string) => Promise<unknown>;
}

export default function DocumentUpload({
  isIngesting,
  onUploadFile,
  onUploadText,
}: DocumentUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [textTitle, setTextTitle] = useState("");
  const [textContent, setTextContent] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      const title = file.name.replace(/\.[^.]+$/, "");
      setStatus(`Uploading ${file.name}...`);
      try {
        const result = await onUploadFile(file, title);
        setStatus(
          `Ingested ${(result as { chunks_ingested: number }).chunks_ingested} chunks from "${file.name}"`,
        );
      } catch {
        setStatus("Upload failed.");
      }
    },
    [onUploadFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleTextSubmit = useCallback(async () => {
    if (!textContent.trim()) return;
    setStatus("Ingesting text...");
    try {
      const result = await onUploadText(
        textContent,
        textTitle || "Untitled",
      );
      setStatus(
        `Ingested ${(result as { chunks_ingested: number }).chunks_ingested} chunks`,
      );
      setTextTitle("");
      setTextContent("");
    } catch {
      setStatus("Ingest failed.");
    }
  }, [textContent, textTitle, onUploadText]);

  return (
    <div className="space-y-3">
      {/* File drop zone */}
      <div
        className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-6 text-center transition-colors"
        style={{
          borderColor: dragOver ? "var(--accent)" : "var(--border)",
          background: dragOver ? "var(--surface-2)" : "var(--surface)",
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter") fileRef.current?.click();
        }}
        aria-label="Upload file"
      >
        <UploadIcon size={24} className="opacity-40" />
        <div>
          <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
            Drop a file here
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {" "}or click to browse
          </span>
        </div>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
          .txt, .md, .csv (max 10MB)
        </span>
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".txt,.md,.csv,.json,.log,.py,.js,.ts,.html,.xml"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {/* Text paste area */}
      <div
        className="rounded-xl border"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="px-3 pt-2">
          <input
            type="text"
            className="w-full border-none bg-transparent text-sm font-medium outline-none placeholder:text-[var(--text-muted)]"
            style={{ color: "var(--text)" }}
            placeholder="Document title..."
            value={textTitle}
            onChange={(e) => setTextTitle(e.target.value)}
          />
        </div>
        <div className="px-3 py-1">
          <textarea
            className="w-full resize-none border-none bg-transparent text-[13px] leading-relaxed outline-none placeholder:text-[var(--text-muted)]"
            style={{ color: "var(--text)", minHeight: 80, maxHeight: 200 }}
            placeholder="Paste text content here..."
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
          />
        </div>
        <div
          className="flex items-center justify-between border-t px-3 py-2"
          style={{ borderColor: "var(--border)" }}
        >
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {textContent.length > 0 && `${textContent.length} chars`}
          </span>
          <button
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all hover:opacity-90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-35"
            style={{ background: "var(--accent)", color: "var(--bg)" }}
            onClick={handleTextSubmit}
            disabled={isIngesting || !textContent.trim()}
          >
            <FileIcon size={13} />
            Ingest
          </button>
        </div>
      </div>

      {/* Status message */}
      {status && (
        <p className="text-center text-xs" style={{ color: "var(--text-muted)" }}>
          {status}
        </p>
      )}
    </div>
  );
}
