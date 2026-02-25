import type { Source } from "../types";

export interface StreamEvent {
  type: "status" | "source" | "chunk" | "done" | "error";
  data: {
    message?: string;
    text?: string;
    response?: string;
    sources?: Source[];
    url?: string;
    title?: string;
    snippet?: string;
    content?: string;
  };
}

export type OnEvent = (event: StreamEvent) => void;

/**
 * Start an SSE search stream. Returns an AbortController for cleanup.
 */
export function streamSearch(
  query: string,
  sessionId: string,
  apiKey: string,
  onEvent: OnEvent,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const resp = await fetch("/api/search/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({ query, session_id: sessionId }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        onError(`Error ${resp.status}: ${resp.statusText}`);
        return;
      }

      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let evtType = "";
      let evtData = "";

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
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError((e as Error).message);
      }
    } finally {
      onDone();
    }
  })();

  return controller;
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
