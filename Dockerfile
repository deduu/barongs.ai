# Multi-stage build for production
FROM python:3.11-slim AS base
WORKDIR /app

FROM base AS deps
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM deps AS app
COPY src/ src/
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.applications.example_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
