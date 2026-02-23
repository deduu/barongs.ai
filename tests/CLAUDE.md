# Testing Rules

## Framework
- pytest + pytest-asyncio (auto mode)
- All async tests: just use `async def test_...` — no decorator needed

## Structure
- tests/conftest.py: shared fixtures (StubAgent, StubTool, StubMemory, etc.)
- tests/core/: tests for the framework library
- tests/applications/: tests for specific applications

## Rules
1. Tests MUST be written BEFORE implementation (TDD).
2. Use fixtures from conftest.py — do not duplicate stubs.
3. Mock external I/O (httpx calls, LLM APIs) — never hit real services.
4. Each test file maps to one source file.
5. Async tests: just use `async def` — asyncio_mode = "auto" handles it.
