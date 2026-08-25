# Student 1 tests

Real pytest suite (51 tests) covering the database and backend services in isolation.

- `test_database_profiles.py` / `test_database_resumes.py` — run the database service's
  Flask app directly against a throwaway per-test SQLite file (via `db_client`).
- `test_backend_profiles.py` / `test_backend_resumes.py` — run the backend service's
  Flask app directly (via `backend_client`), with outbound calls to shared-api and the
  database service faked via `requests_mock`. `auth_headers` attaches a session cookie
  to the test client (Werkzeug's test client requires `set_cookie`, not a `Cookie` header).

## Feature coverage

Mapping of registration-form features to the test files that exercise them.

| Feature (registration form) | Layer | Test file | Coverage |
|---|---|---|---|
| Create / View / Edit / Delete Profile | Database (CRUD, validation, cascade delete) | `test_database_profiles.py` | Full |
| Create / View / Edit / Delete Profile | Backend (session auth, ownership checks) | `test_backend_profiles.py` | Partial — success/forbidden paths only, no upstream-404 propagation |
| Create / View / Edit / Delete Profile | Frontend (`proxy_profiles*`, `profile.html`) | none | Missing |
| Upload / View Stored Resume / Delete Stored Resume | Database (CRUD, file-type/size/base64 validation, cascade) | `test_database_resumes.py` | Full |
| Upload / View Stored Resume / Delete Stored Resume | Backend (role + ownership checks, JSON upload path) | `test_backend_resumes.py` | Partial — only the JSON `file_data` path is exercised |
| Upload / View Stored Resume / Delete Stored Resume | Frontend (`proxy_resumes`, multipart upload proxying) | none | Missing |
| Update user details (first/last name) | Backend (`PUT /api/user` → shared-api) | `test_backend_profiles.py::test_update_user_identity_proxies_to_shared_api` | Partial — success path only |
| Logout | Backend (`POST /api/auth/logout` → shared-api) | none | Missing |
| Logout | Frontend (`proxy_logout`, session cookie deletion) | none | Missing |
| Review / Accept / Discard AI Profile Autocomplete Suggestions | AI autofill (`ai-services/ai-mode`) | none | Not implemented yet (deferred, see main README) |

## Gaps identified in this review

- **No frontend tests at all.** `student-1/frontend/app.py` (route rendering, static CSS,
  and all `_proxy(...)` reverse-proxy routes including multipart file forwarding and the
  `session_token` cookie deletion on logout) has zero coverage.
- **Backend's own multipart upload validation is untested.** `upload_resume` in
  `student-1/backend/app.py` has a separate `request.files` branch (empty-filename,
  disallowed content-type, 10MB size checks) that every current resume test bypasses by
  posting JSON `file_data` directly instead of a real multipart file.
- **Backend logout endpoint is untested** (`POST /api/auth/logout`).
- **Backend "not found" propagation from the DB service is untested** for
  `get_profile`, `update_profile`, `delete_profile`, `download_resume`, and
  `delete_resume` — existing tests only cover the ownership-forbidden and success paths,
  not the case where the DB service itself returns 404 before an ownership check applies.
- **Database layer only tests a single resume per profile** — no test asserts multiple
  resumes are returned/ordered correctly for one profile.
- **No integration test across the full stack** (frontend → backend → shared-api →
  database via docker-compose); all current tests load each Flask app in isolation.
- AI autofill has no tests, which is expected since the feature is not yet implemented.

## Running locally

```bash
pip install -r requirements.txt
pytest
```

## Not yet wired into CI

`student-1-ci.yml` still only builds images and smoke-checks health endpoints — it does
not run this suite yet.

See [../README.md](../README.md) for known architectural deviations and AI feature status.

