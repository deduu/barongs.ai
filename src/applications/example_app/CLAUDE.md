# Example App Rules

## Purpose
Reference application demonstrating how to build on the pormetheus core framework.
Use this as a template when creating new applications.

## Structure
- config.py: ExampleAppSettings extends AppSettings
- main.py: Composition root — wires agents, tools, memory, orchestrator
- routes.py: FastAPI router with app-specific endpoints
- agents/: Concrete agent implementations
- tools/: Concrete tool implementations
- memory/: Memory backend implementations
- lambda_handler.py: AWS Lambda entry point via Mangum
