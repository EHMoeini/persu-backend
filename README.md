# Persu Backend

Django + Django REST Framework backend for phone-based authentication and
authenticated resource APIs.

## Stack

- Python 3.13
- Django 5.2 LTS
- Django REST Framework
- Argon2id password hashing
- HS256 access JWTs + opaque rotating refresh tokens
- SQLite for local development (PostgreSQL supported through environment settings)

## Project layout

```text
config/                 Django project configuration
apps/common/            Shared API errors and health endpoint
apps/accounts/          User model, phone normalization, tokens, auth API, tests
apps/resources/         Authenticated browser-facing resource API, tests
```

## Local setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DJANGO_SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(64))")
$env:AUTH_JWT_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(64))")

python manage.py migrate
python manage.py runserver
```

Settings are read directly from process environment variables. `.env.example`
documents the supported variables; export them in your shell or inject them
through your deployment platform.

Run checks and tests:

```powershell
python manage.py check
python manage.py test
```

The liveness endpoint is `GET /healthz`.

For a full local walkthrough, including the auth flow, CORS checks, and test
commands, see [LOCAL_USAGE.md](LOCAL_USAGE.md).

## Configuration

All secrets and deployment settings come from process environment variables.
See `.env.example` for the full list. Production refuses to start without
`DJANGO_SECRET_KEY` and `AUTH_JWT_SECRET` when `DJANGO_DEBUG=false`; both must
be at least 32 characters.

PostgreSQL is selected with `DB_ENGINE=postgresql` plus the `DB_*` variables.
Install a PostgreSQL driver (`psycopg[binary]`) when using it.

## Token design

- **Access token**: HS256 JWT, 15-minute lifetime, claims `sub`, `typ`, `iss`,
  `aud`, `iat`, `exp`, `jti`. Signature, expiry, issuer, audience, type, and
  required claims are validated on every request.
- **Refresh token**: opaque 32-byte base64url value, 30-day sliding lifetime.
  Only its SHA-256 hash is stored. Each refresh rotates the token within the
  same family and links the old row through `replaced_by`.
- **Reuse detection**: presenting a revoked or already-rotated refresh token
  revokes the entire family and returns 401.
- **One session per user**: login/register revoke all existing refresh tokens
  before creating a new family. The user row is locked to serialize concurrent
  logins.
- **Atomicity**: rotation and family revocation use `transaction.atomic()` and
  `select_for_update()` row locks.
- **Stateless access**: logout and a second login revoke refresh tokens
  immediately, but already-issued access tokens remain valid until they expire
  (at most 15 minutes).

DRF uses `apps.accounts.authentication.BearerAuthentication` by default and
`apps.accounts.permissions.IsAuthenticatedUser` for protected views. The
health endpoint explicitly opts out.

## Auth API

All auth routes are server-to-server, unauthenticated (except session), and
excluded from CORS.

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| POST | `/auth/check` | 200 `{exists}` | Normalizes phone first |
| POST | `/auth/login` | 200 `{accessToken, refreshToken, user}` | Generic 401 on failure |
| POST | `/auth/register` | 201 `{accessToken, refreshToken, user}` | 409 if phone exists |
| POST | `/auth/refresh` | 200 `{accessToken, refreshToken}` | Rotates; reuse revokes family |
| POST | `/auth/logout` | 204 | Idempotent family revocation |
| GET | `/auth/session` | 200 `{user}` | Requires Bearer access token |
| POST | `/auth/otp/send` | 200 `{success: true}` | Stub |
| POST | `/auth/otp/verify` | 200 `{success: true}` | Stub; ignores code |

Request bodies use `countryCode`, `phone`, `password`, and `refreshToken`.
Successful login/register responses include the public user shape:

```json
{
  "accessToken": "...",
  "refreshToken": "...",
  "user": {
    "id": "uuid",
    "phone": "+12024561111"
  }
}
```

`nickName` and `avatar` are included when set.

### Rate limits

Auth throttling is scoped to the normalized phone (or refresh token) rather
than the calling IP, because the Next server calls these routes server-to-server
and all users can share one IP. Invalid phone numbers fall back to the caller IP
so random invalid inputs cannot create unlimited buckets. Limits are configured
in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.

Django's default local-memory cache is used for local development. For a
multi-process production deployment, configure a shared Django cache (for
example Redis) so throttling is enforced globally, and consider IP-level limits
at the edge as an additional layer.

## Resource API

Browser-facing routes live under `/api/*` and require a Bearer access token.
They are also the only routes with CORS enabled.

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| GET | `/api/me` | 200 `{user}` | Current user from the access token |
| PATCH | `/api/me` | 200 `{user}` | Updates `nickName` and/or `avatar` |

`PATCH` accepts only `nickName` and `avatar`; identity and phone fields are
read-only. Sending an empty string clears an optional field. Invalid avatar
URLs return a `validation_error`, and missing/expired tokens return 401.

Example:

```http
GET /api/me HTTP/1.1
Host: api.example.com
Authorization: Bearer <access token>
Origin: https://app.example.com
```

### CORS

CORS is restricted to `/api/*`; `/auth/*` never emits CORS headers because
those routes are server-to-server.

- Allowed origin: `https://app.example.com` (override with
  `CORS_ALLOWED_ORIGINS`, comma-separated)
- Allowed headers: `Authorization` and `Content-Type` only
- Allowed methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- Credentials: disabled (`CORS_ALLOW_CREDENTIALS = False`)
- Preflight requests are answered without requiring an access token
- CORS headers are present on authenticated responses, 401s, validation
  errors, and 404s under `/api/`

## API conventions

- Successful responses use JSON with camelCase fields where required by the
  client contract.
- Every error uses a consistent envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid request data."
  }
}
```

- Auth routes live under `/auth/*` and are server-to-server.
- Browser-facing resource routes live under `/api/*` and use Bearer access
  tokens.
- CORS is enabled only for `/api/*`, never for `/auth/*`.
- Unknown routes and unhandled server errors also use this envelope (JSON
  404/500 handlers).

## Deployment checklist

- Set `DJANGO_DEBUG=false`.
- Set independent `DJANGO_SECRET_KEY` and `AUTH_JWT_SECRET` values.
- Set `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
- Serve over HTTPS and keep `DJANGO_SECURE_SSL_REDIRECT` and HSTS enabled.
- Set `DJANGO_BEHIND_PROXY=true` only behind a trusted reverse proxy.
- Use PostgreSQL (`DB_ENGINE=postgresql`) and run `python manage.py migrate`.
- Configure a shared cache for throttling in multi-process deployments.
- Run `python manage.py check --deploy` and `python manage.py test`.
- Monitor 401/429 rates and plan cleanup of expired refresh-token rows.
- Do not rely on logout for immediate access-token revocation.

## Delivery plan

1. **Foundation** (complete): Django project, environment settings, custom
   phone-first `User` model, Argon2id hashing, DRF error envelope, health
   endpoint, migrations, and initial tests.
2. **Token infrastructure** (complete): access JWT service, refresh-token
   families, atomic rotation/revocation, DRF Bearer authentication and
   permissions.
3. **Auth API** (complete): `/auth/check`, `/auth/login`, `/auth/register`,
   `/auth/refresh`, `/auth/logout`, `/auth/session`, OTP stubs, validation,
   and throttling.
4. **CORS and resources** (complete): authenticated `/api/me` resource,
   profile updates, CORS policy restricted to `/api/*`, and preflight/header
   tests.
5. **Hardening and delivery** (complete): end-to-end acceptance tests, JSON
   404/500 handlers, invalid-input throttling fallback, tighter CORS headers,
   production secret checks, security review, deployment checklist, and final
   QA.
