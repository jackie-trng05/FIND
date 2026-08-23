# Resume seed data

`resumes/` contains 10 committed, realistic PDF/DOCX resumes (odd profile ids are PDF,
even are DOCX) that `init_db.py` reads and inserts as-is — no generation happens at
build time or runtime, so no extra dependencies are needed to run the app or seed the
database.