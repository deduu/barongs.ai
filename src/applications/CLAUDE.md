# Applications Directory Rules

## Structure
Each subdirectory is a standalone application that imports from src.core.

## Creating a New Application
1. Create directory: src/applications/{app_name}/
2. Required files:
   - __init__.py
   - config.py (extends AppSettings)
   - main.py (create_app + uvicorn runner)
   - routes.py (FastAPI router)
   - agents/ (at least one agent)
   - tools/ (optional)
3. Create matching test directory: tests/applications/{app_name}/
4. Write tests FIRST, then implement.
