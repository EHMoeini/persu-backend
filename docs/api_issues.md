# API Issues and Inconsistencies

Chunk 1 of 5. These findings were recorded from the current code, the existing
test suite, and read-only runtime probes. **No production code was changed.**

Severity is an integration/QA assessment, not a formal security rating.

## Summary

| ID | Severity | Area | Finding |
|---|---|---|---|
| API-001 | High | Errors | Validation errors discard all field-level detail |
| API-002 | High | Errors | Django JSON 404/500 handlers only apply when `DEBUG=False`; unresolved routes in local dev return HTML |
| API-003 | High | Auth/OTP | OTP send/verify are stubs that always succeed and issue no session |
| API-004 | High | Auth/passwords | No minimum password length, complexity, or confirmation |
| API-005 | Medium | Validation | Unknown request fields are silently ignored |
| API-006 | Medium | Errors | `406 Not Acceptable` is mislabelled as `bad_request` |
| API-007 | Medium | Permissions | `IsOwner` is unused; no endpoint can produce `403`; object-permission model is undefined |
| API-008 | Medium | Errors/auth | `401` codes/messages vary and only Bearer-auth 401s include `WWW-Authenticate` |
| API-009 | Medium | Tokens | Responses omit access/refresh expiry metadata |
| API-010 | Medium | Tokens | Access tokens remain valid after logout or a later login |
| API-011 | Medium | Tokens | Only one refresh-token family per user; a new login invalidates older sessions |
| API-012 | Medium | CORS | `/auth/*` is not CORS-enabled, including protected `/auth/session` |
| API-013 | Medium | Routing | No trailing-slash variants; `/api/me/` and `/auth/check/` are 404 |
| API-014 | Low | Content types | Docs say JSON, but form/multipart bodies are accepted by default DRF parsers |
| API-015 | Low | Profile | `avatar` accepts `ftp`/`ftps`; blank strings clear fields and omit them from responses |
| API-016 | Low | Registration | User creation and token issuance are not atomic |
| API-017 | Low | Throttling | Per-phone limits allow targeted lockout; `/auth/check` is an enumeration oracle |
| API-018 | Low | API design | No versioning, OpenAPI schema, or pagination/filtering convention |
| API-019 | Low | Operations | Refresh-token rows are never cleaned up and are not visible in admin |
| API-020 | Low | User data | `last_login` is never updated by the custom login flow |
| API-021 | Low | CORS/deploy | CORS is narrow (one origin, two headers) and easy to misconfigure |
| API-022 | Low | HTTP semantics | `OPTIONS`/`HEAD` behavior differs between preflight, authenticated, and public cases |
| API-023 | Low | Phone input | `countryCode` accepts several formats but only some are documented/valid |

## Details

### API-001 — Validation errors discard field-level detail

**Severity:** High
**Area:** Error contract

`apps/common/exceptions.py` maps every DRF `ValidationError` to:

```json
{"error": {"code": "validation_error", "message": "Invalid request data."}}
```

and then replaces `response.data` with that envelope. The original field map
(for example `{"phone": ["This field is required."]}`) is lost.

Runtime probe examples that all produced the identical body:

- `POST /auth/check` with `{}` (missing `countryCode` and `phone`)
- `PATCH /api/me` with `{"nickName": null}`
- `PATCH /api/me` with a 65-character `nickName`
- `PATCH /api/me` with `{"avatar": "not-a-url"}`

**Impact:** a frontend cannot highlight the offending field or show a useful
message. It can only say “Invalid request data.” This is especially painful for
forms with multiple fields.

**Suggested resolution:** add a stable optional `details` object (field name →
array of messages) under `error`, or define per-field codes. Keep the generic
message for clients that do not opt in. Cover each validation case in the test
suite.

### API-002 — JSON 404/500 handlers only apply when `DEBUG=False`

**Severity:** High
**Area:** Error contract / local development

`config/urls.py` registers `handler404` and `handler500`, and the README says
unknown routes use the JSON envelope. However, Django bypasses those handlers in
`DEBUG=True` and renders its technical HTML pages.

Runtime probe:

- `GET /api/missing` with `DEBUG=True` → `404 text/html` technical page.
- `GET /api/missing` with `DEBUG=False` → `404 application/json` with
  `{"error": {"code": "not_found", ...}}`.
- `GET /api/me/` with `DEBUG=True` → `404 text/html`.
- The same paths with `DEBUG=False` → JSON envelope, with CORS headers under
  `/api/`.

**Impact:** the frontend developer proxy usually runs against the local dev
server (`DEBUG=True` by default). Any 404/500 outside a DRF view arrives as HTML,
so `response.json()` fails and error handling is inconsistent between local and
deployed environments. Django’s test runner forces `DEBUG=False`, so existing
tests do not catch the local behavior.

**Suggested resolution:** make the JSON handlers effective in all modes (custom
middleware or a catch-all JSON route), or explicitly document “JSON only in
production” and add a dev-mode test. Do not rely on the README claim as written.

### API-003 — OTP endpoints are non-functional stubs

**Severity:** High
**Area:** Auth / OTP

`OtpSendView` always returns `{"success": true}` and `OtpVerifyView` always
returns `{"success": true}`. `OtpVerifySerializer.code` is optional, allows
blank, and is never read by the view. No SMS is sent, no OTP is stored, and no
token or session is issued.

This is acknowledged in `README.md`/`LOCAL_USAGE.md` as a stub, but the
endpoint names and success responses are indistinguishable from a working OTP
flow from the client’s point of view.

**Impact:** a frontend could ship an OTP login screen that appears to succeed
for any phone/code but never authenticates the user. It also creates a false
sense of security and makes tests that assert only `success: true` misleading.

**Suggested resolution:** return `501 Not Implemented` or a feature-disabled
error until real verification exists, or make the stub issue a real token only
after a deliberately documented test code. Add explicit “stub” documentation to
the frontend contract.

### API-004 — No password policy

**Severity:** High
**Area:** Auth / registration

`LoginSerializer` and `RegisterSerializer` define `password` as a `CharField`
with `max_length=128`, `trim_whitespace=False`, and a custom validator that
rejects only whitespace-only values. There is:

- no minimum length,
- no complexity/breached-password check,
- no confirmation field,
- no check that the password differs from the phone number.

Runtime probe: `POST /auth/register` with `"password": "x"` returned `201` and
created an account.

**Impact:** trivially weak credentials are accepted. The frontend has no
requirements to display because the backend defines none. Existing tests only
check missing/whitespace passwords, so the gap is invisible.

**Suggested resolution:** define and centralize a password policy, return
field-level validation details (API-001), and document the policy in the
frontend contract. Add boundary tests for the minimum/maximum and whitespace
behavior.

### API-005 — Unknown request fields are silently ignored

**Severity:** Medium
**Area:** Request validation

DRF serializers ignore keys they do not declare. Runtime probe
`PATCH /api/me` with:

```json
{"nickname": "Ada", "phone": "+442071838750", "id": "x", "x": 1}
```

returned `200` and only applied the known fields (none of those). The response
still contained the old user data. Likewise, `POST /auth/register` with
`"is_staff": true` and `"is_superuser": true` created a normal user and returned
`201`.

**Impact:** a case-sensitive typo such as `nickname` instead of `nickName`
silently does nothing while reporting success. Clients may believe a profile
update or privilege change happened when it did not. It also makes contract
drift hard to detect.

**Suggested resolution:** reject unknown fields with a validation error, or
explicitly document that unknown fields are ignored. If rejecting, keep the
error shape consistent with API-001. Add tests for common typos and
mass-assignment attempts.

### API-006 — `406 Not Acceptable` is mislabelled as `bad_request`

**Severity:** Medium
**Area:** Error mapping

Only `JSONRenderer` is configured. A request with `Accept: text/html` is
rejected by DRF with `NotAcceptable` (HTTP 406), but `_error_payload()` has no
branch for `NotAcceptable`; it falls through to the generic `APIException`
branch and returns:

```json
{"error": {"code": "bad_request", "message": "Request could not be processed."}}
```

with status `406`.

Runtime probe confirmed this for `GET /healthz` and `GET /api/me`.

**Impact:** status and code disagree. A frontend or API client that branches on
`error.code` will treat a content-negotiation problem as a malformed request.
`415 Unsupported Media Type` is mapped correctly, which makes the gap more
noticeable.

**Suggested resolution:** add an explicit `NotAcceptable` branch with
`not_acceptable`/`Could not satisfy the request Accept header.` and add a test
for `Accept: text/html`.

### API-007 — Permission model is mostly unused/vague

**Severity:** Medium
**Area:** Permissions

- `IsAuthenticatedUser` is the global default and is used by `/auth/session` and
  `/api/me`.
- `IsOwner` exists in `apps/accounts/permissions.py` but no view or viewset uses
  it. There are no object-level resource endpoints.
- The error handler maps `PermissionDenied` to `403 forbidden`, but no current
  endpoint can produce a `403`: public views are `AllowAny`, protected views use
  `IsAuthenticatedUser`, and an inactive user is rejected earlier by
  `BearerAuthentication` as a `401`.
- `IsAuthenticatedUser` duplicates the active-user check already performed by
  Bearer authentication.

**Impact:** the permission story for future resources is undefined. A frontend
cannot rely on `403` semantics, and adding a resource endpoint without an
object-permission decision risks inconsistent behavior. Dead `IsOwner` code may
mislead future implementers.

**Suggested resolution:** decide whether object-level access will use `IsOwner`
or another mechanism, document the 401-vs-403 policy, and either use or remove
`IsOwner`. Add authorization tests when object endpoints are introduced.

### API-008 — `401` taxonomy and headers are inconsistent

**Severity:** Medium
**Area:** Auth errors

All of these are HTTP `401`, but the body codes/messages differ:

| Situation | Code | Message | `WWW-Authenticate` |
|---|---|---|---|
| Missing/non-Bearer credentials | `unauthorized` | `Authentication required.` | Yes (Bearer challenge) |
| Invalid/expired Bearer token | `unauthorized` | `Authentication failed.` | Yes |
| Login bad phone/password | `invalid_credentials` | `Invalid phone number or password.` | No |
| Refresh bad/expired/reused token | `invalid_refresh_token` | `Invalid or expired refresh token.` | No |

**Impact:** a generic “on 401, refresh” interceptor will also fire for login and
refresh failures, potentially causing loops. Clients that expect
`WWW-Authenticate` on every 401 will not find it on the custom auth errors.
Conversely, clients that branch only on the message will break if wording
changes.

**Suggested resolution:** document the code table (done in the inventory) and
standardize whether all 401s carry a challenge header. Prefer machine-readable
codes over message matching. Add tests asserting status, code, message, and
header presence per case.

### API-009 — Token expiry metadata is missing

**Severity:** Medium
**Area:** Token contract

`_token_response()` returns only `accessToken`, `refreshToken`, and `user`.
`RefreshView` returns only the two tokens. There is no `expiresIn`,
`refreshExpiresAt`, `tokenType`, or equivalent.

The access token’s `exp` claim is decodable, but the refresh token is opaque.
The configured defaults are 900 seconds for access and 2,592,000 seconds for
refresh, with the refresh TTL sliding on every rotation.

**Impact:** the frontend must either decode the JWT (and trust clock skew) or
hardcode the TTLs. It cannot schedule a refresh based on the refresh token’s
actual expiry. A future TTL configuration change silently changes frontend
behavior.

**Suggested resolution:** return `expiresIn` (seconds) and
`refreshExpiresAt` (ISO 8601) alongside the tokens, or explicitly document the
TTL contract and keep it stable. Add tests for the fields if added.

### API-010 — Access tokens remain valid after logout or a later login

**Severity:** Medium
**Area:** Token revocation semantics

Access tokens are stateless JWTs. Logout revokes the refresh-token family only.
A later login also revokes previous refresh tokens but does not invalidate
already-issued access tokens. The README states this explicitly, and the
acceptance test `test_second_login_invalidates_old_refresh_but_not_old_access`
asserts that an old access token still returns `200` on `/api/me`.

**Impact:** “logout” does not mean “the current access token stops working.”
A stolen/leaked access token remains usable for up to 15 minutes. A frontend
that clears local storage may still be exposed if the token is replayed.

**Suggested resolution:** document prominently (done) and decide whether
immediate revocation is required. If so, add a `jti` denylist or a per-user
token version claim checked by `BearerAuthentication`. Otherwise accept the
15-minute window as a deliberate trade-off.

### API-011 — Only one refresh-token family per user

**Severity:** Medium
**Area:** Session semantics

`login_user()` and `register_user()` call `issue_token_pair()` with the default
`revoke_existing=True`, which revokes every active refresh token for the user
before creating a new family. The README calls this “one session per user.”

**Impact:** logging in on a second tab/device invalidates the first session’s
refresh token. The first frontend will get `401 invalid_refresh_token` on its
next refresh and must send the user back to login. This is surprising for users
who expect independent sessions.

**Suggested resolution:** confirm this is a product requirement. If not, issue a
new family per login/device and track them independently. If yes, document the
behavior in the frontend UX and ensure the client handles refresh failure
gracefully.

### API-012 — `/auth/*` is not CORS-enabled, including `/auth/session`

**Severity:** Medium
**Area:** CORS / frontend integration

`CORS_URLS_REGEX = r"^/api/"` means CORS headers are emitted only for `/api/*`.
The README says auth routes are server-to-server and intentionally excluded.
However, `/auth/session` is a protected user endpoint that returns the same
`{"user": ...}` payload as `/api/me`; a browser frontend cannot call it from a
different origin, while `/api/me` works.

**Impact:** the frontend must proxy all auth calls through a same-origin server
or backend-for-frontend. Direct browser integration with `/auth/login`,
`/auth/register`, `/auth/refresh`, `/auth/logout`, or `/auth/session` fails
preflight/CORS. The protected `/auth/session` route is particularly easy to
misuse because it looks like a browser session endpoint.

**Suggested resolution:** document the proxy requirement explicitly (done), and
consider moving the browser-facing session route under `/api/` or enabling CORS
for the auth routes if direct calls are desired. Add a CORS integration test for
the chosen architecture.

### API-013 — No trailing-slash variants

**Severity:** Medium
**Area:** Routing

All routes are registered without trailing slashes. `/api/me/`,
`/auth/check/`, `/auth/login/`, etc. do not resolve. `APPEND_SLASH` does not
redirect because no slash-suffixed pattern exists. With `DEBUG=True`, these
paths return Django’s HTML technical 404; with `DEBUG=False`, they return the
JSON `not_found` envelope.

**Impact:** frontend URL joining (`baseUrl + "/api/me/"`), reverse-proxy
rewrites, or manual testing with a trailing slash produce 404s. The failure mode
differs between local and deployed environments.

**Suggested resolution:** standardize one convention. If keeping no-slash
routes, document it prominently and add exact-path integration tests. If adding
slashes, register canonical slash routes and use `APPEND_SLASH` consistently.

### API-014 — JSON is documented, but form/multipart is accepted

**Severity:** Low
**Area:** Content types

`REST_FRAMEWORK` does not override `DEFAULT_PARSER_CLASSES`, so DRF’s defaults
(`JSONParser`, `FormParser`, `MultiPartParser`) are active. Runtime probe:
`POST /auth/check` with form-urlencoded data returned `200`. `text/plain`
returned `415`.

**Impact:** the docs say JSON bodies, but clients can accidentally (or
maliciously) send form data and still succeed. This changes CORS behavior:
`application/x-www-form-urlencoded` is a CORS-safelisted content type and can
avoid a preflight, while `application/json` requires one. Tests that only send
JSON will not cover this.

**Suggested resolution:** set `DEFAULT_PARSER_CLASSES = ["rest_framework.parsers.JSONParser"]`
if JSON-only is intended, or document all accepted content types. Add `415`
tests for unsupported types and decide the CORS implications.

### API-015 — Avatar URL schemes and clear/trim semantics

**Severity:** Low
**Area:** Profile validation

`ProfileUpdateSerializer.avatar` uses DRF `URLField`, whose Django
`URLValidator` accepts `http`, `https`, `ftp`, and `ftps`. Runtime probe:
`{"avatar": "ftp://example.com/a.png"}` returned `200` and stored the value.
`nickName` is trimmed by DRF’s `CharField` default. Empty strings for either
field clear the stored value, and `UserSerializer` then omits the field from the
response. `null` is rejected with `400`.

**Impact:** a frontend `<img>` may not render `ftp://` URLs. Users may not
realize that submitting an empty string clears a field rather than leaving it
unchanged. Trimming means `" Ada "` is stored as `"Ada"`.

**Suggested resolution:** restrict `avatar` to `http`/`https` if that is the
intended contract, and document blank-clears/trim behavior. Add tests for
`ftp`, `ftps`, `javascript:`, blank, `null`, and whitespace-only values.

### API-016 — Registration is not atomic across user and token creation

**Severity:** Low
**Area:** Registration consistency

`register_user()` wraps only `User.objects.create_user(...)` in
`transaction.atomic()`. It then calls `issue_token_pair()` after that block. If
token issuance fails (database error, unexpected exception), the user row is
already committed but the client receives a 500 and no tokens. Retrying
registration then returns `409 phone_already_registered`, and the user must use
login.

**Impact:** a transient failure can leave an account that the user believes was
not created. It is rare but produces confusing support cases.

**Suggested resolution:** wrap user creation and token issuance in one
transaction, or explicitly delete/compensate the user if token issuance fails.
Add a test that simulates token-issuance failure.

### API-017 — Per-phone throttling enables targeted lockout and enumeration

**Severity:** Low
**Area:** Abuse resistance

Auth throttle buckets are keyed by normalized phone (or refresh token), not by
IP. `/auth/login` allows 5 attempts/minute per phone, so an attacker who knows a
victim’s phone can exhaust the bucket with 5 bad passwords and cause `429` for
the victim. `/auth/check` is unauthenticated and reveals whether a phone is
registered; an attacker can enumerate many phones at 10 requests/minute each.
Invalid phone formats fall back to the caller IP, which can affect many users
behind NAT.

The README explains the per-phone choice (shared Next server IP), so this is a
known trade-off rather than a coding bug.

**Impact:** targeted denial of service and phone-number enumeration. The
per-phone bucket also makes shared-IP abuse less visible.

**Suggested resolution:** add edge/IP/global rate limits and monitoring, consider
CAPTCHA or exponential backoff for repeated failures, and review whether
`/auth/check` needs to reveal existence so openly. Document the privacy
trade-off.

### API-018 — No versioning, OpenAPI schema, or pagination convention

**Severity:** Low
**Area:** API design / maintainability

Paths are unversioned (`/auth/*`, `/api/me`), there is no schema generation
package or committed OpenAPI document, and there is no pagination/filtering
configuration. The contract currently lives in README/LOCAL_USAGE and this
inventory.

**Impact:** breaking changes are hard to stage; frontend code generation and
contract tests must be handwritten; future list endpoints have no established
shape.

**Suggested resolution:** introduce a version prefix or version header before
the API grows, publish an OpenAPI schema, and define pagination/filter/order
conventions when the first list endpoint is added.

### API-019 — Refresh-token rows are never cleaned up and are not in admin

**Severity:** Low
**Area:** Operations / data retention

Revoked and expired `RefreshToken` rows remain in `refresh_tokens`; there is no
cleanup task or management command. `apps/accounts/admin.py` registers only
`User`, so operators cannot inspect or revoke sessions through admin.

**Impact:** the table grows without bound over time, and support/operations
cannot easily see active sessions or force revocation.

**Suggested resolution:** add a scheduled cleanup for expired/revoked rows
(accounting for `replaced_by` foreign keys), and register a read-only
`RefreshToken` admin or provide a management command for revocation.

### API-020 — `last_login` is never updated

**Severity:** Low
**Area:** User data / admin

`login_user()` uses the custom `authenticate_user()` and `issue_token_pair()`
helpers; it never calls Django’s `login()` or `update_last_login()`. The
`User.last_login` field therefore remains `null` after successful logins.

**Impact:** admin and analytics cannot distinguish users who have logged in from
those who have never logged in. Any future “last active” feature will be
misleading.

**Suggested resolution:** call `django.contrib.auth.models.update_last_login`
on successful login, or explicitly document that the field is unused. Add a
test if the behavior is changed.

### API-021 — CORS policy is narrow and easy to misconfigure

**Severity:** Low
**Area:** CORS / deployment

Defaults:

- only the configured local test origins are allowed by default;
- allowed headers are exactly `authorization` and `content-type`;
- credentials are disabled;
- preflight cache is 24 hours;
- there is no wildcard or subdomain matching.

The HTTP test stack defaults `SECURE_SSL_REDIRECT` to `False`; enable it (and
HSTS) once TLS is terminated in front of the service. When enabled, HTTP
requests redirect to HTTPS before CORS/auth processing.

**Impact:** local/staging frontends are blocked until `CORS_ALLOWED_ORIGINS` is
set correctly. Any added tracing/request-id/CSRF/custom header breaks preflight
until `CORS_ALLOW_HEADERS` is extended. If HTTPS redirect is enabled while a
frontend still calls HTTP, that frontend gets a redirect instead of an API
response.

**Suggested resolution:** document per-environment origin/header values, add
preflight tests using the actual frontend headers, and ensure the frontend uses
HTTPS in production. If custom headers are required, add them deliberately
rather than allowing all headers.

### API-022 — `OPTIONS`/`HEAD` behavior is non-obvious

**Severity:** Low
**Area:** HTTP semantics

Observed behavior:

- `OPTIONS /api/me` without CORS preflight headers → `401` (authentication is
  checked by DRF metadata handling).
- `OPTIONS /api/me` with a valid Bearer token → `200` DRF metadata.
- `OPTIONS /api/me` with `Origin` + `Access-Control-Request-Method` → `200`,
  empty body, CORS headers, no auth (middleware short-circuit).
- `OPTIONS /auth/check` → `200` DRF metadata without auth, no CORS headers.
- `HEAD /api/me` with a token → `200` empty body; `HEAD /auth/check` → `405`.

**Impact:** API clients, test tools, and documentation generators may see
different `OPTIONS` results depending on headers. A frontend preflight works,
but a manual `OPTIONS` probe may look like an auth failure.

**Suggested resolution:** keep the middleware behavior, document the distinction
(done in the inventory), and add tests for preflight vs. non-preflight
`OPTIONS` if clients depend on metadata.

### API-023 — `countryCode` input formats are under-specified

**Severity:** Low
**Area:** Phone validation

`normalize_phone()` accepts:

- an ISO 3166-1 alpha-2 region such as `"US"` (case-insensitive),
- a dialing code with optional `+`, such as `"1"` or `"+1"`,
- an international `phone` starting with `+` or `00` (country code ignored),

but a three-letter region such as `"USA"` fails, and the serializer only
enforces `max_length=8` before normalization. The docs show `"US"` and `"+1"`
examples but do not define the complete accepted set.

**Impact:** a frontend country picker that sends `"USA"`, `"United States"`, or
an arbitrary dial-code string may get a generic `400 validation_error` with no
field detail (see API-001).

**Suggested resolution:** document the accepted formats precisely and validate
them explicitly with useful errors. Add tests for alpha-2, alpha-3, dialing
codes with/without `+`, `00` prefixes, and punctuation.

## Coverage notes

- Every body-bearing endpoint has a request serializer, and the `User` payload
  has a response serializer (`UserSerializer`). Simple success envelopes such as
  `{"status": "ok"}`, `{"exists": ...}`, and `{"success": true}` are returned as
  plain dictionaries. No exposed payload lacks a defined serializer.
- `RefreshToken` has no serializer because it is never exposed by the API.
- No pagination, filtering, or ordering serializer/back-end exists.
- No email, SMS, task queue, signal, or outbound HTTP side effect exists in the
  application code.
- Existing tests (147) pass on the current checkout. This chunk did not add or
  modify tests.
