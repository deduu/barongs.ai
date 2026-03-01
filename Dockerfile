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
# Install faiss-cpu first (large 23.8 MB wheel, needs generous timeout on slow networks)
RUN pip install --no-cache-dir --timeout=900 --retries=5 faiss-cpu>=1.7.0
RUN pip install --no-cache-dir --timeout=600 --retries=3 ".[rag]"

# ── Stage 3: Final image ────────────────────────────────────
FROM deps AS app

# Non-root user for production safety
RUN groupadd -r barongsai && useradd -r -g barongsai -s /sbin/nologin barongsai

COPY src/ src/
COPY assets/ assets/
COPY --from=frontend /app/frontend/dist/ frontend/dist/

RUN chown -R barongsai:barongsai /app
USER barongsai

EXPOSE 8000

# Tunable via environment
ENV BGS_APP_MODULE=src.applications.search_agent.main:app
ENV BGS_WORKERS=2
ENV BGS_GRACEFUL_TIMEOUT=30
ENV BGS_MAX_REQUESTS=10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["sh", "-c", "python -m uvicorn $BGS_APP_MODULE --host 0.0.0.0 --port 8000 --workers ${BGS_WORKERS} --timeout-graceful-shutdown ${BGS_GRACEFUL_TIMEOUT} --limit-max-requests ${BGS_MAX_REQUESTS}"]
