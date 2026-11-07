# Persu Backend — API Inventory and Frontend Contract

Chunk 1 of 5. This document is an inventory only; no tests are added in this
chunk.

## Scope and sources

Scanned files:

- `config/urls.py`, `config/settings.py`
- `apps/accounts/auth_urls.py`, `views.py`, `serializers.py`, `permissions.py`,
  `authentication.py`, `tokens.py`, `services.py`, `throttles.py`, `phone.py`,
  `models.py`, `admin.py`
- `apps/resources/urls.py`, `views.py`, `serializers.py`
- `apps/common/urls.py`, `views.py`, `exceptions.py`, `handlers.py`
- Existing tests under `apps/*/tests/`
- `README.md`, `LOCAL_USAGE.md`, `.env.example`

The project has **11 method-specific API endpoints on 10 paths**. There are no
list endpoints and no API version prefix. An OpenAPI 3 schema is available at
`/api/schema/`, with Swagger UI at `/api/docs/` and ReDoc at `/api/redoc/`.
`/admin/` is a Django admin HTML UI and is not part of the JSON API; it is
excluded from the endpoint table below.

All API paths are **exact and have no trailing slash**. For example, `/api/me`
is valid; `/api/me/` is a 404. See “Trailing slashes and URL matching” below.

## Endpoint inventory

| Method | Path | View | Auth required | Permissions | Request fields | Response fields | Pagination / filtering | Side effects (emails, tasks, DB) |
|---|---|---|---|---|---|---|---|---|
| GET | `/healthz` | `apps.common.views.HealthView` | No | `AllowAny`; no authentication classes; no throttling | None | `200` `{"status": "ok"}` (`status`: string) | None | None |
| POST | `/auth/check` | `apps.accounts.views.CheckView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_check` (10/min per normalized phone; invalid phone falls back to caller IP) | `countryCode` string, required, max 8; `phone` string, required, max 32; normalized to E.164 before lookup | `200` `{"exists": boolean}`; errors per envelope | None | Read-only; no DB writes |
| POST | `/auth/login` | `apps.accounts.views.LoginView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_login` (5/min per normalized phone) | `countryCode` string, required, max 8; `phone` string, required, max 32; `password` string, required, max 128, whitespace-only rejected, not trimmed | `200` `{"accessToken": string, "refreshToken": string, "user": User}`; errors per envelope | None | Revokes every active refresh token for the user; inserts one new `refresh_tokens` row (new family); does **not** update `last_login`; wrapped in a DB transaction |
| POST | `/auth/register` | `apps.accounts.views.RegisterView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_register` (5/min per normalized phone) | Same as login plus optional `fullName` string, max 64, stored as `nick_name` | `201` `{"accessToken": string, "refreshToken": string, "user": User}`; `409` `phone_already_registered` if normalized phone exists | None | Inserts a `users` row (Argon2id password hash, optional `nick_name`) and one `refresh_tokens` row; duplicate phone is caught from the unique constraint; no email/SMS |
| POST | `/auth/refresh` | `apps.accounts.views.RefreshView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_refresh` (20/min per presented refresh token) | `refreshToken` string, required, max 512, whitespace-only rejected | `200` `{"accessToken": string, "refreshToken": string}` (no `user`); errors per envelope | None | Rotates the refresh token in the same family: inserts a new `refresh_tokens` row, marks the old row `revoked_at` and `replaced_by`; reuse of a revoked token revokes the whole family; transaction |
| POST | `/auth/logout` | `apps.accounts.views.LogoutView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_logout` (30/min per refresh token) | `refreshToken` string, required, max 512, whitespace-only rejected | `204` with empty body; errors per envelope | None | Revokes the token family if the presented refresh token is known; unknown non-empty token still returns `204`; idempotent; no DB write for an unknown token |
| GET | `/auth/session` | `apps.accounts.views.SessionView` | Yes — `Authorization: Bearer <access JWT>` | `IsAuthenticatedUser` (authenticated and `is_active`); no throttling; authentication class `BearerAuthentication` | None | `200` `{"user": User}`; `401` `unauthorized` without a token or with an invalid token | None | Read-only |
| POST | `/auth/otp/send` | `apps.accounts.views.OtpSendView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_otp_send` (5/min per normalized phone) | `countryCode` string, required, max 8; `phone` string, required, max 32 | `200` `{"success": true}`; errors per envelope | None | Stub: no SMS, no OTP row, no token; only the throttle cache is touched |
| POST | `/auth/otp/verify` | `apps.accounts.views.OtpVerifyView` | No | `AllowAny`; `AuthScopedRateThrottle`, scope `auth_otp_verify` (10/min per normalized phone) | `countryCode` and `phone` required as above; `code` required string, max 16, must match `AUTH_OTP_MOCK_CODE` (default `123456`) | `200` `{"accessToken": string, "refreshToken": string, "user": User}`; `401` `invalid_otp` for a wrong code; errors per envelope | None | Code validation is mocked; tokens are real. Creates the user if the phone is unknown, then revokes existing refresh tokens and inserts one new `refresh_tokens` row |
| GET | `/api/me` | `apps.resources.views.MeView` | Yes — `Authorization: Bearer <access JWT>` | `IsAuthenticatedUser`; no throttling; CORS enabled for this path | None | `200` `{"user": User}`; `401` `unauthorized`; `406` if the client cannot accept JSON | None | Read-only |
| PATCH | `/api/me` | `apps.resources.views.MeView` | Yes — `Authorization: Bearer <access JWT>` | `IsAuthenticatedUser`; no throttling; CORS enabled for this path | `nickName` optional string, max 64, blank allowed, trimmed; `avatar` optional URL string, max 500, blank allowed; unknown fields ignored; `{}` is a valid no-op | `200` `{"user": User}`; `400` `validation_error`; `401`; `405`; `415` | None | Updates `users.nick_name`, `users.avatar`, and `updated_at`; empty string clears an optional field; no email/task |

Notes:

- “No” auth means the view explicitly has `authentication_classes = []` and
  `permission_classes = [AllowAny]`.
- The auth endpoints are public and CORS-enabled for the configured frontend
  origins (see below).
- `POST /api/me`, `PUT /api/me`, and `DELETE /api/me` are not supported. With a
  valid token they return `405 method_not_allowed`; without a valid token the
  permission check runs first and returns `401 unauthorized`.
- `HEAD` and `OPTIONS` are implicit on every DRF `APIView`; their behavior is
  covered under “Implicit HTTP behavior”.

## Response shapes

### `User`

Every endpoint that returns a user uses this exact public shape:

```json
{
  "id": "0f6f1c2e-7a4b-4f0e-9f8e-2f0f6a1b2c3d",
  "phone": "+12024561111",
  "nickName": "Ada",
  "avatar": "https://example.com/avatar.png"
}
```

- `id`: UUID rendered as a string.
- `phone`: E.164 string, always with a leading `+`.
- `nickName`: optional string. Omitted when the stored value is empty/blank.
- `avatar`: optional URL string. Omitted when the stored value is empty/blank.
- `nickName` and `avatar` are never returned as `null`.
- Internal fields such as `password`, `password_hash`, `phone_e164`, `is_staff`,
  `is_superuser`, `created_at`, and `updated_at` are never exposed.

### Token responses

Login and register (`200`/`201`):

```json
{
  "accessToken": "<HS256 JWT>",
  "refreshToken": "<opaque base64url string>",
  "user": {
    "id": "uuid",
    "phone": "+12024561111"
  }
}
```

Refresh (`200`):

```json
{
  "accessToken": "<HS256 JWT>",
  "refreshToken": "<opaque base64url string>"
}
```

- Access token: HS256 JWT. Default lifetime 900 seconds (15 minutes). Claims:
  `sub` (user UUID string), `typ` (`"access"`), `iss`, `aud`, `iat`, `exp`,
  `jti`.
- Refresh token: opaque 32-byte base64url value. Default lifetime 2,592,000
  seconds (30 days), sliding on each successful rotation. Only its SHA-256 hash
  is stored.
- Responses do **not** include `expiresIn`, `refreshExpiresAt`, `tokenType`, or
  any expiry metadata. A frontend must either decode the access JWT or use the
  configured TTLs.

### Other success responses

| Endpoint | Status | Body |
|---|---|---|
| `GET /healthz` | 200 | `{"status": "ok"}` |
| `POST /auth/check` | 200 | `{"exists": true}` or `{"exists": false}` |
| `POST /auth/logout` | 204 | Empty body (do not parse JSON) |
| `POST /auth/otp/send` | 200 | `{"success": true}` |
| `POST /auth/otp/verify` | 200 | `{"accessToken": string, "refreshToken": string, "user": User}` |

## Frontend contract

### 1. Authentication mechanism

The API uses **Bearer access JWTs only**. It does **not** use Django session
cookies, DRF `TokenAuthentication`, or a token in a query/body/cookie.

The frontend sends:

```http
Authorization: Bearer <accessToken>
```

- The scheme is case-insensitive (`Bearer`/`bearer`); the token itself is
  case-sensitive.
- The header is read by `apps.accounts.authentication.BearerAuthentication`.
  A header with another scheme (for example `Token ...`) is treated as “no
  credentials” and produces `401 unauthorized` with message
  `"Authentication required."`.
- A malformed Bearer header, invalid signature, expired token, wrong token type,
  missing/disabled user, or token longer than 4,096 characters produces
  `401 unauthorized` with message `"Authentication failed."`.
- Access tokens are stateless. They remain valid until `exp` even after logout
  or a subsequent login.
- Refresh tokens are sent in the JSON body field `refreshToken` to
  `/auth/refresh` and `/auth/logout`; they are never used as Bearer tokens.
- Login and register each create a new refresh-token family and revoke all of
  the user’s previous refresh tokens. A user therefore has **one active refresh
  family** at a time.
- On a `401` from `/api/me`, the intended flow is: call `/auth/refresh` with the
  current `refreshToken`, replace both tokens from the response, then retry the
  original request once. If refresh returns `invalid_refresh_token`, send the
  user back to login.
- Logout requires the refresh token, revokes the refresh family, and returns
  `204`. It does not revoke already-issued access tokens.

`/auth/session` and `/api/me` return the same `{"user": ...}` shape. Both the
`/api/*` and `/auth/*` namespaces are CORS-enabled; `/api/me` remains the
canonical browser profile endpoint.

### 2. Standard error format

Every JSON error uses exactly this envelope:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable message."
  }
}
```

There are no other top-level keys, no `detail` key, and no field-level error
map. A `204` response has no body at all.

| Status | `error.code` | `error.message` | When it occurs |
|---|---|---|---|
| 400 | `validation_error` | `Invalid request data.` | Missing/invalid fields, invalid phone number, whitespace-only password/refresh token, invalid avatar URL, too-long values |
| 400 | `invalid_json` | `Malformed JSON request.` | Request body is not parseable JSON |
| 401 | `unauthorized` | `Authentication required.` | No credentials, or an `Authorization` header with a non-Bearer scheme |
| 401 | `unauthorized` | `Authentication failed.` | Bearer token invalid/expired/wrong type, malformed Bearer header, unknown/disabled user |
| 401 | `invalid_credentials` | `Invalid phone number or password.` | Login with unknown phone, wrong password, or inactive user (deliberately generic) |
| 401 | `invalid_refresh_token` | `Invalid or expired refresh token.` | Refresh with unknown, expired, revoked, reused, or inactive-user token |
| 401 | `invalid_otp` | `Invalid or expired verification code.` | OTP verify with a code that does not match `AUTH_OTP_MOCK_CODE` |
| 403 | `forbidden` | `You do not have permission to perform this action.` | Reserved by the error handler; no current endpoint produces it (see `docs/api_issues.md`) |
| 404 | `not_found` | `Resource not found.` | Unknown path, or no matching route |
| 405 | `method_not_allowed` | `Method not allowed.` | Wrong HTTP method for an existing path; response includes `Allow` |
| 409 | `phone_already_registered` | `Phone number is already registered.` | Register with a phone that already exists after normalization |
| 415 | `unsupported_media_type` | `Unsupported media type.` | Request `Content-Type` is not JSON, form-urlencoded, or multipart |
| 429 | `rate_limited` | `Too many requests. Please try again later.` | Auth throttle exceeded; response includes `Retry-After` in seconds |
| 500 | `internal_error` | `An unexpected error occurred.` | Unhandled server exception |

Additional response headers:

- `401` from Bearer authentication includes `WWW-Authenticate: Bearer realm="api"`.
  The custom `401` errors from login/refresh (`invalid_credentials`,
  `invalid_refresh_token`) do not include this header.
- `405` includes `Allow` (for example, `Allow: GET, PATCH, HEAD, OPTIONS`).
- `429` includes `Retry-After` (integer seconds; observed `60`).
- `404`/`500` under `/api/` or `/auth/` include CORS headers when the request
  `Origin` is allowed.

Unhandled exceptions inside DRF views are converted by `api_exception_handler`
to the `500 internal_error` envelope. Exceptions outside DRF views use
`handler500` only when `DEBUG=False`; otherwise Django returns an HTML technical
page.

The error taxonomy is not completely uniform. In particular, an unacceptable
`Accept` header produces a real `406` status but the body code is
`bad_request`/`Request could not be processed.` because `NotAcceptable` is not
mapped in `apps/common/exceptions.py`. See `docs/api_issues.md`.

### 3. Pagination, filtering, and ordering

There is **no pagination, filtering, or ordering** in the current API:

- No DRF pagination class is configured.
- No filter backends, search fields, or ordering fields are configured.
- There are no list endpoints; every success body is a single JSON object.
- Query parameters such as `?page=`, `?limit=`, `?search=`, or `?ordering=` are
  ignored, not validated.
- Responses contain no `Link` header, `count`, `next`, `previous`, or `results`.

A frontend should not assume any query-parameter behavior. New list endpoints
will need an explicit convention.

### 4. CORS behavior

CORS is enabled for paths matching `CORS_URLS_REGEX = r"^/(?:api|auth)/"`:

- `GET/PATCH /api/me` — CORS enabled.
- `POST /auth/check`, `/auth/login`, `/auth/register`, `/auth/refresh`,
  `/auth/logout`, `/auth/otp/send`, `/auth/otp/verify` — CORS enabled.
- `GET /auth/session` — CORS enabled.
- `/healthz` — no CORS headers.
- `/admin/*` — no CORS headers.

Default policy (`config/settings.py`):

- Allowed origins: `http://localhost:3000` and `http://127.0.0.1:3000`, unless
  overridden by the comma-separated `CORS_ALLOWED_ORIGINS` environment variable.
  Matching is exact (scheme, host, and port); there is no wildcard or subdomain
  matching.
- Allowed request headers: django-cors-headers' safe defaults (including
  `authorization` and `content-type`) plus the frontend headers `X-App-Version`,
  `x-platform`, `X-Client-Locale`, and `x-seconds-from-utc`. Header names are
  matched case-insensitively.
- Allowed methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`.
- Credentials: disabled (`CORS_ALLOW_CREDENTIALS = False`); no
  `Access-Control-Allow-Credentials` header is emitted.
- Preflight cache: `Access-Control-Max-Age: 86400` (24 hours).
- Allowed-origin responses echo the request origin in
  `Access-Control-Allow-Origin` and include `Vary: Origin`.

Preflight behavior:

- `OPTIONS /api/me` with `Origin` and `Access-Control-Request-Method` headers is
  answered by the CORS middleware with `200`, an empty body, and the CORS
  headers above. It does **not** require an access token.
- `OPTIONS /api/me` without CORS preflight headers is handled by DRF and
  requires authentication; without a token it returns `401`.
- With a valid token, a non-preflight `OPTIONS /api/me` returns `200` DRF
  metadata.
- Preflight requests to the public auth endpoints (for example
  `OPTIONS /auth/login`) are answered by the CORS middleware with `200` and the
  CORS headers, so a browser frontend can call the auth routes directly.
- Actual `/api/*` and `/auth/*` responses, including `401`, `400`, and `404`,
  carry the CORS headers when the request origin is allowed, so the browser can
  read the error body.
- A disallowed origin receives no `Access-Control-Allow-Origin`; the server may
  still process the request, but the browser blocks the response.

Because both namespaces are CORS-enabled, a browser frontend can call
`/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/logout`,
`/auth/otp/verify`, and `/auth/session` directly, provided its origin is listed
in `CORS_ALLOWED_ORIGINS`.

Request headers outside the policy listed above (for example `X-Request-Id`)
will cause a preflight failure unless `CORS_ALLOW_HEADERS` is extended.

### 5. CSRF behavior

- All DRF `APIView`s are `csrf_exempt` by DRF design.
- The only configured DRF authentication class is `BearerAuthentication`.
  `SessionAuthentication` is not configured, so API requests do not use Django
  session cookies and do not require a CSRF token.
- `CORS_ALLOW_CREDENTIALS = False`, so cross-origin browser requests do not send
  cookies.
- `CSRF_TRUSTED_ORIGINS` (default empty) is therefore irrelevant to the JSON
  API; it matters for Django admin/non-DRF form posts.
- `/admin/` uses the normal Django session + CSRF flow and is not part of the
  frontend API contract.

A frontend should send `Authorization` and `Content-Type: application/json` and
must not rely on cookies or a CSRF token for `/api/*` or `/auth/*`.

### 6. Request content types and `Accept`

- The documented request format is JSON: `Content-Type: application/json`.
- DRF’s default parsers are still active, so `application/x-www-form-urlencoded`
  and `multipart/form-data` are also accepted on these endpoints.
  `text/plain` returns `415 unsupported_media_type`.
- Only `JSONRenderer` is configured. Requests whose `Accept` header cannot
  accept JSON (for example `Accept: text/html`) return `406` with the
  mislabelled `bad_request` envelope described above. Browser defaults
  (`*/*`) and `Accept: application/json` work.

### 7. Implicit HTTP behavior

- `HEAD` is automatically supported on GET endpoints and returns the same
  status/headers with an empty body (`HEAD /healthz` → `200`,
  `HEAD /api/me` with a token → `200`).
- `HEAD` on POST-only auth endpoints returns `405` with an empty body because
  HEAD is not added to the `Allow` list.
- `OPTIONS` returns DRF metadata on public endpoints; on protected endpoints it
  requires authentication unless it is a CORS preflight, which is intercepted
  earlier by middleware.
- `405` responses include an `Allow` header. On protected views, an
  unauthenticated request with an unsupported method returns `401` before
  method dispatch; with a valid token it returns `405`.

### 8. Trailing slashes and URL matching

Routes are registered without trailing slashes. Use the exact paths:

- Valid: `/healthz`, `/auth/check`, `/auth/login`, `/auth/register`,
  `/auth/refresh`, `/auth/logout`, `/auth/session`, `/auth/otp/send`,
  `/auth/otp/verify`, `/api/me`.
- Invalid: `/api/me/`, `/auth/check/`, `/auth/login/`, etc. These produce a
  `404` (JSON `not_found` when `DEBUG=False`; Django’s HTML technical 404 page
  when `DEBUG=True`).

`APPEND_SLASH` does not help because no slash-suffixed variant is registered.
Frontend URL joining must not append a trailing slash blindly.

## Rate limits

Auth endpoints use `AuthScopedRateThrottle`. The bucket key is the normalized
phone number, or the raw refresh token when one is supplied. Invalid phone
numbers fall back to the caller IP. Throttling is evaluated before serializer
validation, so requests with valid JSON but invalid field values can consume the
bucket.

| Endpoint | Scope | Default limit | Key |
|---|---|---|---|
| `POST /auth/check` | `auth_check` | 10/min | normalized phone; invalid phone → IP |
| `POST /auth/login` | `auth_login` | 5/min | normalized phone; invalid phone → IP |
| `POST /auth/register` | `auth_register` | 5/min | normalized phone; invalid phone → IP |
| `POST /auth/refresh` | `auth_refresh` | 20/min | presented `refreshToken` |
| `POST /auth/logout` | `auth_logout` | 30/min | presented `refreshToken` |
| `POST /auth/otp/send` | `auth_otp_send` | 5/min | normalized phone; invalid phone → IP |
| `POST /auth/otp/verify` | `auth_otp_verify` | 10/min | normalized phone; invalid phone → IP |

No throttling is configured for `/healthz`, `/auth/session`, or `/api/me`.
The default Django local-memory cache is per process, so limits are not global
across workers unless a shared cache is configured.

## Side effects and background work

- No email, SMS, push, Celery, task queue, signals, webhooks, or outbound HTTP
  calls exist in the application code.
- `/auth/otp/send` is a stub: no SMS is sent and no OTP is stored.
  `/auth/otp/verify` validates the configured mock code and issues real tokens;
  it does not generate or deliver a code yet.
- Database tables involved: `users` and `refresh_tokens`, plus Django’s
  auth/session/admin tables.
- Login: revokes all active `refresh_tokens` rows for the user and inserts one
  new row.
- Register: inserts one `users` row and one `refresh_tokens` row.
- OTP verify: validates `code`; creates a `users` row with an unusable password
  only when the normalized phone is unknown, then revokes existing refresh
  tokens and inserts one new `refresh_tokens` row.
- Refresh: inserts a new `refresh_tokens` row, revokes the presented row, and
  links it through `replaced_by`; reuse revokes the whole family.
- Logout: marks the refresh-token family revoked if the presented token exists.
- `PATCH /api/me`: updates `nick_name`, `avatar`, and `updated_at` on the
  authenticated user.
- All other endpoints are read-only with respect to application data.
- Auth throttle hits update the configured Django cache; failures are logged by
  `django.request` at WARNING level.

## Out of scope for the JSON API

- `/admin/` — Django admin HTML, session-cookie authentication, CSRF-protected.
- `/static/*`, `/media/*` — static/media serving, not API.
- Unknown paths — `handler404` returns the JSON envelope only when
  `DEBUG=False`; in local development (`DEBUG=True`) Django returns its HTML
  technical 404 page. `handler500` is similarly a `DEBUG=False` fallback for
  exceptions outside DRF views.

## Frontend integration checklist

1. Configure the API base URL; never append a trailing slash to the paths above.
2. Call `/healthz` for liveness (no auth; it is outside the CORS-enabled
   namespaces).
3. Set `CORS_ALLOWED_ORIGINS` to include the frontend origin, then call
   `/auth/login`, `/auth/register`, `/auth/refresh`, and `/auth/logout` directly
   from the browser.
4. Store `accessToken` and `refreshToken`; send
   `Authorization: Bearer <accessToken>` to `/api/me`.
5. On `401` from `/api/me`, rotate via `/auth/refresh` once and retry. On
   `invalid_refresh_token`, require a new login.
6. Expect `401` bodies with codes `unauthorized`, `invalid_credentials`,
   `invalid_refresh_token`, or `invalid_otp`; treat any `401` as an auth failure
   but branch on the code for UX.
7. Do not expect field-level validation details; all `400` validation failures
   currently have the same generic body.
8. Do not use cookies or CSRF tokens for API calls; do not rely on logout to
   invalidate an already-issued access token.
9. Send `Authorization`, `Content-Type`, and the custom headers
   `X-App-Version`, `x-platform`, `X-Client-Locale`, and `x-seconds-from-utc`
   freely; they are all allowed by CORS.
10. Treat `204` logout as an empty response; do not call `.json()` on it.
