.PHONY: test lint typecheck format run install check

install:
	pip install -e ".[dev]"

test:
	py -m pytest -x -q --cov=src --cov-report=term-missing

lint:
	py -m ruff check src/ tests/

format:
	py -m ruff format src/ tests/

typecheck:
	py -m mypy src/

run:
	py -m uvicorn src.applications.example_app.main:app --reload --port 8000

check: lint typecheck test
