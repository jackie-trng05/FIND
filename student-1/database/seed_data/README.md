# Resume seed data

`resumes/` contains 10 committed, realistic PDF resumes (one per seeded profile) that
`init_db.py` reads and inserts as-is — no generation happens at build time or
runtime, so no extra dependencies are needed to run the app or seed the database.

DOCX resume support was removed repo-wide (agreed with student-3, 2026-08-26); the
files that previously alternated PDF/DOCX now all ship as PDF.