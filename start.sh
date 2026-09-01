#!/bin/bash
# Render startup script for backend

set -e

echo "Starting Financial Risk Analyser API..."

# Ensure cache directory exists
mkdir -p /app/cache

# Run database migrations if needed (placeholder for future)
# python -m alembic upgrade head

# Start the application
exec gunicorn main:app \
    --workers ${WORKERS:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout ${TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info}