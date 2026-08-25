# Student 1 backend

Flask API for the User Profile Customisation feature. Validates the shared session
cookie against `shared-api`, then proxies to `student-1-db` for persistence.

Local dev URL: http://localhost:16005/

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/profiles` | Create the caller's profile |
| GET | `/api/profiles/me` | Get caller's profile + identity + role |
| GET | `/api/profiles/{id}` | Get a profile (owner only) |
| PUT | `/api/profiles/{id}` | Update a profile (owner only) |
| DELETE | `/api/profiles/{id}` | Delete a profile and its resumes (owner only) |
| PUT | `/api/user` | Update first/last name on the shared users table |
| POST | `/api/profiles/{id}/resumes` | Upload a resume (applicant only, owner only) |
| GET | `/api/profiles/{id}/resumes` | List resumes for a profile (applicant only, owner only) |
| GET | `/api/resumes/{id}/download` | Download a resume file (owner only) |
| DELETE | `/api/resumes/{id}` | Delete a resume (owner only) |

Resume uploads are restricted to PDF and 5MB max, enforced both here and
in `student-1-db`.

## Not yet implemented

- AI resume-analysis endpoint (suggest profile fields from resume content) —
  deferred to a separate branch, blocked on the shared `ai-services/ai-mode` service.

See [../README.md](../README.md) for known architectural deviations and testing status.

