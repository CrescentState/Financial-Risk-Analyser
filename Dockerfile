# Multi-stage Dockerfile for Financial Risk Analyser
# --- Stage 1: Build Frontend (React) ---
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build


# --- Stage 2: Python Build ---
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and build virtual environment
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev


# --- Stage 3: Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies & create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /bin/bash appuser

# Copy virtual environment from python-builder
COPY --from=python-builder /app/.venv /app/.venv

# Copy built React static files from frontend-builder
COPY --from=frontend-builder /app/static ./static

# Copy application files (only needed files)
COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser core/ ./core/
COPY --chown=appuser:appuser agents/ ./agents/
COPY --chown=appuser:appuser .env.example ./

# Create cache directory with correct ownership
RUN mkdir -p /app/cache && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Set virtual environment path
ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Dynamic Health Check using PORT env
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Shell-form CMD to allow environment variable expansion ($PORT)
CMD exec gunicorn main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info