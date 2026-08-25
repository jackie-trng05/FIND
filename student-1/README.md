# Student 1 — User Profile Management

Applicant profile CRUD and resume storage for the FIND HR application.

## Feature scope (Release 0, AI to be implemented)

- Create / View / Edit / Delete user profile (applicant self-service)
- Upload / View / Download / Delete resume (PDF only; 5MB max)
- Cross-service session via shared HttpOnly cookie (`session_token`)

## Services

| Service | Container | Port (host) | Port (internal) |
|---------|-----------|-------------|-----------------|
| Frontend | find-student-1-frontend | 16004 | 3000 |
| Backend | find-student-1-backend | 16005 | 5001 |
| Database | find-student-1-db | 16006 | 6001 |

## Running locally

```bash
docker compose up --build
```

1. Log in via shared frontend at http://localhost:16001 (e.g. applicant1@email.com / apply123)
2. Navigate to "My Profile" from the dashboard, or go directly to http://localhost:16004

## Authentication

Session is shared via an HttpOnly `session_token` cookie with `domain=localhost`.
The cookie is set on login by shared-api and automatically sent by the browser to all
localhost services. The browser calls `student-1-backend` directly via HTMX
(`hx-get`/`hx-post`/etc.) using that cookie — the frontend is a thin template
shell and does not proxy any calls (same convention as student-2/3).

## Database seeding

`init_db.py` seeds 10 profiles (mapped to shared-db user IDs 1–10) and 10 realistic
resumes (PDF only) from files committed under `database/seed_data/resumes/`.

## Known deviations from the registration form

- Identity fields (first/last name) live on the shared `users` table, not on `profiles`.
- Resumes are stored as a `BLOB` in SQLite (`file_data`), not as a `Resume_FilePath`.
- Resume-level routes are `/resume/{resumeId}` rather than nested under
  `/profile/{id}/resume/{resumeId}`; ownership is still checked server-side.

## AI feature status

The resume-based AI autofill feature (suggest professional title/summary/interests,
review/accept/discard) is **not yet implemented**. It depends on the shared
`ai-services/ai-mode` service, which is currently a placeholder team-wide.