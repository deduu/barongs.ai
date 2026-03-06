# Progress Log

## 2026-03-06
- Added per-request timeout override support to Orchestrator.run(...) and covered it with a new unit test in tests/core/test_orchestrator.py.
- Made ResearchDAGStrategy time-budget aware: it now tracks elapsed wall time (used_time_seconds), clamps per-agent timeout to remaining budget, and avoids overrunning total budget.
- Updated deep-search streaming pipeline to honor request max_time_seconds in orchestrator calls, inject research_budget, apply request max_iterations, and emit explicit timeout errors with guidance.
- Added deep-search capacity and control wiring: configurable research_per_agent_timeout_seconds, stream_max_concurrent_requests, router admission control (429 at capacity), and request-timeout override in sync route.
- Refined DAG timeout enforcement so per-agent timeout never exceeds remaining time budget (prevents overshooting tight budgets).
- Added and updated targeted tests; focused deep-search/orchestrator suite passes (59 tests).
- Added Scholar-targeted academic search fallback (google_scholar_web) in AcademicSearchTool and wired AcademicResearcherAgent to query semantic scholar + arXiv + Scholar web in one pass.
- Hardened deep synthesis prompts/output for academic quality: explicit clickable citation format, injected reference catalog guidance, and automatic post-processing to append citation index/references when missing.
- Added/updated deep-search tests for Scholar fallback and reference enforcement; targeted deep-search suite passes (36 tests).
- Added timeout-budget handoff from ResearchDAGStrategy to agents (`agent_timeout_seconds` in task metadata), and aggregated `attempted_sources` across DAG outputs for downstream synthesis.
- Updated DeepWebResearcherAgent to be budget-aware: per-step timeout guards, bounded per-source crawl settings, early partial return on low remaining time, and `attempted_sources` metadata for every touched URL.
- Extended DeepCrawlerTool to accept per-request overrides (`max_depth`, `max_pages`, `page_timeout_seconds`) with safe bounds, enabling faster deep-search passes without changing global architecture defaults.
- Wired StreamableDeepSearchPipeline to carry `attempted_sources` from DAG results into synthesis context.
- Enhanced DeepSynthesizerAgent fallback mode: when verified findings are empty, it now uses attempted source URLs in prompt reference catalog and appends a `## Search Log References` section instead of empty references.
- Improved fallback post-processing to still append `## Search Log References` when the model emits a bare `## References` heading without any URLs.
- Added/updated targeted tests for timeout hint propagation, attempted-source aggregation, crawler overrides, pipeline metadata passthrough, and fallback reference rendering; targeted suite passes (51 tests).
- Upgraded frontend streaming visibility with a persistent live status telemetry panel (phase chips + elapsed timer + last update age + event counter + stale-step warning + moving activity bar) wired from SSE event timestamps in `useStreamSearch`.
- Verified frontend compiles after UI telemetry changes via `npm --prefix frontend run build`.
