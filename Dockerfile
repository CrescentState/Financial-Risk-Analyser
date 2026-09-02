# Multi-stage Dockerfile for Financial Risk Analyser

# =============================================================================
# Stage 1: Build Frontend (React + Vite)
# =============================================================================
FROM node:20-alpine AS frontend-builder

# Set working directory directly inside frontend
WORKDIR /app/frontend

# Copy package files from frontend directory
COPY frontend/package*.json ./

# Install dependencies cleanly
RUN npm ci

# Copy full frontend directory context
COPY frontend/ ./

# Build production bundle (outputs to /app/frontend/dist)
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build


# =============================================================================
# Stage 2: Python Dependencies
# =============================================================================
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications and generate virtualenv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev


# =============================================================================
# Stage 3: Runtime Environment
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime utilities & configure appuser
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash appuser

# Copy virtualenv from python-builder stage
COPY --from=python-builder /app/.venv /app/.venv

# Copy compiled React static bundle into /app/static for FastAPI to serve
COPY --from=frontend-builder /app/frontend/dist ./static

# Copy FastAPI application source code
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser core/ ./core/
COPY --chown=appuser:appuser agents/ ./agents/
COPY --chown=appuser:appuser .env.example ./

# Allocate runtime cache permissions
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info