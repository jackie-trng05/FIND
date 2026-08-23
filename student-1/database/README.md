# Student 1 database

SQLite service (`student1.db`) backing the User Profile Customisation feature.

Local dev URL: http://localhost:16006/ (health check at `/health`)

## Schema

- `profiles` — one row per user (`user_id` unique FK to the shared users table):
  `profile_id`, `user_id`, `phone`, `location`, `professional_title`, `summary`,
  `interests`, `created_at`, `updated_at`.
- `resumes` — one or more rows per profile, cascade-deleted with the profile:
  `resume_id`, `profile_id`, `file_name`, `file_type`, `file_data` (BLOB),
  `uploaded_at`, `updated_at`, `parsed_at`.

`init_db.py` re-creates both tables and seeds 10 profiles (mapped to shared-db
user IDs 1–10) and 10 resumes with realistic, persona-matched content — 5 PDF and
5 DOCX, alternating by profile id. The files live under `seed_data/resumes/` and are
read as-is at build time; see `seed_data/README.md` for details.

## Not yet implemented

- `parsed_at` is reserved for the AI resume-parsing feature, not yet populated —
  deferred to a separate branch.

See [../README.md](../README.md) for known architectural deviations and testing status.

