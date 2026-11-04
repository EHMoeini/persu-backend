# Persu Backend

## Project Overview

Persu Backend is a Django REST Framework API for phone-based authentication and
authenticated user profiles. Users are identified by a normalized E.164 phone
number and can register, log in, refresh sessions, read their profile, and update
their nickname and avatar.

Technologies used:

- Python 3.13
- Django 5.2 LTS
- Django REST Framework 3.16
- Argon2id password hashing
- HS256 access JWTs and opaque, rotating refresh tokens
- SQLite for local development, with PostgreSQL for deployment
- Redis-backed throttling for multi-worker deployments
- Gunicorn and WhiteNoise for production serving
- django-cors-headers for the browser-facing `/api/*` routes

Project layout:

```text
config/                 Django project settings and root URL configuration
apps/accounts/          User model, phone normalization, tokens, auth API
apps/resources/         Authenticated profile API
apps/common/            Health endpoint and shared error handling
Dockerfile              Production image using Gunicorn and WhiteNoise
docker-compose.yml      PostgreSQL, Redis, and web services for test deployment
requirements-prod.txt   Production runtime dependencies
```

## Installation and Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

For local development:

```bash
pip install -r requirements.txt
```

For a production-like deployment, use `requirements-prod.txt` instead. It
includes Gunicorn, PostgreSQL support, and Redis support.

```bash
pip install -r requirements-prod.txt
```

### 3. Configure environment variables

The application ships with production-like test defaults in
`config/settings.py`, so it can start without any environment variables. The
signing keys and database password in that file are test-only placeholders, not
production secrets. Override them with environment variables for any shared
deployment.

Configuration is read from process environment variables. The project does not
load `.env` automatically. `.env.example` lists optional local overrides.

For local development, enable debug mode. Setting explicit secrets is
recommended when your environment is shared:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-value"
$env:AUTH_JWT_SECRET = "replace-with-a-different-long-random-value"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
```

On macOS/Linux, use `export NAME=value` instead.

### 4. Set up the database

SQLite is the default and requires no external service:

```bash
python manage.py migrate
```

To use PostgreSQL, install `requirements-prod.txt` (which includes the driver)
or install the driver directly, then set the database variables:

```bash
pip install "psycopg[binary]"

export DB_ENGINE=postgresql
export DB_NAME=persu
export DB_USER=persu
export DB_PASSWORD=replace-me
export DB_HOST=127.0.0.1
export DB_PORT=5432

python manage.py migrate
```

If `DB_PASSWORD` is omitted, the test-only password from `config/settings.py`
is used. Always set a real password for a shared database.

### 5. Run the development server

```bash
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000`. The liveness endpoint is
`GET /healthz`.

Optional admin account:

```bash
python manage.py createsuperuser
```

### 6. Run checks and tests

```bash
python manage.py check
python manage.py test

pip install -r requirements-test.txt
pytest
```

For a complete local walkthrough of registration, login, token refresh, CORS,
and testing, see [LOCAL_USAGE.md](LOCAL_USAGE.md).

## Production-Ready Test Deployment

The repository includes a production-oriented stack: Gunicorn, WhiteNoise,
PostgreSQL, and Redis. The Docker setup is intended for a test or staging
environment; use HTTPS and a managed database for production.

### Docker Compose

The stack starts with the built-in test defaults:

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`. Check the service and create an
admin account:

```bash
curl http://localhost:8000/healthz
docker compose exec web python manage.py createsuperuser
```

For a shared test deployment, override the defaults with an environment file.
Copy the template, replace every placeholder, and generate independent secrets:

```bash
cp .env.production.example .env.production
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and
`CSRF_TRUSTED_ORIGINS` to the test frontend/API origins, then start the stack:

```bash
docker compose --env-file .env.production up --build
```

When an environment file is used, pass it to the other Compose commands too:

```bash
docker compose --env-file .env.production exec web python manage.py createsuperuser
docker compose --env-file .env.production down
```

The API listens on `http://localhost:8000` by default. Change `WEB_PORT` in
`.env.production` if that port is already in use.

Use `down -v` only when you intentionally want to delete the PostgreSQL volume.

### Non-container deployment

The built-in test defaults work without an environment file. For a shared
deployment, set the environment variables first, then run:

```bash
pip install -r requirements-prod.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Run `python manage.py check --deploy` before exposing the service. With the
plain-HTTP test defaults it reports the expected HTTPS warnings. Terminate TLS
at a trusted reverse proxy or load balancer, then set
`DJANGO_BEHIND_PROXY=true`, `DJANGO_SECURE_SSL_REDIRECT=true`, and
`DJANGO_SECURE_HSTS_SECONDS=31536000`. The `/healthz` endpoint is exempt from
the HTTPS redirect so internal health checks work.

### Environment variables

The values below are the defaults in `config/settings.py`. The committed
signing keys and database password are test-only placeholders; override them
for any shared deployment.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `false` | Production-like default; set `true` for local development. |
| `DJANGO_SECRET_KEY` | Test-only placeholder | Override for shared deployments; use at least 32 random characters. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Comma-separated hostnames accepted by Django. |
| `DJANGO_SECURE_SSL_REDIRECT` | `false` | Redirect HTTP requests to HTTPS; enable once TLS is available. |
| `DJANGO_BEHIND_PROXY` | `false` | Trust `X-Forwarded-Proto` and `X-Forwarded-Host` from a proxy. |
| `DJANGO_SECURE_HSTS_SECONDS` | `0` | HSTS lifetime; set `31536000` behind HTTPS. |
| `DJANGO_SECURE_COOKIES` | Follows SSL redirect | Mark session and CSRF cookies as Secure. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated trusted origins for Django admin and form posts. |
| `AUTH_JWT_SECRET` | Test-only placeholder | Override for shared deployments; must differ from `DJANGO_SECRET_KEY`. |
| `AUTH_JWT_ISSUER` | `http://localhost:8000` | JWT issuer claim. |
| `AUTH_JWT_AUDIENCE` | `http://localhost:3000` | JWT audience claim. |
| `AUTH_ACCESS_TOKEN_TTL_SECONDS` | `900` | Access-token lifetime in seconds. |
| `AUTH_REFRESH_TOKEN_TTL_SECONDS` | `2592000` | Refresh-token lifetime in seconds (30 days). |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated browser origins allowed for `/api/*`. |
| `DB_ENGINE` | `sqlite` | Use `postgresql` for PostgreSQL. |
| `SQLITE_PATH` | `db.sqlite3` | SQLite database path when using SQLite. |
| `DB_NAME` | `persu` | PostgreSQL database name. |
| `DB_USER` | `persu` | PostgreSQL user. |
| `DB_PASSWORD` | Test-only placeholder | Override for shared or production databases. |
| `DB_HOST` | `127.0.0.1` | PostgreSQL host. |
| `DB_PORT` | `5432` | PostgreSQL port. |
| `DB_CONN_MAX_AGE` | `60` | Persistent database connection lifetime in seconds. |
| `REDIS_URL` | Empty (local memory) | Redis URL for shared throttling cache, for example `redis://redis:6379/1`. |
| `DJANGO_LOG_LEVEL` | `INFO` | Application and Django log level. |
| `WEB_PORT` | `8000` | Host port published by Docker Compose. |
| `GUNICORN_WORKERS` | `3` | Gunicorn worker count in the container. |
| `GUNICORN_TIMEOUT` | `60` | Gunicorn request timeout in seconds. |

## API Endpoints

Paths are exact and have no trailing slash. `/admin/` is the Django admin HTML
interface and is not part of the JSON API.

| Method | Endpoint | Description | Authentication |
| --- | --- | --- | --- |
| GET | `/healthz` | Liveness check; returns `{"status": "ok"}`. | None |
| POST | `/auth/check` | Checks whether a phone number is registered; returns `{"exists": true}` or `{"exists": false}`. | None; throttled at 10/min per normalized phone. |
| POST | `/auth/login` | Authenticates a phone number and password; returns an access token, refresh token, and user. | None; throttled at 5/min per normalized phone. |
| POST | `/auth/register` | Creates a user; returns `201` with an access token, refresh token, and user. | None; throttled at 5/min per normalized phone. |
| POST | `/auth/refresh` | Rotates a refresh token; returns a new access token and refresh token. | None; requires `refreshToken` in the body; throttled at 20/min per token. |
| POST | `/auth/logout` | Revokes the refresh-token family; returns `204` with an empty body. | None; requires `refreshToken` in the body; idempotent; throttled at 30/min per token. |
| GET | `/auth/session` | Returns the authenticated user. | Bearer access token; active user required. |
| POST | `/auth/otp/send` | OTP send stub; returns `{"success": true}` without sending an SMS. | None; throttled at 5/min per normalized phone. |
| POST | `/auth/otp/verify` | OTP verify stub; accepts any or absent code and returns `{"success": true}`. | None; throttled at 10/min per normalized phone. |
| GET | `/api/me` | Returns the authenticated user's profile. | Bearer access token; active user required; CORS enabled. |
| PATCH | `/api/me` | Updates `nickName` and/or `avatar`; returns the updated user. | Bearer access token; active user required; CORS enabled. |

### Request fields

Phone-based endpoints are `POST /auth/check`, `/auth/login`, `/auth/register`,
`/auth/otp/send`, and `/auth/otp/verify`.

| Field | Required | Rules |
| --- | --- | --- |
| `countryCode` | Yes | String, max 8. ISO country code such as `US`, or a dialing code such as `+1`. |
| `phone` | Yes | String, max 32. Normalized to E.164 before lookup or storage. |
| `password` | Login and register | String, max 128; whitespace-only values are rejected. |
| `code` | OTP verify only | Optional string, max 16; currently ignored by the stub. |

Token endpoints (`/auth/refresh` and `/auth/logout`) require:

| Field | Required | Rules |
| --- | --- | --- |
| `refreshToken` | Yes | String, max 512; whitespace-only values are rejected. |

`PATCH /api/me` accepts only these writable fields:

| Field | Required | Rules |
| --- | --- | --- |
| `nickName` | No | String, max 64; an empty string clears it. |
| `avatar` | No | URL string, max 500; an empty string clears it. |

Identity, phone, and password fields are read-only for this endpoint. Sending
`{}` is a valid no-op.

### Responses

Login and registration return:

```json
{
  "accessToken": "<access token>",
  "refreshToken": "<refresh token>",
  "user": {
    "id": "<uuid>",
    "phone": "+12024561111"
  }
}
```

`/auth/refresh` returns `accessToken` and `refreshToken` without `user`.
`/auth/session` and `/api/me` return `{"user": ...}`. The user object contains
`id`, `phone`, and, when set, `nickName` and `avatar`; empty optional fields are
omitted.

`/auth/logout` returns `204` with no body. The OTP stubs return
`{"success": true}`. Unknown paths return `404`.

### Status codes

| Status | Meaning |
| --- | --- |
| 200 | Successful read, login, refresh, check, update, or OTP stub response. |
| 201 | Successful registration. |
| 204 | Successful logout. |
| 400 | Invalid request data (`validation_error`) or malformed JSON (`invalid_json`). |
| 401 | Missing or invalid access token, invalid login credentials, or invalid/expired refresh token. |
| 404 | Unknown route (`not_found`). |
| 405 | HTTP method not allowed for the route. |
| 409 | Phone number already registered (`phone_already_registered`). |
| 415 | Unsupported request media type. |
| 429 | Rate limit exceeded (`rate_limited`). |
| 500 | Unhandled server error (`internal_error`). |

Errors use a consistent envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request data."
  }
}
```

## Authentication and Authorization

The API uses Bearer access JWTs. Send the token in the request header:

```http
Authorization: Bearer <access token>
```

- Access tokens are HS256 JWTs with a default lifetime of 15 minutes.
- Refresh tokens are opaque values with a default lifetime of 30 days. Only
  their SHA-256 hashes are stored, and each successful refresh rotates the
  token.
- Login and registration create a new refresh-token family and revoke the
  user's previous refresh tokens. Presenting a revoked or reused refresh token
  revokes the whole family.
- Logout revokes the refresh-token family. Access tokens are stateless and
  remain valid until they expire, even after logout.
- `/auth/session`, `GET /api/me`, and `PATCH /api/me` require a valid Bearer
  access token for an active user.
- Public endpoints explicitly allow anonymous access. Auth endpoints are
  intended for server-to-server calls and do not emit CORS headers.
- CORS is enabled only for `/api/*`. The default allowed origins are
  `http://localhost:3000` and `http://127.0.0.1:3000`; change them with
  `CORS_ALLOWED_ORIGINS`.
- There are no role-specific API permissions. Any active authenticated user can
  read and update only their own profile.
- Missing, expired, malformed, or wrong-type tokens return `401` with an
  `unauthorized` error code.

## Git Workflow

The repository uses four branch types:

- `main`: production-ready code. It is updated only by intentional releases
  from `develop`.
- `develop`: integration branch for ongoing development.
- `feature/*`: individual features or development tasks, created from
  `develop` and merged back into `develop`.
- `fix/*`: bug fixes, created from `develop` and merged back into `develop`.
  A production hotfix may be branched from `main` and merged back into both
  `main` and `develop`.

Do not commit development work directly to `main`. Create a feature or fix
branch and merge it into `develop` through a pull request or a reviewed local
merge.

Start a new feature:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c feature/my-feature
```

Make changes, then commit and push:

```bash
git add .
git commit -m "feat: describe the change"
git push -u origin feature/my-feature
```

Merge completed work into `develop`:

```bash
git switch develop
git pull --ff-only origin develop
git merge --no-ff feature/my-feature
git push origin develop
```

Start a bug fix the same way:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c fix/my-bug
```

Publish a release by merging `develop` into `main`:

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff develop
git push origin main
```

After a branch is merged, keep it until it is no longer needed; branch cleanup is
a separate, explicit decision.
