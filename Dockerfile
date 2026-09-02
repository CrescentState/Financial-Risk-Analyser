# Multi-stage Dockerfile for Financial Risk Analyser
# Build with: docker build -t financial-risk-analyser .
# Context: project root (where this Dockerfile lives)

# =============================================================================
# Stage 1: Build Frontend (React + Vite)
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files from frontend directory
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./frontend/

# Build frontend - Vite outputs to /app/static (per vite.config.ts outDir: '../static')
WORKDIR /app/frontend
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build


# =============================================================================
# Stage 2: Python Dependencies
# =============================================================================
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev


# =============================================================================
# Stage 3: Runtime
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies & create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from python-builder
COPY --from=python-builder /app/.venv /app/.venv

# Copy built React static files from frontend-builder (Vite outputs to /app/static)
COPY --from=frontend-builder /app/static ./static

# Copy application source code
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser core/ ./core/
COPY --chown=appuser:appuser agents/ ./agents/
COPY --chown=appuser:appuser .env.example ./

# Create cache directory
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start server
CMD exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info