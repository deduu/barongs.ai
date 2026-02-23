# Core Library Rules

## This Directory
Contains the shared framework: interfaces (ABCs), Pydantic models,
orchestrator engine + strategies, middleware, and the FastAPI server layer.

## Key Principles
- Everything here is GENERIC. No application-specific logic.
- Interfaces use ABC for agents/tools/memory, Protocol for strategies.
- All models use Pydantic v2 with `model_config` (not old Config class).
- Frozen models for immutable data (AgentContext).

## Adding a New Interface
1. Write tests in tests/core/test_interfaces.py FIRST
2. Define ABC in src/core/interfaces/
3. Export from src/core/interfaces/__init__.py
4. Update src/core/__init__.py public API

## Adding a New Strategy
1. Write tests in tests/core/test_orchestrator.py FIRST
2. Create file in src/core/orchestrator/strategies/
3. Strategy must satisfy OrchestratorStrategy Protocol
4. Export from strategies/__init__.py
