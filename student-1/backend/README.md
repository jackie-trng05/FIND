# Student 1 backend

Flask app for the User Profile Customisation feature. Validates the shared session
cookie against `shared-api`, then proxies to `student-1-db` for persistence. Every
route renders an HTML fragment for the HTMX frontend (matching student-2/3's
convention) — there is no JSON API.

Local dev URL: http://localhost:16005/

## Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/user` | User details fragment (first/last name form) |
| PUT | `/user` | Update first/last name on the shared users table |
| GET | `/profile` | Profile fragment (create-prompt or update form + nested resume panel) |
| POST | `/profile` | Create the caller's profile |
| PUT | `/profile/{id}` | Update a profile (owner only) |
| DELETE | `/profile/{id}` | Delete a profile and its resume (owner only) |
| GET | `/resume` | Resume fragment (upload form or resume table) |
| POST | `/resume` | Upload the caller's resume (applicant only, one per profile) |
| DELETE | `/resume/{id}` | Delete a resume (owner only) |
| GET | `/resume/{id}/download` | Download a resume file (owner only, or staff) |

Resume uploads are restricted to PDF and 5MB max, enforced both here and
in `student-1-db`. Code is organised as `routes/` (blueprints), `views/`
(HTML fragment builders), and `services/` (HTTP clients for shared-api/db),
mirroring student-2/3's structure.

## Not yet implemented

- AI resume-analysis endpoint (suggest profile fields from resume content) —
  deferred to a separate branch, blocked on the shared `ai-services/ai-mode` service.

See [../README.md](../README.md) for known architectural deviations and testing status.

