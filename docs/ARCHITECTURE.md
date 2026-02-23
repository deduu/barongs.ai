# Pormetheus — Architecture Documentation

> Generated 2026-02-23 | Scope: Full codebase
> Stack: Python 3.11+, FastAPI, Pydantic v2, asyncio, httpx

---

## 1. Project Overview

Pormetheus is a production-ready Python AI agent framework providing generic, reusable abstractions (Agent, Tool, Memory, Orchestrator) so concrete AI applications can be built without reinventing infrastructure concerns like timeout enforcement, circuit breaking, rate limiting, authentication, structured logging, and LLM provider integration.

The framework ships two concrete applications:
- **example_app** — Minimal reference app demonstrating framework wiring, using a trivial `EchoAgent`.
- **search_agent** — A Perplexity-style search chatbot performing real web research, synthesizing results with citations, supporting streaming via SSE, and exposing an OpenAI-compatible `/v1/chat/completions` API.

---

## 2. Directory Structure

```
pormetheus/
├── pyproject.toml                   # Project metadata, dependencies, ruff/mypy/pytest config
├── CLAUDE.md                        # Development rules and architecture conventions
│
├── src/
│   ├── core/                        # Framework library — generic, no app-specific logic
│   │   ├── interfaces/
│   │   │   ├── agent.py             # Agent ABC
│   │   │   ├── tool.py              # Tool ABC
│   │   │   ├── memory.py            # Memory ABC
│   │   │   └── orchestrator.py      # OrchestratorStrategy Protocol + Orchestrator class
│   │   ├── models/
│   │   │   ├── context.py           # AgentContext (frozen), ToolInput
│   │   │   ├── results.py           # AgentResult, ToolResult, ToolCallRecord
│   │   │   ├── messages.py          # Message, Conversation, Role
│   │   │   └── config.py            # AppSettings (pydantic-settings, PROM_ prefix)
│   │   ├── orchestrator/strategies/
│   │   │   ├── single_agent.py      # SingleAgentStrategy
│   │   │   ├── router.py            # RouterStrategy
│   │   │   ├── pipeline.py          # PipelineStrategy
│   │   │   └── parallel.py          # ParallelStrategy + default_merge
│   │   ├── middleware/
│   │   │   ├── auth.py              # verify_api_key, create_api_key_dependency
│   │   │   ├── circuit_breaker.py   # CircuitBreaker, CircuitBreakerError, CircuitState
│   │   │   ├── rate_limiter.py      # TokenBucketRateLimiter, RateLimitExceededError
│   │   │   ├── timeout.py           # with_timeout, timeout_decorator
│   │   │   └── logging.py           # setup_logging, get_logger (structlog)
│   │   ├── server/
│   │   │   ├── factory.py           # create_app() — App Factory pattern
│   │   │   ├── dependencies.py      # get_settings FastAPI dependency
│   │   │   ├── health.py            # GET /health, GET /ready
│   │   │   ├── exception_handlers.py
│   │   │   └── openai_compat/
│   │   │       ├── models.py        # OpenAI wire-format Pydantic models
│   │   │       ├── converters.py    # openai_request_to_context, agent_result_to_openai_response
│   │   │       ├── registry.py      # ModelRegistry, RegisteredModel, StreamableAgent Protocol
│   │   │       ├── router.py        # GET /v1/models, POST /v1/chat/completions
│   │   │       └── auth.py          # create_bearer_auth_dependency
│   │   ├── llm/
│   │   │   ├── base.py              # LLMProvider ABC
│   │   │   ├── models.py            # LLMMessage, LLMRequest, LLMResponse
│   │   │   ├── registry.py          # LLMProviderRegistry
│   │   │   └── providers/
│   │   │       ├── openai.py        # OpenAIProvider
│   │   │       └── openai_compatible.py  # OpenAICompatibleProvider (vLLM, Ollama)
│   │   ├── mcp/
│   │   │   ├── client.py            # MCPClient, MCPServerConfig
│   │   │   ├── tool_adapter.py      # MCPToolAdapter (wraps MCP tool as pormetheus Tool)
│   │   │   └── skills_loader.py     # load_skills_md()
│   │   └── utils/
│   │       ├── async_helpers.py     # gather_with_timeout, retry_async
│   │       └── sanitize.py          # sanitize_dict, redact_string
│
│   └── applications/
│       ├── example_app/             # Reference application
│       │   ├── config.py            # ExampleAppSettings(AppSettings)
│       │   ├── main.py              # create_example_app() composition root
│       │   ├── routes.py            # POST /api/chat
│       │   ├── lambda_handler.py    # AWS Lambda via Mangum
│       │   ├── agents/echo_agent.py
│       │   ├── tools/web_search_tool.py
│       │   └── memory/in_memory.py
│       │
│       └── search_agent/            # Production search chatbot
│           ├── config.py            # SearchAgentSettings(AppSettings)
│           ├── main.py              # create_search_app() composition root
│           ├── routes.py            # POST /api/search, /api/search/stream, /api/chat
│           ├── streaming_pipeline.py # StreamableSearchPipeline (OpenAI streaming adapter)
│           ├── lambda_handler.py
│           ├── agents/
│           │   ├── query_analyzer.py
│           │   ├── web_researcher.py
│           │   ├── synthesizer.py       # Streaming-capable
│           │   ├── direct_answerer.py
│           │   └── search_pipeline.py   # Composite agent (routes internally)
│           ├── tools/
│           │   ├── search_api.py    # BraveSearchTool, DuckDuckGoSearchTool
│           │   ├── content_fetcher.py
│           │   └── url_validator.py
│           ├── memory/
│           │   ├── conversation_memory.py  # Sliding-window
│           │   └── semantic_memory.py      # Keyword search + namespace support
│           └── models/
│               ├── search.py        # Source, SearchQuery, SearchResult
│               └── streaming.py     # StreamEventType, StreamEvent
│
└── tests/
    ├── conftest.py                  # StubAgent, StubTool, StubMemory, async_client
    ├── core/                        # Tests for framework library
    └── applications/                # Tests for each app
```

---

## 3. Architecture & Patterns

### 3.1 High-Level Architecture

```
[HTTP Client / Open WebUI]
         │
         ▼
[FastAPI App] ── created by create_app() in src/core/server/factory.py
         │
         ├── CORSMiddleware
         ├── Exception handlers (Timeout→504, CircuitBreaker→503, RateLimit→429)
         ├── GET /health, GET /ready
         ├── App-specific routes (e.g. POST /api/search)
         └── OpenAI-compat routes (GET /v1/models, POST /v1/chat/completions)
                   │
                   ▼
            [Orchestrator]  — asyncio.wait_for(timeout=30s)
                   │
         [OrchestratorStrategy]
         SingleAgent | Router | Pipeline | Parallel
                   │
             [Agent(s)]  — receives frozen AgentContext, returns AgentResult
                   │
                   ├── LLM calls → src/core/llm/ providers (AsyncOpenAI)
                   └── Tool calls → src/core/interfaces/tool.py
                              │
                              └── External HTTP → httpx + CircuitBreaker
```

### 3.2 Design Patterns

**App Factory** (`src/core/server/factory.py`): `create_app(settings)` produces a configured `FastAPI` instance. Each application's `create_*_app()` calls this factory and then includes additional routers. Separates serving infrastructure from business logic.

**Strategy Pattern** (`src/core/interfaces/orchestrator.py`): `Orchestrator` holds a swappable `OrchestratorStrategy`. Defined as a `Protocol` (structural typing) — third-party strategies need no base class inheritance. Swappable at runtime via `orchestrator.strategy = new_strategy`.

```python
# src/core/interfaces/orchestrator.py
@runtime_checkable
class OrchestratorStrategy(Protocol):
    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult: ...
```

**Frozen Pydantic Models** (`src/core/models/context.py`): `AgentContext` uses `model_config = {"frozen": True}`. Agents cannot mutate context; they call `context.model_copy(update={...})` to produce a new context for the next pipeline stage.

**Composition Root** (each app's `main.py`): All dependencies (LLM providers, tools, agents, orchestrators) are wired together explicitly in a single `create_*_app()` function. No lazy resolution or DI containers.

**Composite Agent** (`src/applications/search_agent/agents/search_pipeline.py`): `SearchPipelineAgent` implements `Agent` and internally orchestrates `QueryAnalyzer → WebResearcher → Synthesizer` (or `DirectAnswerer`). The outer `Orchestrator` sees it as a single agent, keeping inter-agent routing inside the composite without violating the "agents never call each other via the orchestrator" rule.

**Adapter** (`src/core/mcp/tool_adapter.py`): `MCPToolAdapter` implements `Tool` and delegates to `MCPClient`. Any MCP server tool becomes a first-class pormetheus tool.

**Registry** (`src/core/llm/registry.py`, `src/core/server/openai_compat/registry.py`): Both use the same pattern — a dict keyed by string name, with `register()` / `get()` / `list_*()` methods.

### 3.3 Architectural Rules

- **Unidirectional dependency**: `applications → core`, never `core → applications`. The core library has zero imports from `src.applications`.
- **Agents never call agents directly**: The only legal form of agent composition is a composite agent (`SearchPipelineAgent`) that holds references injected at construction time. External orchestration always goes through `Orchestrator.run()`.
- **Tools never access memory directly**: Memory is injected into `AgentContext.metadata` by the composition root and passed through. Tools only receive `ToolInput`.
- **All external I/O through the tools layer**: Agents call tools; they do not use httpx directly (LLM calls go through `src/core/llm/`).
- **Circuit breakers on every external call**: Every HTTP tool holds a `CircuitBreaker` instance and wraps calls with `await self._circuit_breaker.call(...)`.
- **All I/O must be async**: No blocking calls. Sync-only SDKs (e.g. `ddgs`) are wrapped with `asyncio.to_thread`.

---

## 4. Data Flow

### 4.1 Standard Non-Streaming Search Request

```
POST /api/search {"query": "..."}
    │
    ▼ SearchRequest validated by Pydantic (routes.py)
    │ X-API-Key header checked via create_api_key_dependency
    ▼
AgentContext(user_message=request.query)  ← frozen
    │
    ▼ Orchestrator.run(context)
      asyncio.wait_for(..., timeout=30s)
      └── SingleAgentStrategy → SearchPipelineAgent.run(context)
            ├── QueryAnalyzerAgent → LLMProvider.generate()
            │     returns: {query_type, refined_queries}
            │
            ├── [search path] WebResearcherAgent.run(research_context)
            │     ├── asyncio.gather(search_tool.execute() × N queries)
            │     │     └── CircuitBreaker → httpx → Brave/DuckDuckGo API
            │     ├── url_validator.execute(all URLs)
            │     └── asyncio.gather(content_fetcher.execute(url) × top N)
            │           └── CircuitBreaker → httpx → GET → BeautifulSoup → text
            │
            └── SynthesizerAgent.run(synth_context)
                  └── LLMProvider.generate(sources in system prompt)
                        returns: cited markdown with [[N]](URL) links
    │
    ▼
SearchResponse(response, sources, query_type, agent_name) → JSON 200
```

**Data models at each boundary:**
- Route input: `SearchRequest` (`src/applications/search_agent/routes.py`)
- Agent boundary: `AgentContext` (`src/core/models/context.py`) — frozen
- Search models: `Source`, `SearchQuery`, `SearchResult` (`src/applications/search_agent/models/search.py`)
- Agent output: `AgentResult` (`src/core/models/results.py`)
- Route output: `SearchResponse` (`src/applications/search_agent/routes.py`)

### 4.2 Streaming Search Request (SSE)

```
POST /api/search/stream
    │
    ▼ EventSourceResponse(event_generator())
    ├── yield STATUS "Searching..."
    ├── WebResearcherAgent.run()           ← gather all sources first
    ├── yield SOURCE event per source
    ├── yield STATUS "Synthesizing..."
    ├── SynthesizerAgent.stream_run()
    │     └── LLMProvider.stream() → AsyncIterator[str]
    │           └── yield CHUNK {"text": token} per token
    └── yield DONE {"response": full, "sources": sources}
```

### 4.3 OpenAI-Compatible API Flow

```
POST /v1/chat/completions {"model": "gpt-4o", "messages": [...], "stream": true}
    │
    ▼ create_openai_router (src/core/server/openai_compat/router.py)
    ├── Bearer token validated (if openai_auth_enabled=True)
    ├── openai_request_to_context(request) → AgentContext
    │     (last user message → user_message; others → conversation_history)
    │
    ├── stream=False: orchestrator.run() → agent_result_to_openai_response()
    │
    └── stream=True: EventSourceResponse
          └── StreamableSearchPipeline.stream_run()
                ├── WebResearcherAgent.run()        [non-streaming]
                └── SynthesizerAgent.stream_run()   [token streaming]
```

### 4.4 Direct Answer Path

When `QueryAnalyzerAgent` classifies the query as `"direct"`:

```
SearchPipelineAgent.run()
    └── DirectAnswererAgent.run(context)
          ├── Builds messages from context.conversation_history
          └── LLMProvider.generate() → AgentResult (no sources, no web search)
```

### 4.5 Example App Request

```
POST /api/chat {"message": "Hello!"}
    │  X-API-Key header required
    ▼
AgentContext(user_message="Hello!")
    │
    ▼ Orchestrator → SingleAgentStrategy → EchoAgent.run()
    └── returns AgentResult(response="[Echo] Hello!")
    │
    ▼
ChatResponse(response, agent_name, metadata) → JSON 200
```

---

## 5. Dependency Map

### 5.1 Hub Files (high blast radius)

| File | Imported By | Role |
|------|-------------|------|
| `src/core/interfaces/agent.py` | All agents, orchestrator strategies, conftest | Agent contract |
| `src/core/models/context.py` | Every agent, every tool, every route, orchestrator | Primary I/O model |
| `src/core/models/results.py` | Every agent, every tool, orchestrator, routes | Primary output model |
| `src/core/models/config.py` | All `*Settings` classes, factory, auth, rate limiter | Config base |
| `src/core/middleware/circuit_breaker.py` | All HTTP tools, exception_handlers | Resilience |
| `src/core/llm/base.py` | QueryAnalyzerAgent, SynthesizerAgent, DirectAnswererAgent, OpenAIProvider | LLM contract |
| `src/core/server/factory.py` | example_app/main.py, search_agent/main.py | App creation |
| `src/core/interfaces/orchestrator.py` | Both app main.py, openai_compat/router.py | Orchestration contract |

### 5.2 External Boundaries

| Boundary | Code Location | Protection |
|----------|---------------|------------|
| OpenAI / OpenAI-compatible LLM | `src/core/llm/providers/openai.py` | `httpx.Timeout(30s, connect=5s)` via AsyncOpenAI |
| Brave Search API | `src/applications/search_agent/tools/search_api.py:BraveSearchTool` | CircuitBreaker(threshold=3, recovery=60s) |
| DuckDuckGo (ddgs) | `src/applications/search_agent/tools/search_api.py:DuckDuckGoSearchTool` | CircuitBreaker + `asyncio.to_thread` |
| Web page content | `src/applications/search_agent/tools/content_fetcher.py` | CircuitBreaker, 10s timeout |
| MCP servers | `src/core/mcp/client.py` | stdio transport; managed via AsyncExitStack |
| AWS Lambda | `src/**/lambda_handler.py` | Mangum ASGI adapter |

### 5.3 Module Dependency Direction

```
src/applications/search_agent/  ──►  src/core/
src/applications/example_app/   ──►  src/core/
src/core/  ✗  never imports from  src/applications/

Within src/core:
  server/         ──►  middleware/, models/, interfaces/
  orchestrator/   ──►  interfaces/, models/
  llm/            ──►  (self-contained)
  mcp/            ──►  interfaces/tool.py, models/context.py, models/results.py
  middleware/     ──►  models/config.py (auth only)
  utils/          ──►  (no internal imports)
```

---

## 6. Extension Guide

### Adding a New Agent

1. **Write tests first** in `tests/applications/{app}/test_{agent_name}.py`. Mock the LLM provider with `AsyncMock`.

2. Create `src/applications/{app}/agents/{name}.py`:

```python
from __future__ import annotations
from src.core.interfaces.agent import Agent
from src.core.models.context import AgentContext
from src.core.models.results import AgentResult

class MyAgent(Agent):
    @property
    def name(self) -> str: return "my_agent"

    @property
    def description(self) -> str: return "What this agent does."

    async def run(self, context: AgentContext) -> AgentResult:
        response = await self._llm.generate(...)
        return AgentResult(agent_name=self.name, response=response.content)
```

3. Inject in the composition root (`create_*_app()`) and pass to `Orchestrator(agents=[...])`.

4. For streaming, implement `stream_run(context) -> AsyncIterator[str]` and register via `ModelRegistry.register(..., streamable_agent=...)`.

### Adding a New Tool

1. **Write tests first** in `tests/applications/{app}/test_{tool_name}.py`. Patch `httpx.AsyncClient` for HTTP tools.

2. Create `src/applications/{app}/tools/{name}.py`:

```python
from __future__ import annotations
from src.core.interfaces.tool import Tool
from src.core.middleware.circuit_breaker import CircuitBreaker
from src.core.models.context import ToolInput
from src.core.models.results import ToolResult

class MyTool(Tool):
    def __init__(self) -> None:
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    @property
    def name(self) -> str: return "my_tool"
    @property
    def description(self) -> str: return "What this tool does."
    @property
    def input_schema(self) -> dict: return {"type": "object", "properties": {...}, "required": [...]}

    async def execute(self, tool_input: ToolInput) -> ToolResult:
        async def _call() -> str:
            async with httpx.AsyncClient() as client:
                resp = await client.get(..., timeout=10.0)
                resp.raise_for_status()
                return resp.text
        try:
            output = await self._circuit_breaker.call(_call)
            return ToolResult(tool_name=self.name, output=output)
        except Exception as exc:
            return ToolResult(tool_name=self.name, output=None, success=False, error=str(exc))
```

3. Instantiate in the composition root and inject into agents via constructor.

4. For MCP tools: use `MCPClient` + `MCPToolAdapter.from_mcp_tool_info()` — no need for the above.

### Adding a New Orchestration Strategy

1. **Write tests first** in `tests/core/test_orchestrator.py`.

2. Create `src/core/orchestrator/strategies/{name}.py`. No inheritance needed — just satisfy the `OrchestratorStrategy` Protocol:

```python
class MyStrategy:
    async def execute(self, agents: list[Agent], context: AgentContext) -> AgentResult:
        ...
```

3. Export from `src/core/orchestrator/strategies/__init__.py` and `src/core/orchestrator/__init__.py`.

### Adding a New Application

1. Create `src/applications/{app_name}/` with `__init__.py`, `config.py`, `main.py`, `routes.py`, `agents/`, `tools/`.

2. `config.py` — extend `AppSettings`:
```python
from src.core.models.config import AppSettings
class MyAppSettings(AppSettings):
    app_name: str = "my-app"
```

3. `main.py` — write the composition root:
```python
from src.core.server.factory import create_app
def create_my_app() -> FastAPI:
    settings = MyAppSettings()
    orchestrator = Orchestrator(strategy=SingleAgentStrategy(), agents=[MyAgent(...)])
    app = create_app(settings)
    app.include_router(create_router(orchestrator, settings))
    return app
app = create_my_app()
```

4. `routes.py` — endpoints with `create_api_key_dependency`:
```python
def create_router(orchestrator, settings) -> APIRouter:
    verify_key = create_api_key_dependency(settings)
    @router.post("/run")
    async def run(req: MyRequest, _: str = Depends(verify_key)) -> MyResponse:
        result = await orchestrator.run(AgentContext(user_message=req.message))
        return MyResponse(response=result.response)
```

5. Optionally add `lambda_handler.py` using `Mangum(create_my_app(), lifespan="auto")`.

6. Create test files in `tests/applications/{app_name}/` **before** implementation files.

---

## 7. Configuration

All settings use `pydantic-settings` with `PROM_` prefix, loaded from environment or `.env`.

**Base settings** (`src/core/models/config.py:AppSettings`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROM_APP_NAME` | `"pormetheus"` | FastAPI title |
| `PROM_DEBUG` | `false` | FastAPI debug mode |
| `PROM_LOG_LEVEL` | `"INFO"` | structlog level |
| `PROM_ENVIRONMENT` | `"development"` | `"production"` enables JSON logging |
| `PROM_API_KEY` | `"changeme"` | Required `X-API-Key` header value |
| `PROM_CORS_ORIGINS` | `["*"]` | CORS origins (use specific list in production) |
| `PROM_OPENAI_AUTH_ENABLED` | `false` | Bearer token auth on `/v1/*` |
| `PROM_AGENT_TIMEOUT_SECONDS` | `30.0` | `asyncio.wait_for` on orchestrator |
| `PROM_TOOL_TIMEOUT_SECONDS` | `15.0` | Available for tools to consume |
| `PROM_RATE_LIMIT_REQUESTS` | `100` | Token bucket capacity |
| `PROM_RATE_LIMIT_WINDOW_SECONDS` | `60` | Token bucket refill window |
| `PROM_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `PROM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `30` | Seconds before HALF_OPEN |

**Search agent additions** (`src/applications/search_agent/config.py:SearchAgentSettings`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROM_LLM_PROVIDER` | `"openai"` | Registry key for LLM provider |
| `PROM_LLM_MODEL` | `"gpt-4o"` | Model identifier |
| `PROM_LLM_API_KEY` | `""` | OpenAI API key |
| `PROM_LLM_BASE_URL` | `None` | Override for local models (Ollama, vLLM) |
| `PROM_SEARCH_PROVIDER` | `"duckduckgo"` | `"duckduckgo"` or `"brave"` |
| `PROM_SEARCH_API_KEY` | `""` | Brave Search API key |
| `PROM_SEARCH_MAX_RESULTS` | `20` | Max results per query |
| `PROM_CONVERSATION_WINDOW_SIZE` | `20` | ConversationMemory sliding window |
| `PROM_SEMANTIC_MEMORY_ENABLED` | `true` | Enable SemanticMemory |
| `PROM_MCP_SERVERS` | `[]` | MCP server identifiers |

**Run the servers:**
```bash
uvicorn src.applications.search_agent.main:app --reload
uvicorn src.applications.example_app.main:app --reload
```

---

## 8. Key Files Reference

| File | Purpose | Blast Radius |
|------|---------|-------------|
| `src/core/models/context.py` | Primary input model (frozen) | Critical — every agent/tool/route |
| `src/core/models/results.py` | Primary output models | Critical — every agent/tool/route |
| `src/core/interfaces/agent.py` | Agent contract | Critical — all agents |
| `src/core/interfaces/orchestrator.py` | Strategy Protocol + Orchestrator | High — all strategies, routes |
| `src/core/models/config.py` | Base settings | High — all `*Settings`, factory, auth |
| `src/core/server/factory.py` | App Factory (`create_app`) | High — both app main.py |
| `src/core/middleware/circuit_breaker.py` | Circuit breaker | High — all HTTP tools |
| `src/core/middleware/auth.py` | API key auth | High — all routes |
| `src/core/llm/base.py` | LLM Provider ABC | High — all LLM-using agents |
| `src/core/server/openai_compat/router.py` | `/v1/chat/completions` | Medium — OpenAI API surface |
| `src/core/server/openai_compat/registry.py` | Model registry + StreamableAgent Protocol | Medium |
| `src/core/server/openai_compat/converters.py` | Request/response translation | Medium |
| `src/core/mcp/tool_adapter.py` | MCP → Tool bridge | Medium |
| `src/applications/search_agent/agents/search_pipeline.py` | Composite agent (routes search vs direct) | High within search_agent |
| `src/applications/search_agent/agents/synthesizer.py` | Streaming-capable synthesis | High within search_agent |
| `src/applications/search_agent/streaming_pipeline.py` | OpenAI streaming adapter | Medium |
| `src/applications/search_agent/main.py` | Search app composition root | High within search_agent |
| `src/applications/example_app/main.py` | Example app composition root | High within example_app |
| `tests/conftest.py` | Shared stubs and fixtures | High — all tests |
