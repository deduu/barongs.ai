import type { ChatMode } from "../types";

/* ── Per-mode settings interfaces ──────────────────────── */

export interface WebSearchSettings {
  temperature: number;
  max_sources: number;
  search_max_results: number;
}

export interface DeepSearchSettings {
  temperature: number;
  max_iterations: number;
  max_sources: number;
  extraction_detail: "low" | "medium" | "high";
  max_time_seconds: number;
  enable_academic_search: boolean;
  crawl_depth: number;
  research_mode: "general" | "academic" | "consultant";
  interactive_outline: boolean;
}

export interface RAGSettings {
  temperature: number;
  top_k: number;
  dense_weight: number;
  enable_reranker: boolean;
}

export interface SearchSettings {
  search: WebSearchSettings;
  deep_search: DeepSearchSettings;
  rag: RAGSettings;
}

/* ── Preset system ─────────────────────────────────────── */

export type PresetName = "quick" | "balanced" | "thorough";

type ModeSettings = SearchSettings[ChatMode];
type PresetsMap = { [M in ChatMode]: Record<PresetName, SearchSettings[M]> };

export const PRESETS: PresetsMap = {
  search: {
    quick: { temperature: 0.3, max_sources: 4, search_max_results: 10 },
    balanced: { temperature: 0.3, max_sources: 8, search_max_results: 20 },
    thorough: { temperature: 0.2, max_sources: 12, search_max_results: 30 },
  },
  deep_search: {
    quick: {
      temperature: 0.3,
      max_iterations: 1,
      max_sources: 3,
      extraction_detail: "low",
      max_time_seconds: 120,
      enable_academic_search: false,
      crawl_depth: 1,
      research_mode: "general",
      interactive_outline: false,
    },
    balanced: {
      temperature: 0.3,
      max_iterations: 3,
      max_sources: 5,
      extraction_detail: "medium",
      max_time_seconds: 300,
      enable_academic_search: true,
      crawl_depth: 2,
      research_mode: "general",
      interactive_outline: false,
    },
    thorough: {
      temperature: 0.2,
      max_iterations: 5,
      max_sources: 8,
      extraction_detail: "high",
      max_time_seconds: 600,
      enable_academic_search: true,
      crawl_depth: 3,
      research_mode: "general",
      interactive_outline: true,
    },
  },
  rag: {
    quick: { temperature: 0.3, top_k: 3, dense_weight: 0.7, enable_reranker: false },
    balanced: { temperature: 0.3, top_k: 5, dense_weight: 0.7, enable_reranker: true },
    thorough: { temperature: 0.2, top_k: 10, dense_weight: 0.7, enable_reranker: true },
  },
};

export const DEFAULT_SETTINGS: SearchSettings = {
  search: PRESETS.search.balanced,
  deep_search: PRESETS.deep_search.balanced,
  rag: PRESETS.rag.balanced,
};

/* ── Parameter metadata (drives generic UI rendering) ──── */

interface SliderMeta {
  label: string;
  description: string;
  type: "slider";
  min: number;
  max: number;
  step: number;
}

interface SelectMeta {
  label: string;
  description: string;
  type: "select";
  options: { value: string; label: string }[];
}

interface ToggleMeta {
  label: string;
  description: string;
  type: "toggle";
}

export type ParamMeta = SliderMeta | SelectMeta | ToggleMeta;

type ParamMetaMap<T> = { [K in keyof T]: ParamMeta };

export const PARAM_META: { [M in ChatMode]: ParamMetaMap<SearchSettings[M]> } = {
  search: {
    temperature: {
      label: "Temperature",
      description: "How creative vs. factual the response is",
      type: "slider",
      min: 0,
      max: 1,
      step: 0.1,
    },
    max_sources: {
      label: "Max Sources",
      description: "Number of web pages to analyze",
      type: "slider",
      min: 3,
      max: 15,
      step: 1,
    },
    search_max_results: {
      label: "Search Results",
      description: "How many search results to scan",
      type: "slider",
      min: 5,
      max: 30,
      step: 5,
    },
  },
  deep_search: {
    temperature: {
      label: "Temperature",
      description: "How creative vs. factual the response is",
      type: "slider",
      min: 0,
      max: 1,
      step: 0.1,
    },
    max_iterations: {
      label: "Research Iterations",
      description: "Rounds of research to perform",
      type: "slider",
      min: 1,
      max: 5,
      step: 1,
    },
    max_sources: {
      label: "Sources per Task",
      description: "Web pages analyzed per research task",
      type: "slider",
      min: 3,
      max: 10,
      step: 1,
    },
    extraction_detail: {
      label: "Extraction Detail",
      description: "How much detail to extract per source",
      type: "select",
      options: [
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
      ],
    },
    max_time_seconds: {
      label: "Time Budget",
      description: "Maximum research time in seconds",
      type: "slider",
      min: 60,
      max: 600,
      step: 30,
    },
    enable_academic_search: {
      label: "Academic Search",
      description: "Include academic papers from Semantic Scholar and arXiv",
      type: "toggle",
    },
    crawl_depth: {
      label: "Crawl Depth",
      description: "How deep to follow links from each page",
      type: "slider",
      min: 1,
      max: 3,
      step: 1,
    },
    research_mode: {
      label: "Report Style",
      description: "Output format for the research report",
      type: "select",
      options: [
        { value: "general", label: "General Report" },
        { value: "academic", label: "Academic Paper" },
        { value: "consultant", label: "Consulting Report" },
      ],
    },
    interactive_outline: {
      label: "Interactive Outline",
      description: "Review and edit the research plan before execution begins",
      type: "toggle",
    },
  },
  rag: {
    temperature: {
      label: "Temperature",
      description: "How creative vs. factual the response is",
      type: "slider",
      min: 0,
      max: 1,
      step: 0.1,
    },
    top_k: {
      label: "Results to Retrieve",
      description: "Number of document chunks to retrieve",
      type: "slider",
      min: 1,
      max: 20,
      step: 1,
    },
    dense_weight: {
      label: "Semantic vs. Keyword",
      description: "Balance between semantic search and keyword match (higher = more semantic)",
      type: "slider",
      min: 0,
      max: 1,
      step: 0.1,
    },
    enable_reranker: {
      label: "Reranking",
      description: "Rerank results with a cross-encoder for better relevance",
      type: "toggle",
    },
  },
};

/** Check if two mode settings objects are deeply equal. */
export function settingsEqual(a: ModeSettings, b: ModeSettings): boolean {
  const ka = Object.keys(a) as (keyof typeof a)[];
  const kb = Object.keys(b) as (keyof typeof b)[];
  if (ka.length !== kb.length) return false;
  return ka.every((k) => a[k] === (b as unknown as Record<string, unknown>)[k]);
}

/** Find which preset (if any) matches the given mode settings. */
export function findActivePreset(mode: ChatMode, current: ModeSettings): PresetName | null {
  const modePresets = PRESETS[mode] as Record<PresetName, ModeSettings>;
  for (const name of ["quick", "balanced", "thorough"] as PresetName[]) {
    if (settingsEqual(current, modePresets[name])) return name;
  }
  return null;
}
