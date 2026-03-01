export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** i;
  return `${value < 10 ? value.toFixed(1) : Math.round(value)} ${units[i]}`;
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

const FILE_TYPE_LABELS: Record<string, string> = {
  ".pdf": "PDF",
  ".pptx": "Presentation",
  ".xlsx": "Spreadsheet",
  ".png": "Image",
  ".jpg": "Image",
  ".jpeg": "Image",
  ".gif": "Image",
  ".webp": "Image",
  ".txt": "Text",
  ".md": "Markdown",
  ".csv": "CSV",
  ".json": "JSON",
  ".py": "Python",
  ".js": "JavaScript",
  ".ts": "TypeScript",
  ".html": "HTML",
  ".xml": "XML",
};

export function getFileTypeLabel(ext: string): string {
  return FILE_TYPE_LABELS[ext.toLowerCase()] ?? ext.replace(".", "").toUpperCase();
}
