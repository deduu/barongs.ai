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
