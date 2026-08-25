# Student 1 tests

Real pytest suite (76 tests) covering the frontend, backend, and database services in
isolation.

- `test_database_profiles.py` / `test_database_resumes.py` — run the database service's
  Flask app directly against a throwaway per-test SQLite file (via `db_client`).
- `test_backend_profiles.py` / `test_backend_resumes.py` — run the backend service's
  Flask app directly (via `backend_client`), with outbound calls to shared-api and the
  database service faked via `requests_mock`. `auth_headers` attaches a session cookie
  to the test client (Werkzeug's test client requires `set_cookie`, not a `Cookie` header).
- `test_frontend.py` — runs the frontend service's Flask app directly (via
  `frontend_client`), with outbound proxy calls to the backend faked via `requests_mock`.

## Feature coverage

Mapping of registration-form features to the test files that exercise them.

| Feature (registration form) | Layer | Test file | Coverage |
|---|---|---|---|
| Create / View / Edit / Delete Profile | Database (CRUD, validation, cascade delete) | `test_database_profiles.py` | Full |
| Create / View / Edit / Delete Profile | Backend (session auth, ownership checks, upstream 404 propagation) | `test_backend_profiles.py` | Full |
| Create / View / Edit / Delete Profile | Frontend (`proxy_profiles*`, `profile.html`) | `test_frontend.py` | Full |
| Upload / View Stored Resume / Delete Stored Resume | Database (CRUD, file-type/size/base64 validation, cascade, multiple resumes) | `test_database_resumes.py` | Full |
| Upload / View Stored Resume / Delete Stored Resume | Backend (role + ownership checks, JSON and multipart upload paths, upstream 404 propagation) | `test_backend_resumes.py` | Full |
| Upload / View Stored Resume / Delete Stored Resume | Frontend (`proxy_resumes`, multipart upload proxying) | `test_frontend.py` | Full |
| Update user details (first/last name) | Backend (`PUT /api/user` → shared-api, local blank-name validation) | `test_backend_profiles.py` | Full |
| Logout | Backend (`POST /api/auth/logout` → shared-api) | `test_backend_profiles.py::test_logout_proxies_to_shared_api` | Full |
| Logout | Frontend (`proxy_logout`, session cookie deletion) | `test_frontend.py::test_proxy_logout_clears_session_cookie` | Full |
| Review / Accept / Discard AI Profile Autocomplete Suggestions | AI autofill (`ai-services/ai-mode`) | none | Not implemented yet (deferred, see main README) |

Remaining:

- **No integration test across the full stack** (frontend → backend → shared-api →
  database via docker-compose); all current tests load each Flask app in isolation with
  its outbound calls faked via `requests_mock`. Closing this needs a docker-compose-based
  test run rather than more pytest-level unit tests.
- Found while adding multipart tests: the backend's own 5MB resume size check
  (`upload_resume` in `student-1/backend/app.py`) is unreachable via multipart uploads —
  Flask's `MAX_CONTENT_LENGTH` config rejects an oversized body with `413` before the
  handler's manual `len(file_bytes) > ...` check ever runs. Not a test gap, but worth
  knowing if that error message is ever surfaced to the UI.
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

