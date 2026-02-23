# Pormetheus

Production-ready Python AI agent framework with async-first design, enterprise middleware, and modular architecture.

## Features

- **Agent Framework** — Abstract base classes for Agent, Tool, Memory with a Strategy-pattern Orchestrator
- **Async-First** — Built on FastAPI + httpx + asyncio, no blocking calls anywhere
- **Enterprise Middleware** — Circuit breakers, rate limiting, API key auth, structured logging (structlog), timeouts
- **LLM Provider Agnostic** — OpenAI, OpenAI-compatible (Ollama, vLLM, Azure), HuggingFace local models
- **OpenAI-Compatible API** — `/v1/chat/completions` endpoint works with Open WebUI and other OpenAI clients
- **MCP Integration** — Model Context Protocol client with automatic tool adaptation
- **Streaming** — Server-Sent Events (SSE) for real-time token streaming
- **Orchestration Strategies** — SingleAgent, Router, Pipeline, Parallel, swappable at runtime
- **Docker-Ready** — Multi-stage Dockerfile included

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

```bash
git clone https://github.com/deduu/prometheus.git
cd prometheus

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# For local HuggingFace models (requires GPU)
pip install -e ".[local]"
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your settings (API keys, etc.)
```

### Run the Example App

```bash
uvicorn src.applications.example_app.main:app --reload --port 8000
```

### Run the Search Agent

```bash
# Set your LLM API key in .env, then:
uvicorn src.applications.search_agent.main:app --reload --port 8000
```

The search agent exposes:

| Endpoint | Description |
|----------|-------------|
| `POST /api/search` | Search with web research and cited synthesis |
| `POST /api/search/stream` | Streaming search with SSE |
| `POST /v1/chat/completions` | OpenAI-compatible API (works with Open WebUI) |
| `GET /health` | Health check |

## Docker

### Run with Docker Compose

```bash
cp .env.example .env
# Edit .env — set at minimum: PROM_LLM_API_KEY

docker compose up --build
```

The search agent will be available at `http://localhost:8000`.

To run the example app instead, set `PROM_APP_MODULE` in your `.env`:

```
PROM_APP_MODULE=src.applications.example_app.main:app
```

### Run with Open WebUI (Full Stack)

A pre-configured compose file starts the full stack — Pormetheus, [Open WebUI](https://github.com/open-webui/open-webui), PostgreSQL, and Redis — in one command:

```bash
cp .env.example .env
# Edit .env — set at minimum: PROM_LLM_API_KEY

docker compose -f docker-compose.openwebui.yml up --build
```

| Service | URL | Purpose |
|---------|-----|---------|
| Open WebUI | `http://localhost:3000` | Chat interface |
| Pormetheus API | `http://localhost:8000` | Search agent backend |
| PostgreSQL | `localhost:5432` | Persistent storage (Open WebUI + Pormetheus) |
| Redis | `localhost:6379` | Caching layer |

Open WebUI is pre-configured to connect to Pormetheus as its OpenAI-compatible backend. Once all containers are healthy, open `http://localhost:3000` and start chatting — queries go through the search agent pipeline (web research + synthesis with citations).

You can customize the database credentials in your `.env`:

```
POSTGRES_USER=pormetheus
POSTGRES_PASSWORD=pormetheus
POSTGRES_DB=pormetheus
```

### Setting up Open WebUI manually

If you already have Open WebUI running or prefer to configure it yourself:

1. **Start Pormetheus** (locally or via Docker):
   ```bash
   # Local
   uvicorn src.applications.search_agent.main:app --host 0.0.0.0 --port 8000

   # Or Docker
   docker compose up --build
   ```

2. **Open the Open WebUI admin panel** — go to **Settings > Connections**.

3. **Add an OpenAI connection**:
   - **API Base URL**: `http://localhost:8000/v1` (or `http://pormetheus:8000/v1` if both run in Docker)
   - **API Key**: the value of `PROM_API_KEY` from your `.env` (default: `changeme`)

4. **Verify**: Click the refresh button next to the URL field. You should see the model listed (e.g., `gpt-4o` or whatever you set `PROM_LLM_MODEL` to).

5. **Start chatting**: Select the model in the chat interface. Search queries will trigger web research; direct questions get answered immediately.

> **Note**: If `PROM_OPENAI_AUTH_ENABLED` is `false` (default), the API key field in Open WebUI can be any non-empty string. Set it to `true` in your `.env` and use your actual `PROM_API_KEY` to require authentication.

### OpenAI-Compatible API Reference

The search agent exposes a standard OpenAI-compatible API at `/v1`:

```bash
# List available models
curl http://localhost:8000/v1/models

# Chat completion (non-streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "What is FastAPI?"}]
  }'

# Chat completion (streaming)
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "What is FastAPI?"}],
    "stream": true
  }'
```

The `model` field should match `PROM_LLM_MODEL` (default: `gpt-4o`). Check `GET /v1/models` to see what's registered.

## Architecture

```
[HTTP Client / Open WebUI]
         |
    [FastAPI App]  ── created by create_app()
         |
    [Orchestrator] ── asyncio.wait_for(timeout=30s)
         |
  [Strategy: Single | Router | Pipeline | Parallel]
         |
    [Agent(s)]     ── frozen AgentContext in, AgentResult out
         |
    [Tool(s)]      ── external I/O with circuit breakers
```

- `src/core/` — Generic framework library (interfaces, models, orchestrator, server, middleware)
- `src/applications/` — Concrete apps built on the core framework
- Dependencies are unidirectional: `applications -> core`, never `core -> applications`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full documentation.

## Applications

### Example App

Minimal reference app demonstrating framework wiring with an `EchoAgent`. Use as a template for new applications.

### Search Agent

Perplexity-style search chatbot with:

- **Query Analysis** — Classifies queries as search vs. direct answer
- **Web Research** — Parallel search via DuckDuckGo (free) or Brave (API key), content fetching, URL validation
- **Synthesis** — LLM-powered answer generation with clickable markdown citations
- **Streaming** — Real-time token streaming via SSE
- **OpenAI API** — Drop-in replacement for OpenAI chat completions

## Development

```bash
make test       # Run tests with coverage
make lint       # Lint with ruff
make typecheck  # Type check with mypy
make format     # Auto-format code
make check      # Run all checks (lint + typecheck + test)
```

### Project Rules

- All I/O must be async
- Pydantic validation on all inputs
- Circuit breakers on all external API calls
- TDD: write tests before implementation

See [CLAUDE.md](CLAUDE.md) for complete development rules.

## License

[MIT](LICENSE)
