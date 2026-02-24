# Multi-stage build for production
FROM python:3.11-slim AS base
WORKDIR /app

FROM base AS deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM deps AS app
COPY src/ src/
EXPOSE 8000

# Default: search agent. Override with BGS_APP_MODULE env var.
ENV BGS_APP_MODULE=src.applications.search_agent.main:app
CMD ["sh", "-c", "python -m uvicorn $BGS_APP_MODULE --host 0.0.0.0 --port 8000"]
