# Local Usage and Testing

This guide shows how to run the backend locally, exercise the authentication
flow, call the resource API, and run the automated tests.

The examples use Windows PowerShell. The default local database is SQLite, so
no external services are required.

## 1. Prerequisites

- Python 3.13
- PowerShell
- A checkout of this repository

## 2. Create the virtual environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

If `py -3.13` is unavailable, use `py -m venv .venv`.

## 3. Set local environment variables

The application has production-like test defaults in `config/settings.py`.
Enable debug mode for local development; setting explicit secrets is
recommended when your environment is shared:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = .\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(64))"
$env:AUTH_JWT_SECRET = .\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(64))"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
```

Optional settings:

```powershell
$env:CORS_ALLOWED_ORIGINS = "http://localhost:3000"
$env:DJANGO_LOG_LEVEL = "INFO"
```

These variables apply only to the current PowerShell session.

## 4. Apply migrations

```powershell
.\.venv\Scripts\python manage.py migrate
```

Optional admin account:

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

The admin site is available at `http://127.0.0.1:8000/admin/`.

## 5. Start the server

```powershell
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

In a second PowerShell window, set the base URL:

```powershell
$base = "http://127.0.0.1:8000"
```

## 6. Smoke test

```powershell
Invoke-RestMethod -Uri "$base/healthz"
```

Expected response:

```json
{"status": "ok"}
```

## 7. Authentication walkthrough

The examples use the US phone number `202-456-1111`, which normalizes to
`+12024561111`. Use any valid phone number you control for local testing.

### Check whether a phone is registered

```powershell
$checkBody = @{
    countryCode = "US"
    phone = "2024561111"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$base/auth/check" `
    -ContentType "application/json" `
    -Body $checkBody
```

Expected before registration:

```json
{"exists": false}
```

### Register

```powershell
$registerBody = @{
    countryCode = "US"
    phone = "2024561111"
    password = "correct horse battery staple"
} | ConvertTo-Json

$registered = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/auth/register" `
    -ContentType "application/json" `
    -Body $registerBody

$registered.user
```

The response contains `accessToken`, `refreshToken`, and `user`. The public user
shape is:

```json
{
  "id": "uuid",
  "phone": "+12024561111"
}
```

`nickName` and `avatar` appear only when set.

### Login

A new login starts a new refresh-token family and revokes the registration
family, so use the login tokens for the rest of the walkthrough.

```powershell
$loginBody = @{
    countryCode = "US"
    phone = "2024561111"
    password = "correct horse battery staple"
} | ConvertTo-Json

$session = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$accessToken = $session.accessToken
$refreshToken = $session.refreshToken
```

### Read the current session

```powershell
Invoke-RestMethod `
    -Uri "$base/auth/session" `
    -Headers @{ Authorization = "Bearer $accessToken" }
```

### Read the resource API

```powershell
Invoke-RestMethod `
    -Uri "$base/api/me" `
    -Headers @{ Authorization = "Bearer $accessToken" }
```

### Update the profile

```powershell
$profileBody = @{
    nickName = "Ada"
    avatar = "https://example.com/avatar.png"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Patch `
    -Uri "$base/api/me" `
    -Headers @{ Authorization = "Bearer $accessToken" } `
    -ContentType "application/json" `
    -Body $profileBody
```

Only `nickName` and `avatar` are writable. Sending an empty string clears an
optional field.

### Refresh the token pair

```powershell
$rotated = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/auth/refresh" `
    -ContentType "application/json" `
    -Body (@{ refreshToken = $refreshToken } | ConvertTo-Json)

$rotated.accessToken
$rotated.refreshToken
```

The old refresh token is now invalid. Presenting it again is treated as reuse
and revokes the whole family.

### Logout

```powershell
$logout = Invoke-WebRequest `
    -Method Post `
    -Uri "$base/auth/logout" `
    -ContentType "application/json" `
    -Body (@{ refreshToken = $rotated.refreshToken } | ConvertTo-Json)

$logout.StatusCode
```

Expected status: `204`. Logout is idempotent.

### Error response example

```powershell
try {
    Invoke-RestMethod `
        -Method Post `
        -Uri "$base/auth/login" `
        -ContentType "application/json" `
        -Body (@{
            countryCode = "US"
            phone = "2024561111"
            password = "wrong password"
        } | ConvertTo-Json)
} catch {
    $_.ErrorDetails.Message
}
```

Expected envelope:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Invalid phone number or password."
  }
}
```

## 8. Check CORS locally

Resource routes under `/api/*` allow the configured browser origin. Auth routes
under `/auth/*` intentionally do not emit CORS headers.

```powershell
$corsHeaders = @{
    Origin = "http://localhost:3000"
    "Access-Control-Request-Method" = "PATCH"
    "Access-Control-Request-Headers" = "authorization,content-type"
}

$preflight = Invoke-WebRequest `
    -Method Options `
    -Uri "$base/api/me" `
    -Headers $corsHeaders

$preflight.StatusCode
$preflight.Headers["Access-Control-Allow-Origin"]
$preflight.Headers["Access-Control-Allow-Methods"]
$preflight.Headers["Access-Control-Allow-Headers"]
```

Expected:

- status `200`
- `Access-Control-Allow-Origin: http://localhost:3000`
- `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS` in the allowed methods
- `Authorization` and `Content-Type` in the allowed headers
- no `Access-Control-Allow-Credentials` header

To test a disallowed origin, use `Origin: https://evil.example.com`; the response
should not include `Access-Control-Allow-Origin`.

If you prefer curl, use `curl.exe` in PowerShell:

```powershell
curl.exe -i -X POST "$base/auth/check" `
  -H "Content-Type: application/json" `
  -d '{"countryCode":"US","phone":"2024561111"}'
```

## 9. Run the automated tests

Run the full suite:

```powershell
.\.venv\Scripts\python manage.py test
```

The suite covers auth, token rotation and reuse, one-session behavior, resource
access, CORS, throttling, and error envelopes.

Run focused groups:

```powershell
.\.venv\Scripts\python manage.py test apps.accounts.tests.test_acceptance -v 2
.\.venv\Scripts\python manage.py test apps.accounts.tests.test_auth_api -v 2
.\.venv\Scripts\python manage.py test apps.resources.tests -v 2
```

Run project checks:

```powershell
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
.\.venv\Scripts\python -m pip check
```

## 10. Production-style deployment check

Run this in a separate PowerShell window so the production environment variables
do not affect your local development server:

```powershell
$env:DJANGO_DEBUG = "false"
$env:DJANGO_SECRET_KEY = "check-only-django-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz"
$env:AUTH_JWT_SECRET = "check-only-jwt-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz-different"
$env:DJANGO_ALLOWED_HOSTS = "api.example.com"
$env:DJANGO_SECURE_SSL_REDIRECT = "true"
$env:DJANGO_SECURE_HSTS_SECONDS = "31536000"
$env:DJANGO_SECURE_COOKIES = "true"

.\.venv\Scripts\python manage.py check --deploy
```

Expected: `System check identified no issues`.

## 11. Reset the local database

This deletes all local users and refresh tokens.

```powershell
Remove-Item .\db.sqlite3
.\.venv\Scripts\python manage.py migrate
```

## 12. Troubleshooting

### `429 rate_limited`

Auth routes are rate limited. Limits include:

| Route | Limit |
| --- | --- |
| `/auth/check` | 10/min per phone |
| `/auth/login` | 5/min per phone |
| `/auth/register` | 5/min per phone |
| `/auth/refresh` | 20/min per token |
| `/auth/logout` | 30/min per token |
| `/auth/otp/send` | 5/min per phone |
| `/auth/otp/verify` | 10/min per phone |

The default local-memory cache is per process. Restart the development server
to clear local rate-limit state, or wait for the window to pass.

### `401 unauthorized`

Access tokens expire after 15 minutes. Refresh the token pair or log in again.
A refresh token cannot be used as a Bearer access token.

### CORS errors in a browser

- The request must come from `http://localhost:3000`, or whatever is set in
  `CORS_ALLOWED_ORIGINS`.
- Auth routes under `/auth/*` are intentionally not CORS-enabled.
- Resource routes must send `Authorization` and `Content-Type`.

### `DisallowedHost`

Set `DJANGO_ALLOWED_HOSTS` to include the host you are using, such as
`localhost,127.0.0.1,testserver`.

### `ImproperlyConfigured`

The built-in `DJANGO_SECRET_KEY` and `AUTH_JWT_SECRET` are test-only
placeholders. For a shared deployment, override both with values of at least 32
characters.

### `curl` behaves differently in PowerShell

`curl` may resolve to `Invoke-WebRequest`. Use `curl.exe` for real curl behavior.

## 13. Known local limitations

- OTP endpoints are stubs; no SMS is sent and any code is accepted.
- Access tokens are stateless. Logout and a second login revoke refresh tokens,
  but already-issued access tokens remain valid until they expire.
- The default throttle cache is local to one process. Production should use a
  shared cache such as Redis.
- Password reset, MFA, social/email login, and multiple simultaneous sessions
  are out of scope.
