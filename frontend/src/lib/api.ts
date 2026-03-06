import type { ChatMode, RAGDocument, Source } from "../types";

export interface OutlineSection {
  heading: string;
  description: string;
}

export interface ResearchTask {
  task_id: string;
  query: string;
  task_type: string;
  agent_name: string;
  depends_on: string[];
}

export interface StreamEvent {
  type:
    | "status" | "source" | "chunk" | "done" | "error"
    | "disambiguation_required" | "disambiguation_confirmed"
    | "planning" | "researching" | "finding" | "reflecting"
    | "synthesizing" | "budget_update" | "knowledge_graph"
    | "outline_ready" | "awaiting_confirmation" | "outline_confirmed";
  data: {
    message?: string;
    error?: string;
    text?: string;
    token?: string;
    response?: string;
    status?: string;
    sources?: Source[];
    rag_sources?: RAGSourceData[];
    url?: string;
    title?: string;
    snippet?: string;
    content?: string;
    finding?: Record<string, unknown>;
    finding_count?: number;
    // RAG source fields
    id?: string;
    score?: number;
    source?: string;
    metadata?: Record<string, unknown>;
    // Interactive outline fields
    session_id?: string;
    query?: string;
    research_mode?: string;
    sections?: OutlineSection[];
    research_tasks?: ResearchTask[];
    task_id?: string;
    agent_name?: string;
    active_task_count?: number;
    entity_name?: string;
    clarification?: string;
  };
}

export interface RAGSourceData {
  id: string;
  content: string;
  score: number;
  source: string;
  metadata: Record<string, unknown>;
}

export type OnEvent = (event: StreamEvent) => void;

/**
 * Internal SSE reader shared by both stream functions.
 */
function readSSE(
  resp: Response,
  onEvent: OnEvent,
  onDone: () => void,
  onError: (err: string) => void,
) {
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let evtType = "";
  let evtData = "";

  (async () => {
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const rawLine of lines) {
          const line = rawLine.replace(/\r$/, "");

          if (line.startsWith("event:")) {
            evtType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            evtData = line.slice(5).trim();
          } else if (line === "") {
            if (evtType && evtData) {
              try {
                onEvent({
                  type: evtType as StreamEvent["type"],
                  data: JSON.parse(evtData),
                });
              } catch (e) {
                console.warn("SSE parse error:", e);
              }
            }
            evtType = "";
            evtData = "";
          }
        }
      }

      // Flush decoder and remaining buffer after stream ends
      buf += decoder.decode(new Uint8Array(), { stream: false });
      if (buf.trim()) {
        for (const rawLine of buf.split("\n")) {
          const line = rawLine.replace(/\r$/, "");
          if (line.startsWith("event:")) {
            evtType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            evtData = line.slice(5).trim();
          }
        }
      }
      // Dispatch any pending event not terminated by a blank line
      if (evtType && evtData) {
        try {
          onEvent({
            type: evtType as StreamEvent["type"],
            data: JSON.parse(evtData),
          });
        } catch (e) {
          console.warn("SSE flush parse error:", e);
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError((e as Error).message);
      }
    } finally {
      onDone();
    }
  })();
}

/**
 * Start an SSE stream. Returns an AbortController for cleanup.
 * When mode is "rag", hits /api/rag/chat/stream instead.
 */
export function streamSearch(
  query: string,
  sessionId: string,
  apiKey: string,
  onEvent: OnEvent,
  onDone: () => void,
  onError: (err: string) => void,
  mode: ChatMode = "search",
  settings?: Record<string, unknown>,
): AbortController {
  const controller = new AbortController();

  const endpoint =
    mode === "rag"
      ? "/api/rag/chat/stream"
      : mode === "deep_search"
        ? "/api/deep-search/stream"
        : "/api/search/stream";

  const baseBody: Record<string, unknown> =
    mode === "rag"
      ? { query }
      : mode === "deep_search"
        ? { query, session_id: sessionId }
      : { query, session_id: sessionId };

  const body = JSON.stringify({ ...baseBody, ...settings });

  (async () => {
    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body,
        signal: controller.signal,
      });

      if (!resp.ok) {
        onError(`Error ${resp.status}: ${resp.statusText}`);
        onDone();
        return;
      }

      readSSE(resp, onEvent, onDone, onError);
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError((e as Error).message);
      }
      onDone();
    }
  })();

  return controller;
}

/* ── RAG Document Management API ──────────────────────── */

export async function ingestText(
  content: string,
  title: string,
  apiKey: string,
  metadata: Record<string, unknown> = {},
): Promise<{ chunks_ingested: number; doc_id_prefix: string }> {
  const resp = await fetch("/api/rag/ingest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ content, title, metadata }),
  });
  if (!resp.ok) throw new Error(`Ingest failed: ${resp.status}`);
  return resp.json();
}

export async function ingestFile(
  file: File,
  title: string,
  apiKey: string,
): Promise<{ chunks_ingested: number; doc_id_prefix: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("title", title);

  const resp = await fetch("/api/rag/ingest/file", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
  });
  if (!resp.ok) throw new Error(`File ingest failed: ${resp.status}`);
  return resp.json();
}

export async function listDocuments(
  apiKey: string,
): Promise<RAGDocument[]> {
  const resp = await fetch("/api/rag/documents", {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.documents ?? [];
}

export async function getDocumentChunks(
  docPrefix: string,
  apiKey: string,
): Promise<RAGDocument[]> {
  const resp = await fetch(`/api/rag/documents/${encodeURIComponent(docPrefix)}/chunks`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.chunks ?? [];
}

export async function deleteDocument(
  docId: string,
  apiKey: string,
): Promise<void> {
  await fetch(`/api/rag/documents/${encodeURIComponent(docId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${apiKey}` },
  });
}

/* ── Interactive Outline API ──────────────────────────── */

export async function confirmOutline(
  sessionId: string,
  apiKey: string,
  approved: boolean = true,
  sections?: OutlineSection[],
  researchTasks?: ResearchTask[],
): Promise<{ status: string }> {
  const body: Record<string, unknown> = { session_id: sessionId, approved };
  if (sections) body.sections = sections;
  if (researchTasks) body.research_tasks = researchTasks;

  const resp = await fetch("/api/deep-search/outline/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`Confirm failed: ${resp.status}`);
  return resp.json();
}

export async function confirmDisambiguation(
  sessionId: string,
  apiKey: string,
  clarification: string,
): Promise<{ status: string }> {
  const resp = await fetch("/api/deep-search/disambiguate/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({ session_id: sessionId, clarification }),
  });
  if (!resp.ok) throw new Error(`Disambiguation confirm failed: ${resp.status}`);
  return resp.json();
}

/**
 * Fetch available models from the OpenAI-compatible endpoint.
 */
export async function fetchModels(apiKey: string): Promise<string[]> {
  try {
    const r = await fetch("/v1/models", {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (!r.ok) return [];
    const data = await r.json();
    return ((data.data ?? []) as { id: string }[]).map((m) => m.id);
  } catch (e) {
    console.warn("fetchModels:", e);
    return [];
  }
}
