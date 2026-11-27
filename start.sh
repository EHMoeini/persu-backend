#!/bin/sh
# Start step: apply pending migrations, seed mock listings only when the
# facilities table is empty, then run Gunicorn.
set -eu

python manage.py migrate --noinput
python manage.py seed_facilities --if-empty

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-${GUNICORN_WORKERS:-2}}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
