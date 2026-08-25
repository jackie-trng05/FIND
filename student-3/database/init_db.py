import os
import sqlite3
from datetime import datetime, timedelta, timezone

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student3.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_posting_id INTEGER NOT NULL,
    resume_id INTEGER,
    application_status TEXT NOT NULL DEFAULT 'Draft',
    availability_date TEXT NOT NULL DEFAULT '',
    declaration_accepted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    submitted_at TEXT
)
""")

cursor.execute("DELETE FROM applications")

# resume_id is a soft cross-service foreign key to student-1's resumes.resume_id.
# It is not enforced by SQLite (SQLite databases are per-service); the API layer
# validates the resume exists before saving. Seed applicants (shared-db user_ids
# 6-10) map 1:1 to student-1 resume_ids 6-10 because student-1 seeds one resume
# per profile in ascending user_id order.
# JobPosting_Id values 1..12 come from the seeded student-2 job_postings table.


def _future(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


def _past(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()


# (user_id, job_posting_id, resume_id, application_status,
#  availability_date, declaration_accepted, submitted_at)
seed_applications = [
    (6,  1, 6, "Submitted",            _future(14), 1, _past(5)),
    (6,  3, 6, "Interview Completed",  _future(21), 1, _past(10)),
    (6,  7, 6, "Draft",                _future(30), 0, None),
    (6, 11, 6, "Shortlisted",          _future(20), 1, _past(8)),
    (7,  2, 7, "Interview Completed",  _future(10), 1, _past(12)),
    (7,  5, 7, "Interview Completed",  _future(28), 1, _past(3)),
    (8,  4, 8, "Rejected",             _future(14), 1, _past(15)),
    (8,  6, 8, "Interview Completed",  _future(21), 1, _past(20)),
    (8,  8, 8, "Draft",                _future(45), 0, None),
    (9,  1, 9, "Interview Completed",  _future(35), 1, _past(18)),
    (9,  5, 9, "Hired",                _future(20), 1, _past(40)),
    (10, 2, 10, "Interview Completed", _future(14), 1, _past(25)),
    (10, 7, 10, "Submitted",           _future(28), 1, _past(1)),
]

cursor.executemany("""
INSERT INTO applications (user_id, job_posting_id, resume_id, application_status,
availability_date, declaration_accepted, submitted_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", seed_applications)

conn.commit()
conn.close()

print("Student-3 database initialized with applications table (13 seed records).")
