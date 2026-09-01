# Multi-stage Dockerfile for Financial Risk Analyser

# --- Build stage ---
    FROM python:3.11-slim AS builder

    WORKDIR /app
    
    # Install uv
    RUN pip install --no-cache-dir uv
    
    # Install build dependencies
    RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        && rm -rf /var/lib/apt/lists/*
    
    # Copy dependency files and build virtual environment
    COPY pyproject.toml uv.lock ./
    RUN uv sync --frozen --no-cache
    
    
    # --- Runtime stage ---
    FROM python:3.11-slim AS runtime
    
    WORKDIR /app
    
    # Install runtime dependencies & create non-root user
    RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        && rm -rf /var/lib/apt/lists/* && \
        useradd --create-home --shell /bin/bash appuser
    
    # Copy virtual environment from builder
    COPY --from=builder /app/.venv /app/.venv
    
    # Copy application files
    COPY --chown=appuser:appuser . .
    
    # Create cache directory with correct ownership
    RUN mkdir -p /app/cache && chown -R appuser:appuser /app
    
    USER appuser
    
    # Expose fallback port
    EXPOSE 8000
    
    # Set virtual environment path
    ENV PATH="/app/.venv/bin:$PATH"
    ENV PORT=8000
    
    # Dynamic Health Check using default or passed PORT env
    HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
        CMD curl -f http://localhost:${PORT}/health || exit 1
    
    # Shell-form CMD to allow environment variable expansion ($PORT)
    CMD exec gunicorn main:app \
        --workers 2 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:${PORT} \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -