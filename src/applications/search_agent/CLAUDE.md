# Search Agent Application

## Architecture
- Perplexity/Grok-style search chatbot
- Pipeline: QueryAnalyzer → SearchPathAgent → (or DirectAnswerer)
- SearchPathAgent wraps WebResearcher → Synthesizer behind an Orchestrator
  (PipelineWithMetadataStrategy) so sources flow from researcher to synthesizer
- SearchPipelineAgent delegates all agent calls through Orchestrator instances
- StreamableSearchPipeline is a presentation adapter for SSE streaming;
  it uses an Orchestrator for the research phase, then calls
  synthesizer.stream_run() directly (presentation-layer streaming)

## Key Rules
- All LLM calls go through src/core/llm/ providers (never import openai directly)
- All MCP calls go through src/core/mcp/ client (never import mcp directly)
- Tools use circuit breakers for external HTTP calls
- Sources must be validated and deduplicated before synthesis
- Citations use [1][2] format mapped to Source.index
- Streaming uses SSE via sse-starlette

## Testing
- Mock all LLM calls (never hit real APIs in tests)
- Mock all HTTP calls (search API, content fetching)
- Test the pipeline end-to-end with mocked dependencies
