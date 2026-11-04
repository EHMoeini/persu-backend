# API Test Plan

Chunk 2 of 5. This document defines the coverage matrix and test infrastructure.
**No endpoint tests are implemented in this chunk.** The one test in this chunk
is an infrastructure smoke test only.

Reference: `docs/api_inventory.md` (endpoint contract) and
`docs/api_issues.md` (known inconsistencies).

## 1. Goals and constraints

- Assert exact status codes, JSON keys, value types, error codes, messages,
  headers, and database side effects — never merely “no error”.
- Keep every test independent, deterministic, and dependent only on the local
  test database. No external network, email, SMS, cache server, or clock
  service.
- Test the real URL routing, authentication, permissions, serializers, token
  services, throttles, and middleware; do not bypass them with direct view
  calls unless testing a failure-injection case.
- Record contract defects in `docs/api_issues.md`; do not change production
  code to make a test pass.
- Cover both success and failure paths for all 11 method endpoints on 10 paths.

## 2. Test stack and commands

| Item | Choice |
|---|---|
| Runner | pytest 8 + pytest-django |
| HTTP client | DRF `APIClient` |
| Fixtures/factories | pytest fixtures + factory_boy `DjangoModelFactory` |
| Database | Django test database (SQLite by default) |
| Settings | `config/settings_test.py` |
| Legacy suite | Still runnable with `manage.py test` |

Install and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/api/accounts/test_auth_check.py -v
.\.venv\Scripts\python.exe manage.py test          # existing Django-runner suite
```

`pytest.ini` sets `DJANGO_SETTINGS_MODULE=config.settings_test`, discovers only
`tests/`, and adds the repository root to `pythonpath`.

## 3. Infrastructure layout

```text
config/settings_test.py       pytest-only settings
pytest.ini                    pytest-django configuration
requirements-test.txt         test-only dependencies
tests/
  __init__.py
  conftest.py                 shared fixtures and authenticated clients
  factories.py                UserFactory, RefreshTokenFactory
  test_infrastructure.py      one smoke test
  api/
    common/                   test_health.py (later chunk)
    accounts/                 test_auth_check.py, test_login.py, ...
    resources/                test_me.py (later chunk)
```

### Test settings

`config/settings_test.py` inherits production settings and overrides only
test-environment concerns:

- `DEBUG=False` so 404/500 handlers are exercised (tests that need `DEBUG=True`
  use `override_settings`).
- `SECURE_SSL_REDIRECT=False`, HSTS/cookie-secure flags off, so HTTP test-client
  requests are not redirected.
- `PASSWORD_HASHERS=[MD5]` for speed. Tests that specifically assert Argon2id
  hashing must use `override_settings(PASSWORD_HASHERS=[...])`.
- Explicit local-memory cache `persu-api-tests`.
- Local-memory email backend (no network).
- `ALLOWED_HOSTS` includes `testserver`.

### Factories

`UserFactory`:

- Unique, valid US E.164 phone numbers: `+1202555xxxx` via a sequence.
- Default password `correct horse battery staple`; stored as a hash.
- Traits `inactive=True` and `staff=True`.
- `skip_postgeneration_save=True` with an explicit password save hook.

`RefreshTokenFactory`:

- Creates a `RefreshToken` row with a unique SHA-256 `token_hash`, a family ID,
  and a 30-day expiry.
- Does not retain the raw token. Tests that need a raw token call
  `issue_token_pair()`/`generate_refresh_token()` from the token service.

### Authenticated clients and roles

| Fixture | User / credentials |
|---|---|
| `api_client` | anonymous `APIClient` |
| `user` | active user |
| `auth_client` | active user + fresh Bearer access JWT |
| `other_user` | second active user |
| `other_auth_client` | second active user + Bearer access JWT |
| `inactive_user` | `is_active=False` |
| `inactive_auth_client` | inactive user + Bearer token (must be rejected) |
| `staff_user` | active `is_staff=True` user |
| `staff_auth_client` | staff user + Bearer token (no special API permission) |
| `bearer_token` | raw access JWT for `user` |
| `token_pair` | raw access + refresh tokens for `user` |
| `auth_client_for` | factory function `make(user) -> APIClient` |

All clients use `Authorization: Bearer <token>`. The API has no cookie/session
role and no staff-only endpoint; staff is tested to prove it does **not** get
extra API privileges.

### Isolation

- pytest-django wraps each DB test in a transaction and rolls it back.
- `clear_throttle_cache` is autouse and clears the locmem cache before and after
  every test.
- Tests that need a throttle boundary clear the cache explicitly, then make
  exactly the allowed number of requests and assert the next response is `429`
  with `Retry-After`.
- No test depends on execution order, real time, network, or another test’s
  database rows.

## 4. Test-ID convention

- Cross-cutting: `X-<area>-<nn>` (for example `X-ERR-01`).
- Endpoint: `<PREFIX>-<scenario>-<nn>`.
- Prefixes: `HLT` health, `CHK` check, `LGN` login, `REG` register, `RFH` refresh,
  `LGO` logout, `SES` session, `OTS` OTP send, `OTV` OTP verify, `MEG` GET /api/me,
  `MEP` PATCH /api/me.
- Scenario tags: `HP` happy path, `VAL` validation, `AUTH` authentication/
  authorization/roles, `HTTP` routing/method/media, `LIST` pagination/filtering/
  sorting/empty, `IDEM` duplicates/idempotency, `DB` side effects/transactions,
  `BIZ` endpoint business rules.

## 5. Coverage matrix

`N/A` means the scenario does not exist because there are no list endpoints or
no create/delete operation. The cross-cutting `X-LIST-01` test still asserts that
query parameters are ignored and no pagination envelope appears.

| Endpoint | Happy path / exact shape | Validation | Auth / roles / other-user data | 404 / 405 / 415 | Pagination / filter / sort / empty | Duplicate / idempotency | DB side effects / transactions | Business rules |
|---|---|---|---|---|---|---|---|---|
| `GET /healthz` (HLT) | `HLT-HP-01` 200, exact `{"status":"ok"}`, JSON content type | `HLT-VAL-01` no body; query params ignored | `HLT-AUTH-01` public; invalid Authorization still 200; no CORS | `HLT-HTTP-01` POST/PUT/PATCH/DELETE 405 + `Allow`; HEAD 200; OPTIONS 200 | `HLT-LIST-01` N/A; query params ignored | `HLT-IDEM-01` repeat GET identical | `HLT-DB-01` no rows written | `HLT-BIZ-01` liveness independent of DB/auth |
| `POST /auth/check` (CHK) | `CHK-HP-01` existing/unknown, exact boolean body; normalized formats | `CHK-VAL-01` missing/blank/over-length/wrong-type phone or countryCode; invalid phone; malformed JSON | `CHK-AUTH-01` public; bad Authorization ignored; inactive user still “exists” | `CHK-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS metadata; 415 text/plain; trailing-slash 404 | `CHK-LIST-01` N/A; query params ignored | `CHK-IDEM-01` repeated checks identical; no writes | `CHK-DB-01` `User` count/rows unchanged | `CHK-BIZ-01` E.164 normalization, `+`/`00`/alpha-2/dial-code inputs; throttle 10/min |
| `POST /auth/login` (LGN) | `LGN-HP-01` 200, exact 3 keys, user shape, JWT claims, refresh row | `LGN-VAL-01` missing/blank/over-length/wrong-type fields; invalid phone; malformed JSON; 415 | `LGN-AUTH-01` public; generic 401 for unknown/wrong/inactive; no enumeration; no CORS | `LGN-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `LGN-LIST-01` N/A; query params ignored | `LGN-IDEM-01` second login revokes first family; old refresh 401; old access still 200 | `LGN-DB-01` active refresh rows revoked, exactly one new row, no `last_login` change | `LGN-BIZ-01` password spaces preserved; throttle 5/min; one session per user |
| `POST /auth/register` (REG) | `REG-HP-01` 201, exact 3 keys, user shape, hash + refresh row | `REG-VAL-01` missing/blank/over-length/wrong-type fields; invalid phone; 128/129 password; malformed JSON; 415 | `REG-AUTH-01` public; bad Authorization ignored; no CORS | `REG-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `REG-LIST-01` N/A; query params ignored | `REG-IDEM-01` duplicate phone 409; normalized duplicate 409; no extra rows | `REG-DB-01` user + refresh row; password not plaintext; no email/SMS | `REG-BIZ-01` phone uniqueness; 1-char password accepted (documented issue); unknown fields ignored |
| `POST /auth/refresh` (RFH) | `RFH-HP-01` 200, exact 2 keys, no `user`, new token differs | `RFH-VAL-01` missing/blank/over-512/wrong-type token; malformed JSON; 415 | `RFH-AUTH-01` public; no Bearer required; access token as refresh 401; invalid/expired/revoked/reused 401 | `RFH-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `RFH-LIST-01` N/A; query params ignored | `RFH-IDEM-01` rotate once; reuse old token revokes family; new token then 401 | `RFH-DB-01` old row revoked + `replaced_by`; new row same family; transaction | `RFH-BIZ-01` sliding TTL; inactive user revokes family; 20/min per token |
| `POST /auth/logout` (LGO) | `LGO-HP-01` 204 empty body; family revoked | `LGO-VAL-01` missing/blank/over-512/wrong-type token; malformed JSON; 415 | `LGO-AUTH-01` public; no Bearer required; bad Authorization ignored; no CORS | `LGO-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `LGO-LIST-01` N/A; query params ignored | `LGO-IDEM-01` repeat 204; unknown token 204; after logout repeat 204 | `LGO-DB-01` family `revoked_at` set; unknown token no writes; other family unaffected | `LGO-BIZ-01` idempotent; access token still valid after logout (documented) |
| `GET /auth/session` (SES) | `SES-HP-01` 200, exact `{"user": ...}`; optional fields | `SES-VAL-01` no body; query params ignored | `SES-AUTH-01` anon/invalid/expired/inactive 401; staff same as active; other-user token returns that user | `SES-HTTP-01` POST/PUT/PATCH/DELETE 405 + `Allow`; OPTIONS with/without token; trailing-slash 404; no CORS | `SES-LIST-01` N/A; query params ignored | `SES-IDEM-01` repeat GET identical; no writes | `SES-DB-01` no rows written | `SES-BIZ-01` token `sub` is source of truth; deleted user 401; refresh token rejected as Bearer |
| `POST /auth/otp/send` (OTS) | `OTS-HP-01` 200 exact `{"success":true}` | `OTS-VAL-01` missing/invalid/over-length/wrong-type phone/country; malformed JSON; 415 | `OTS-AUTH-01` public; bad Authorization ignored; no CORS | `OTS-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `OTS-LIST-01` N/A; query params ignored | `OTS-IDEM-01` repeat 200; no OTP state | `OTS-DB-01` no user/refresh/OTP rows; no email/SMS | `OTS-BIZ-01` stub always succeeds; throttle 5/min |
| `POST /auth/otp/verify` (OTV) | `OTV-HP-01` 200 exact `{"success":true}` with code, without code, nonsense code | `OTV-VAL-01` missing/invalid phone/country; code over 16; wrong types; malformed JSON; 415 | `OTV-AUTH-01` public; no CORS | `OTV-HTTP-01` GET/PUT/PATCH/DELETE 405; OPTIONS; trailing-slash 404 | `OTV-LIST-01` N/A; query params ignored | `OTV-IDEM-01` repeat 200; no session/token | `OTV-DB-01` no rows written | `OTV-BIZ-01` code ignored; never authenticates; throttle 10/min |
| `GET /api/me` (MEG) | `MEG-HP-01` 200 exact user shape; optional fields present/omitted | `MEG-VAL-01` no body; query params ignored; Accept html 406 | `MEG-AUTH-01` anon/invalid/expired/inactive 401; staff same; other-user token returns other user; `X-User-Id` ignored | `MEG-HTTP-01` POST/PUT/DELETE 405 with token, 401 without; OPTIONS preflight/no-preflight; trailing-slash 404; CORS allowed/disallowed | `MEG-LIST-01` N/A; query params ignored | `MEG-IDEM-01` repeat GET identical; no writes | `MEG-DB-01` no rows written | `MEG-BIZ-01` no cross-user access; token subject authoritative |
| `PATCH /api/me` (MEP) | `MEP-HP-01` 200 exact user shape; one/both fields; blank clears; trim | `MEP-VAL-01` null/wrong-type/64-65 nick; invalid/500-501 avatar; unknown fields ignored; malformed JSON; 415 | `MEP-AUTH-01` anon/invalid/expired/inactive 401; staff same; other-user token updates only that user | `MEP-HTTP-01` GET/POST/PUT/DELETE 405 with token, 401 without; OPTIONS; trailing-slash 404; CORS | `MEP-LIST-01` N/A; query params ignored | `MEP-IDEM-01` same payload twice same result; `{}` no-op; no duplicate rows | `MEP-DB-01` only target user’s `nick_name/avatar/updated_at`; invalid request leaves unchanged | `MEP-BIZ-01` phone/id immutable; unknown case-sensitive fields ignored; ftp avatar accepted (issue); no email |

## 6. Cross-cutting scenarios

These are implemented as shared tests/helpers and applied to every endpoint
where meaningful.

### Error envelope and statuses

- `X-ERR-01` Every JSON error has exactly `{"error": {"code": string,
  "message": string}}`; no extra top-level or nested keys. Assert `type(code)`
  and `type(message)`.
- `X-ERR-02` `400 invalid_json` for malformed JSON on every POST/PATCH body
  endpoint; exact message `Malformed JSON request.`; DB unchanged.
- `X-ERR-03` `401` matrix:
  - no credentials → `unauthorized` / `Authentication required.` /
    `WWW-Authenticate: Bearer realm="api"`;
  - malformed Bearer header → `unauthorized` / `Authentication failed.` /
    challenge;
  - invalid signature, expired access token, refresh token as Bearer, deleted
    user, inactive user → `unauthorized` / `Authentication failed.` / challenge;
  - login bad credentials → `invalid_credentials` / exact message, no challenge;
  - refresh bad token → `invalid_refresh_token` / exact message, no challenge.
- `X-ERR-04` `403 forbidden` is documented as reserved; no API endpoint should
  return it in the current contract. This is a known issue, not a passing
  requirement.
- `X-ERR-05` `404 not_found` for unknown paths under `/api`, `/auth`, and `/`;
  exact body; `DEBUG=False` JSON and `DEBUG=True` HTML technical page are both
  asserted to document the environment difference. Under `/api`, CORS headers
  are present for an allowed origin.
- `X-ERR-06` `405 method_not_allowed` for each wrong method on each path; exact
  body and `Allow` header. On protected paths, assert `401` without credentials
  and `405` with credentials.
- `X-ERR-07` `415 unsupported_media_type` for `text/plain` bodies; exact body.
- `X-ERR-08` `406` for `Accept: text/html`; status `406`, body code
  `bad_request` (documented issue).
- `X-ERR-09` `409 phone_already_registered` only for duplicate registration;
  exact code/message.
- `X-ERR-10` `429 rate_limited` after the exact limit; `Retry-After` integer
  header; other phone/token buckets unaffected.
- `X-ERR-11` Mock an unhandled exception in a view and assert `500
  internal_error`; no stack trace or internal detail leaks.

### Routing, methods, content types

- `X-ROUTE-01` Trailing slash on each path → `404` (`JSON` at `DEBUG=False`).
- `X-ROUTE-02` Exact paths resolve; unknown subpaths do not.
- `X-MEDIA-01` JSON body accepted; form-urlencoded and multipart also accepted
  by the current DRF defaults; `text/plain` → `415`. Tests should pin the
  documented choice once the parser policy is decided.
- `X-METHOD-01` `HEAD` on GET endpoints → same status/headers, empty body;
  `HEAD` on POST-only endpoints → `405`.
- `X-OPTIONS-01` Preflight `OPTIONS /api/me` → `200`, empty body, CORS headers,
  no auth. Non-preflight `OPTIONS /api/me` without token → `401`; with token →
  `200` metadata. Public auth `OPTIONS` → `200` metadata, no CORS.

### Pagination, filtering, sorting, empty results

- `X-LIST-01` There are no list endpoints. For every endpoint, append
  `?page=1&limit=1&offset=0&search=x&ordering=-id&foo=bar` and assert the
  response is unchanged; no `count/next/previous/results` keys, no `Link`,
  `X-Total-Count`, or pagination headers.
- `X-LIST-02` “Empty results” is N/A until a list endpoint exists. If one is
  added, require a test for an empty collection with exact `results: []`,
  `count: 0`, `next: null`, `previous: null` (or the chosen convention).

### Duplicates and idempotency

- `X-IDEM-01` GET/check/OTP calls are repeatable with identical bodies.
- `X-IDEM-02` Login is intentionally not idempotent: a second login revokes the
  first refresh family. Assert this explicitly.
- `X-IDEM-03` Register duplicate → `409`, no second user/refresh row.
- `X-IDEM-04` Refresh is intentionally not idempotent: old token reuse → `401`
  and family revocation.
- `X-IDEM-05` Logout is idempotent: repeat with the same or unknown token → `204`.
- `X-IDEM-06` PATCH is idempotent for the same payload; `{}` is a no-op.
- `X-IDEM-07` DELETE is not implemented; assert `405` on every path.

### CORS, CSRF, and security headers

- `X-CORS-01` Allowed origin `https://app.example.com` on `/api/me` GET/PATCH
  and on `401`/`400`/`404` responses → exact `Access-Control-Allow-Origin`,
  `Vary: Origin`, no `Access-Control-Allow-Credentials`.
- `X-CORS-02` Disallowed origin → no `Access-Control-Allow-Origin`; server still
  processes the request.
- `X-CORS-03` `/auth/*` and `/healthz` → no CORS headers, including preflight.
- `X-CORS-04` Preflight for `PATCH` and `authorization,content-type` → `200`,
  allowed methods/headers, `Access-Control-Max-Age: 86400`.
- `X-CSRF-01` No CSRF token required for `/api/*` or `/auth/*`; requests with or
  without cookies behave the same because only Bearer authentication is active.
- `X-SEC-01` In production-style settings, HTTP is redirected to HTTPS
  (`SECURE_SSL_REDIRECT`); test settings disable this so assertions are not
  masked by redirects.

### Throttling

- `X-THROTTLE-01` Clear cache; make exactly the allowed number of requests;
  next request is `429` with `Retry-After`; a different phone/token still
  succeeds.
- `X-THROTTLE-02` Invalid phone numbers share the caller-IP bucket.
- `X-THROTTLE-03` Throttle applies before serializer validation for valid JSON
  requests with invalid field values.
- `X-THROTTLE-04` No throttle on `/healthz`, `/auth/session`, `/api/me`.
- `X-THROTTLE-05` Shared-cache caveat is documented but not simulated; tests use
  the locmem cache and must not assume cross-process enforcement.

## 7. Endpoint-specific scenarios

### HLT — `GET /healthz`

- `HLT-HP-01`: 200; exact `{"status": "ok"}`; `Content-Type:
  application/json`; no auth header needed.
- `HLT-AUTH-01`: `Authorization: Bearer garbage` still 200 (authentication
  classes are empty).
- `HLT-HTTP-01`: POST/PUT/PATCH/DELETE → 405 with `Allow: GET, HEAD, OPTIONS`;
  HEAD → 200 empty; OPTIONS → 200 metadata; trailing slash → 404.
- `HLT-LIST-01`: query params ignored; no CORS headers.
- `HLT-DB-01`: no `User`/`RefreshToken` row changes.

### CHK — `POST /auth/check`

- `CHK-HP-01`: registered phone → `{"exists": true}`; unknown valid phone →
  `{"exists": false}`; inactive registered user still → `true` (`phone_exists`
  does not filter `is_active`).
- `CHK-HP-02`: normalization cases: `US` + `2024561111`, `+1` + punctuation,
  `1` + digits, international `+...`, `00...`; all return the same boolean.
- `CHK-VAL-01`: `{}`; missing one field; blank strings; `countryCode` > 8;
  `phone` > 32; invalid phone; invalid country; JSON booleans/lists/objects;
  numeric scalars (assert the actual DRF coercion behavior).
- `CHK-VAL-02`: malformed JSON → `400 invalid_json`; `text/plain` → `415`.
- `CHK-AUTH-01`: no auth/bad auth header → still 200; no CORS; inactive user
  semantics as above.
- `CHK-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS → 200 metadata; trailing
  slash → 404.
- `CHK-IDEM-01`: repeat same request → identical body; no DB writes.
- `CHK-BIZ-01`: throttle 10/min per normalized phone; 11th → 429; different
  phone unaffected; invalid phone attempts share IP bucket.

### LGN — `POST /auth/login`

- `LGN-HP-01`: 200; exactly `{accessToken, refreshToken, user}`; `user` has
  `{id, phone}` (plus optional fields when set); tokens are non-empty strings;
  access token decodes with `sub == user.id`; one active refresh row.
- `LGN-HP-02`: phone normalization and password punctuation/spaces; password
  `" pw "` must match only the exact stored value.
- `LGN-VAL-01`: missing/blank/over-128 password; missing phone/country;
  over-length values; wrong types; JSON booleans/lists/objects; malformed JSON;
  `415`.
- `LGN-AUTH-01`: unknown phone, wrong password, and inactive user all return the
  same `401 invalid_credentials` body (no enumeration). No CORS.
- `LGN-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `LGN-IDEM-01`: login twice → second succeeds; first refresh token → `401`;
  second refresh token works; first access token still works (stateless).
- `LGN-DB-01`: before/after active refresh count; old rows `revoked_at` set;
  exactly one active row; `last_login` remains unchanged (documented issue);
  no email/SMS.
- `LGN-BIZ-01`: throttle 5/min per phone; 6th → 429; different phone unaffected.

### REG — `POST /auth/register`

- `REG-HP-01`: 201; exact token response; `user` shape; password stored as a
  hash, not plaintext; one active refresh row; access token works on
  `/api/me`.
- `REG-VAL-01`: missing/blank fields; invalid phone; password 128 accepted,
  129 rejected; whitespace-only rejected; 1-char password accepted (known
  issue); wrong types; malformed JSON; `415`.
- `REG-AUTH-01`: public; bad Authorization ignored; no CORS.
- `REG-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `REG-IDEM-01`: duplicate same normalized phone → `409`; duplicate across
  formats → `409`; no extra user or refresh row; later login still works.
- `REG-DB-01`: one `User` row, one `RefreshToken` row; no email/SMS; simulate
  token-issuance failure to expose the non-atomic user/token gap (API-016).
- `REG-BIZ-01`: phone uniqueness; unknown fields ignored; one active family;
  throttle 5/min.

### RFH — `POST /auth/refresh`

- `RFH-HP-01`: 200; exactly `{accessToken, refreshToken}`; no `user`; new
  refresh token differs; access token decodes to same user; same family ID.
- `RFH-VAL-01`: missing/blank/over-512/wrong-type token; malformed JSON; `415`.
- `RFH-AUTH-01`: no Bearer required; an access token sent as `refreshToken` →
  `401 invalid_refresh_token`; unknown/expired/revoked/reused → `401`; inactive
  user → `401` and family revoked.
- `RFH-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `RFH-IDEM-01`: rotate once succeeds; reuse old token → `401 invalid_refresh_token`;
  the newly rotated token then also → `401` because the family was revoked;
  no further refresh works.
- `RFH-DB-01`: old row `revoked_at` set and `replaced_by` points to new row;
  new row has same `family_id`; no new family; transaction rollback on failure.
- `RFH-BIZ-01`: sliding 30-day expiry; refresh response has no user; throttle
  20/min per presented token.

### LGO — `POST /auth/logout`

- `LGO-HP-01`: 204; empty body; subsequent refresh with the same token → `401`;
  access token still works on `/api/me` (documented).
- `LGO-VAL-01`: missing/blank/over-512/wrong-type token; malformed JSON; `415`.
- `LGO-AUTH-01`: public; no Bearer required; bad Authorization ignored; no CORS.
- `LGO-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `LGO-IDEM-01`: same token twice → 204; unknown non-empty token → 204; blank
  still `400` via serializer; no DB writes for unknown token.
- `LGO-DB-01`: presented family `revoked_at` set; a second independently created
  family (via `issue_token_pair(revoke_existing=False)`) is unaffected.
- `LGO-BIZ-01`: idempotent; access token not revoked; throttle 30/min per token.

### SES — `GET /auth/session`

- `SES-HP-01`: 200; exactly `{"user": ...}`; `id` string equals token subject;
  optional `nickName`/`avatar` present/omitted; no internal fields.
- `SES-AUTH-01`: missing/invalid/expired/wrong-type token, refresh token as
  Bearer, inactive user, deleted user → `401 unauthorized`; staff same as active;
  other-user token returns that other user, never a fixed/request-supplied user.
- `SES-HTTP-01`: POST/PUT/PATCH/DELETE with token → 405 + Allow; without token
  → 401; OPTIONS with token → 200 metadata, without → 401; trailing slash → 404;
  no CORS.
- `SES-VAL-01`: no body; query params ignored.
- `SES-IDEM-01` / `SES-DB-01`: repeat GET identical; no DB writes.
- `SES-BIZ-01`: token `sub` authoritative; `X-User-Id` header ignored.

### OTS — `POST /auth/otp/send`

- `OTS-HP-01`: 200 exact `{"success": true}`; no token/session.
- `OTS-VAL-01`: missing/invalid phone/country; over-length; wrong types;
  malformed JSON; `415`.
- `OTS-AUTH-01`: public; bad Authorization ignored; no CORS.
- `OTS-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `OTS-IDEM-01` / `OTS-DB-01`: repeat 200; no OTP rows, no user/refresh writes,
  no email/SMS.
- `OTS-BIZ-01`: stub always succeeds; throttle 5/min per phone.

### OTV — `POST /auth/otp/verify`

- `OTV-HP-01`: 200 exact `{"success": true}` with a code, without `code`, and
  with nonsense code; never returns tokens or sets a session.
- `OTV-VAL-01`: missing/invalid phone/country; `code` 16 accepted, 17 rejected;
  blank code accepted; wrong types; malformed JSON; `415`.
- `OTV-AUTH-01`: public; no CORS.
- `OTV-HTTP-01`: GET/PUT/PATCH/DELETE → 405; OPTIONS; trailing slash → 404.
- `OTV-IDEM-01` / `OTV-DB-01`: repeat 200; no DB writes.
- `OTV-BIZ-01`: code ignored; does not authenticate; throttle 10/min.

### MEG — `GET /api/me`

- `MEG-HP-01`: 200; exact `{"user": ...}`; optional fields; own data only.
- `MEG-AUTH-01`: anon/invalid/expired/wrong-type/inactive → 401; staff same as
  active; other-user token returns other user; `X-User-Id` header ignored.
- `MEG-HTTP-01`: POST/PUT/DELETE with token → 405 + Allow; without token → 401;
  OPTIONS preflight → 200 empty + CORS, non-preflight without token → 401, with
  token → 200 metadata; trailing slash → 404; CORS allowed/disallowed.
- `MEG-VAL-01`: no body; query params ignored; `Accept: text/html` → 406
  `bad_request` (documented).
- `MEG-IDEM-01` / `MEG-DB-01`: repeat GET identical; no DB writes.
- `MEG-BIZ-01`: no cross-user access; token subject authoritative.

### MEP — `PATCH /api/me`

- `MEP-HP-01`: 200; exact `{"user": ...}`; one field and both fields; response
  reflects changes; DB reflects changes.
- `MEP-HP-02`: blank `nickName`/`avatar` clears and omits from response;
  surrounding whitespace trimmed; `{}` returns current user unchanged.
- `MEP-VAL-01`: `null` values → 400; wrong types → 400; 64-char nick accepted,
  65 → 400; valid 500-char avatar accepted, 501 → 400; invalid avatar → 400;
  `ftp://` accepted (documented issue); `javascript:` rejected; unknown fields
  ignored (assert known fields still apply); `phone`/`id` cannot change;
  malformed JSON → `400 invalid_json`; `text/plain` → `415`.
- `MEP-AUTH-01`: anon/invalid/expired/inactive → 401; staff same as active;
  other-user token updates only the other user; `X-User-Id` ignored.
- `MEP-HTTP-01`: GET/POST/PUT/DELETE with token → 405 + Allow; without token
  → 401; OPTIONS; trailing slash → 404; CORS.
- `MEP-IDEM-01`: same payload twice → same response and DB state; no duplicate
  rows.
- `MEP-DB-01`: only target user’s `nick_name`, `avatar`, `updated_at` change;
  invalid request leaves all fields unchanged; no email/task.
- `MEP-BIZ-01`: field case sensitivity (`nickName`, not `nickname`); avatar
  schemes; blank-clears; only own profile.

## 8. Role and access matrix

| Caller | `/healthz` | Public auth (`check/login/register/refresh/logout/otp/*`) | `/auth/session` | `/api/me` |
|---|---|---|---|---|
| Anonymous | 200 | Contract-specific (usually 200/201/400/401) | 401 | 401 |
| Active user | 200 | Same as anonymous; auth header ignored | 200 own user | 200 own user |
| Other active user | 200 | Same as anonymous | 200 that user | 200 that user; no cross-user data |
| Inactive user | 200 | Login/refresh behave as documented 401; check still sees existence | 401 | 401 |
| Staff user | 200 | Same as active; no special API permission | 200 own user | 200 own user |
| Deleted user (valid token) | 200 | Login 401; refresh 401 | 401 | 401 |
| Missing/invalid Bearer | 200 | Public routes ignore it | 401 | 401 |

No endpoint accepts a user ID in the path or body for data access. “Access to
another user’s data” is tested by issuing a token for user B and asserting that
`/auth/session` and `/api/me` return B, and that a PATCH by B changes only B.
`X-User-Id` and body `id`/`phone` must never redirect the operation to user A.

## 9. Database side-effect matrix

| Operation | Expected rows/fields | Must not happen |
|---|---|---|
| `GET /healthz` | none | any DB write |
| `POST /auth/check` | none | user creation/update |
| `POST /auth/login` | all active refresh rows for user revoked; one new active row; new family | `last_login` update (current behavior), duplicate user |
| `POST /auth/register` | one user, one active refresh row, password hash | plaintext password, email/SMS, duplicate user on retry |
| `POST /auth/refresh` | one new refresh row same family; old row revoked and linked | new family, extra active rows, user change |
| `POST /auth/logout` | family `revoked_at` set | deletion of rows, access-token state change |
| `GET /auth/session` | none | any DB write |
| `POST /auth/otp/send` | none | OTP/SMS/user/token rows |
| `POST /auth/otp/verify` | none | session/token issuance |
| `GET /api/me` | none | any DB write |
| `PATCH /api/me` | target user’s `nick_name`, `avatar`, `updated_at` | changes to another user, id/phone, password |

Transaction tests:

- Duplicate registration must leave the DB usable for a later request.
- Refresh reuse must revoke the family atomically; no partially rotated row.
- A simulated token-issuance failure during registration should expose the
  current non-atomic gap (API-016) rather than silently pass.
- Invalid PATCH/validation must leave the user row byte-for-byte unchanged
  (except no `updated_at` bump).
- Unknown-token logout must not create/update rows.

## 10. Endpoint-specific business rules to pin

- Phone normalization is shared by check/login/register/OTP; test `US`,
  `+1`, punctuation, `00` prefix, alpha-2, missing/invalid country code.
- `phone_exists` does not filter `is_active`; inactive accounts still return
  `exists: true`.
- Login and register revoke existing refresh families; second login invalidates
  the first refresh token but not the first access token.
- Refresh reuse revokes the whole family; an expired token does not rotate.
- Logout is idempotent for unknown non-empty tokens; blank is still `400`.
- OTP endpoints are stubs; success does not imply authentication.
- `/api/me` is always the token subject; no path/body ID can select another user.
- PATCH only accepts `nickName` and `avatar`; empty string clears, `null` is
  invalid, unknown fields are ignored.
- Error codes `invalid_credentials`, `invalid_refresh_token`, `unauthorized`,
  and `validation_error` are distinct and must be asserted exactly.
- Rate limits: check 10/min, login 5/min, register 5/min, refresh 20/min,
  logout 30/min, OTP send 5/min, OTP verify 10/min.

## 11. Known issues that tests must expose, not hide

These are already documented in `docs/api_issues.md`; tests should assert the
current behavior and fail if the contract changes without an explicit decision:

- `API-001`: field-level validation details are absent.
- `API-002`: `DEBUG=True` unknown routes return HTML, not JSON.
- `API-003`: OTP endpoints always succeed and issue no session.
- `API-004`: 1-character passwords are accepted.
- `API-005`: unknown fields are silently ignored.
- `API-006`: `406` body code is `bad_request`.
- `API-007`: `403` is unreachable; `IsOwner` is unused.
- `API-008`: 401 codes/messages and `WWW-Authenticate` differ by source.
- `API-009`: no token expiry metadata.
- `API-010`: access tokens survive logout/second login.
- `API-011`: one refresh family per user.
- `API-012`: `/auth/*` has no CORS.
- `API-013`: trailing slash → 404.
- `API-014`: form/multipart bodies are accepted despite JSON docs.
- `API-015`: `ftp`/`ftps` avatars accepted; blank clears.
- `API-016`: registration is not atomic across user/token.
- `API-017`: per-phone throttle lockout/enumeration.
- `API-018`–`API-023`: versioning/schema, cleanup, `last_login`, CORS narrowness,
  OPTIONS/HEAD semantics, `countryCode` formats.

## 12. Exit criteria for chunks 3–5

- Every row in the coverage matrix has at least one corresponding test, except
  explicitly marked N/A list/delete scenarios.
- Every test asserts exact status, body keys, value types, error code/message,
  relevant headers, and DB state.
- Full suite passes from a clean test database with no network access.
- Legacy `manage.py test` still passes (or any intentional incompatibility is
  documented).
- No production code changed to make a test pass.
- New contract defects discovered during implementation are added to
  `docs/api_issues.md`.
