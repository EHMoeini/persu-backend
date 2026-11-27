# Deploying on Render

This project is ready to run as a minimal prototype on Render's free plan.

## Option A: Dashboard (manual)

Use these values in the Render "New Web Service" form:

| Field | Value |
| --- | --- |
| Language | Python 3 |
| Branch | `main` (or whichever branch has these changes) |
| Build Command | `bash build.sh` |
| Pre-Deploy Command | `python manage.py migrate --noinput` |
| Start Command | `bash start.sh` |
| Health Check Path | `/healthz` |

Add these environment variables (Settings → Environment):

| Key | Value |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `AUTH_JWT_SECRET` | generate a **different** value the same way |
| `DJANGO_BEHIND_PROXY` | `true` |
| `CORS_ALLOWED_ORIGINS` | comma-separated frontend origins, for example `https://your-frontend.example.com` |
| `AUTH_OTP_MOCK_CODE` | `123456` (optional; the mock code accepted by `/auth/otp/verify`) |

`CORS_ALLOWED_ORIGINS` enables browser calls to both `/api/*` and `/auth/*`.
The defaults allow only `http://localhost:3000` and `http://127.0.0.1:3000`, so
set your deployed frontend origin here or the browser will block the responses.
The allowed request headers include `Authorization`, `Content-Type`,
`X-App-Version`, `x-platform`, `X-Client-Locale`, and `x-seconds-from-utc`.

`DJANGO_SECRET_KEY` and `AUTH_JWT_SECRET` must both be set, and must differ.
If you omit both, the non-production defaults in `config/settings.py` are used;
that works for a throwaway prototype but is not safe for public use.

The Python version is pinned in `.python-version`. `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS` automatically include the service's
`*.onrender.com` hostname. If you attach a custom domain, also set:

```
DJANGO_ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

## Option B: Blueprint

`render.yaml` at the repository root defines the same web service, including
auto-generated secrets. In the Render dashboard choose **New → Blueprint** and
point it at this repository.

## Database

By default the service uses SQLite (`db.sqlite3`). This is fine for a
prototype, but Render's free instances have an ephemeral filesystem: data is
lost on every deploy/restart. On startup, `start.sh` applies pending migrations
and seeds the mock facility listings only when the `facilities` table is empty,
so a fresh prototype instance still has searchable data. If any real facility
exists, the mock seed is skipped.

To persist data, create a Render PostgreSQL instance and set the web service's
`DATABASE_URL` to the database's **Internal Database URL**. The settings file
parses it automatically:

```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

PostgreSQL requires `psycopg`, which is already included in
`requirements-prod.txt` (installed by `build.sh`).

## What the scripts do

- `build.sh` installs production dependencies and runs `collectstatic`.
- `python manage.py migrate --noinput` (Pre-Deploy Command) applies database migrations before the new version goes live. This remains the recommended step for zero-downtime deploys.
- `start.sh` applies any pending migrations, seeds mock listings only if the database is empty, then starts Gunicorn on `$PORT`. The migration and seed steps are idempotent, so running them after the Pre-Deploy Command is safe.

`requirements-prod.txt` is an alias for `requirements.txt`, which includes
Gunicorn, PostgreSQL, and Redis. A default Render build that only runs
`pip install -r requirements.txt` therefore installs everything the app needs.

To run the same setup locally (Linux/macOS/Git Bash):

```bash
bash build.sh
PORT=8000 bash start.sh
```
