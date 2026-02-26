# Pormetheus — Development Rules

## Project Overview
Pormetheus is a production-ready Python AI agent framework. It provides
ABCs/Protocols for Agent, Tool, Memory, and Orchestrator, with a strategy
pattern for orchestration and a modular application structure.

## Tech Stack
- Python 3.11+, FastAPI, Pydantic v2, asyncio, httpx
- Testing: pytest + pytest-asyncio
- Linting: ruff | Type checking: mypy (strict mode)

## Commands
- `py -m pytest` — run all tests
- `py -m pytest tests/core/` — run core tests only
- `py -m pytest -x -q` — stop on first failure, quiet output
- `py -m ruff check src/ tests/` — lint
- `py -m ruff format src/ tests/` — format
- `py -m mypy src/` — type check
- `make test` / `make lint` / `make typecheck` — shortcuts

## Production Rules (MANDATORY)
1. **All I/O must be async.** No blocking calls. Use httpx, not requests.
2. **Pydantic validation on ALL inputs.** Every endpoint, every agent context,
   every tool input uses a Pydantic model.
3. **Authentication via FastAPI dependencies.** Never inline auth checks.
4. **Rate limiting** on all public endpoints.
5. **CORS** configured per-environment (never wildcard in production).
6. **Structured logging** via structlog. JSON format in production.
7. **Circuit breakers** for every external API call (LLM providers, HTTP tools).
8. **Timeout limits** on all agent/tool calls. Default 30s agents, 15s tools.
9. **NEVER log sensitive data.** Use src/core/utils/sanitize.py for redaction.

## Development Workflow (MANDATORY)
1. **TDD: Write tests BEFORE implementation** for agents, tools, orchestrator.
   - Test file must exist and have failing tests before the implementation file.
2. **Plan mode by default.** Enter plan mode for ANY non-trivial task (3+ steps
   or architectural decisions). If something goes sideways, STOP and re-plan.
3. **Use TodoWrite** for task decomposition on complex features.

## Workflow Orchestration
- **Subagent Strategy**: Use subagents liberally — offload research, exploration,
  and parallel analysis. One task per subagent for focused execution.
- **Self-Improvement Loop**: After ANY correction, update `tasks/lessons.md`
  with the pattern. Write rules that prevent the same mistake. Review lessons
  at session start.
- **Verification Before Done**: Never mark a task complete without proving it
  works. Run tests, check logs. Ask: "Would a staff engineer approve this?"
- **Demand Elegance**: For non-trivial changes, pause and ask "is there a more
  elegant way?" Skip this for simple, obvious fixes — don't over-engineer.
- **Autonomous Bug Fixing**: When given a bug report, just fix it. Point at
  logs/errors/failing tests, then resolve. Zero hand-holding required.

## Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior dev standards.
- **Minimal Impact**: Only touch what's necessary. Avoid introducing bugs.

## Architecture
- `src/core/` — Framework library (interfaces, models, orchestrator, server)
- `src/applications/` — Specific apps built on core
- Each application imports from core, defines its own agents/tools/config
- Orchestrator uses Strategy pattern: SingleAgent, Router, Pipeline, Parallel
- FastAPI uses App Factory pattern (create_app in src/core/server/factory.py)
- Agents NEVER call other agents directly — always go through the Orchestrator
- Tools NEVER access memory directly — memory is injected via AgentContext
- All external I/O goes through the tools layer, never directly in agents
- Dependencies are unidirectional: applications → core, never core → applications

## Code Style
- Absolute imports from `src.` prefix
- Type annotations on all public functions
- `from __future__ import annotations` at top of every file

## Meta
If this file exceeds 100 lines, split into per-directory CLAUDE.md files.
If any rule conflicts with the current codebase patterns, flag it.
