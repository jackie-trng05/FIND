# Student 3 database

SQLite service (`student3.db`) backing the Application Management feature.

Local dev URL: http://localhost:16012/ (health check at `/health`)

## Schema

- `applications` — one row per candidate application:
  `application_id`, `user_id`, `job_posting_id`, `resume_id`,
  `application_status`, `availability_date`, `declaration_accepted`,
  `created_at`, `updated_at`, `submitted_at`.

`resume_id` is a soft cross-service foreign key to
[student-1's `resumes.resume_id`](../../student-1/database/init_db.py). SQLite
databases are per-service so the link is not enforced by the engine — the API
layer is responsible for validating that the referenced resume exists.

`init_db.py` re-creates the table and seeds 13 applications spanning shared-db
user IDs 6–10 across job postings 1–11 (see student-2). Statuses cover the full
workflow (Draft, Submitted, Shortlisted, Interview Completed, Hired, Rejected)
so downstream services have realistic data to render.

See [../README.md](../README.md) for known architectural deviations and testing status.
