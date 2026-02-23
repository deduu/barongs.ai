# Search Agent Application

## Architecture
- Perplexity/Grok-style search chatbot
- Pipeline: QueryAnalyzer → WebResearcher → Synthesizer (for search queries)
- Router: search vs direct answer path via QueryAnalyzer classification
- SearchPipelineAgent wraps the full pipeline as a single composite Agent

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
