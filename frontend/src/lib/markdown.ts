import DOMPurify from "dompurify";
import hljs from "highlight.js";
import { marked } from "marked";

function escapeHtml(text: string): string {
  const map: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
  return text.replace(/[&<>]/g, (c) => map[c] ?? c);
}

/* Configure marked once */
const renderer = new marked.Renderer();
renderer.code = function (codeOrToken: string | { text: string; lang?: string }, lang?: string): string {
  // Handle both marked v4 (string args) and v12+ (token object)
  const text = typeof codeOrToken === "object" ? codeOrToken.text : codeOrToken;
  const language = typeof codeOrToken === "object" ? (codeOrToken.lang ?? "") : (lang ?? "");
  try {
    const validLang = language && hljs.getLanguage(language);
    const hl = validLang
      ? hljs.highlight(text, { language }).value
      : hljs.highlightAuto(text).value;
    return `<pre><code class="hljs${validLang ? " language-" + language : ""}">${hl}</code></pre>`;
  } catch {
    return `<pre><code class="hljs">${escapeHtml(text)}</code></pre>`;
  }
};

marked.use({ gfm: true, breaks: true, renderer });

/** Render markdown during streaming (no citation processing). */
export function renderStreaming(text: string): string {
  try {
    let html = marked.parse(text) as string;
    // Make all links open in new tab during streaming too
    html = html.replace(
      /<a\s+href="/g,
      '<a target="_blank" rel="noopener noreferrer" href="',
    );
    return DOMPurify.sanitize(html, { ADD_ATTR: ["target", "rel"] });
  } catch {
    return escapeHtml(text);
  }
}

/** Render final markdown with citation badges. */
export function renderFinal(text: string): string {
  try {
    let html = marked.parse(text) as string;

    // [[N]](URL) → marked produces <a href="URL">[N]</a> → convert to cite-badge
    html = html.replace(
      /<a\s+href="([^"]*)">\[(\d+)\]<\/a>/g,
      (_match, _url: string, num: string) => {
        const idx = parseInt(num) - 1;
        return `<button class="cite-badge" data-idx="${idx}">${num}</button>`;
      },
    );

    // Also catch [N](URL) → marked produces <a href="URL">N</a> (number-only text)
    html = html.replace(
      /<a\s+href="([^"]*)">(\d+)<\/a>/g,
      (_match, _url: string, num: string) => {
        const idx = parseInt(num) - 1;
        return `<button class="cite-badge" data-idx="${idx}">${num}</button>`;
      },
    );

    // Make all remaining <a> tags open in new tab
    html = html.replace(
      /<a\s+href="/g,
      '<a target="_blank" rel="noopener noreferrer" href="',
    );

    return DOMPurify.sanitize(html, {
      ADD_ATTR: ["data-idx", "target", "rel"],
    });
  } catch {
    return escapeHtml(text);
  }
}

/** Escape user text for display (no markdown). */
export function escapeUserHtml(text: string): string {
  return escapeHtml(text).replace(/\n/g, "<br>");
}
