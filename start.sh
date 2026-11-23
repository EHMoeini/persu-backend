#!/usr/bin/env bash
# Start step: run Gunicorn.
# Database migrations are executed separately via pre-deployment commands.
set -o errexit

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-${GUNICORN_WORKERS:-2}}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
