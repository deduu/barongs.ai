import DOMPurify from "dompurify";
import hljs from "highlight.js";
import { marked } from "marked";

function escapeHtml(text: string): string {
  const map: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
  return text.replace(/[&<>]/g, (c) => map[c] ?? c);
}

function escapeAttr(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

const renderer = new marked.Renderer();
renderer.code = function (codeOrToken: string | { text: string; lang?: string }, lang?: string): string {
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

function stripSourcesSection(text: string): string {
  return text.replace(/\n---\s*\n#{1,3}\s*Sources[\s\S]*$/i, "").trimEnd();
}

export function renderStreaming(text: string): string {
  try {
    let html = marked.parse(stripSourcesSection(text)) as string;
    html = html.replace(
      /<a\s+href="/g,
      '<a target="_blank" rel="noopener noreferrer" href="',
    );
    return DOMPurify.sanitize(html, { ADD_ATTR: ["target", "rel"] });
  } catch {
    return escapeHtml(text);
  }
}

export function renderFinal(text: string): string {
  try {
    let html = marked.parse(stripSourcesSection(text)) as string;

    html = html.replace(
      /<a\s+href="([^"]*)">\[([^\]]+)\]<\/a>/g,
      (_match, url: string, label: string) => {
        const numeric = /^\d+$/.test(label);
        const idxAttr = numeric ? ` data-idx="${parseInt(label, 10) - 1}"` : "";
        return (
          `<button class="cite-badge" data-url="${escapeAttr(url)}" ` +
          `data-label="${escapeAttr(label)}"${idxAttr}>${label}</button>`
        );
      },
    );

    html = html.replace(
      /<a\s+href="([^"]*)">(\d+)<\/a>/g,
      (_match, url: string, num: string) => {
        const idx = parseInt(num, 10) - 1;
        return (
          `<button class="cite-badge" data-idx="${idx}" data-url="${escapeAttr(url)}" ` +
          `data-label="${escapeAttr(num)}">${num}</button>`
        );
      },
    );

    html = html.replace(
      /<a\s+href="/g,
      '<a target="_blank" rel="noopener noreferrer" href="',
    );

    return DOMPurify.sanitize(html, {
      ADD_ATTR: ["data-idx", "data-url", "data-label", "target", "rel"],
    });
  } catch {
    return escapeHtml(text);
  }
}

export function escapeUserHtml(text: string): string {
  return escapeHtml(text).replace(/\n/g, "<br>");
}
