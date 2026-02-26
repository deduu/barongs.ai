# ── Stage 1: Build frontend ──────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python dependencies ─────────────────────────────
FROM python:3.11-slim AS base
WORKDIR /app

FROM base AS deps
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[rag]"

# ── Stage 3: Final image ────────────────────────────────────
FROM deps AS app
COPY src/ src/
COPY assets/ assets/
COPY --from=frontend /app/frontend/dist/ frontend/dist/
EXPOSE 8000

# Default: search agent. Override with BGS_APP_MODULE env var.
ENV BGS_APP_MODULE=src.applications.search_agent.main:app
CMD ["sh", "-c", "python -m uvicorn $BGS_APP_MODULE --host 0.0.0.0 --port 8000"]
