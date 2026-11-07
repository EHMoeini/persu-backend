FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home \
        --shell /usr/sbin/nologin app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-prod.txt

COPY --chown=app:app . .

# Build-time secrets are placeholders; runtime values are supplied by the environment.
RUN DJANGO_DEBUG=false \
    DJANGO_SECRET_KEY=build-only-secret-key-0123456789abcdefghijklmnopqrstuvwxyz \
    AUTH_JWT_SECRET=build-only-jwt-secret-0123456789abcdefghijklmnopqrstuvwxyz \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5)"

# Apply migrations before starting Gunicorn. The Dockerfile is also used
# directly (outside docker-compose), so it must not assume an external entrypoint
# already ran `migrate`.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60} --access-logfile - --error-logfile -"]
