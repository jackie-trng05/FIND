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
# Reset AUTOINCREMENT so seeded application_ids stay 1..n; student-4's
# interviews and student-5's evaluations reference them by number.
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'applications'")

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
#
# Status decides what the other services may do with an application:
#   Shortlisted        -> an interview can be scheduled (must have no interview)
#   Interview Requested / Scheduled / Completed -> a matching interview exists
#   Interview Completed / Hired / Rejected -> an evaluation can exist
#   Hired / Rejected   -> a final outcome; any interview is deleted, and an
#                         applicant can only be Hired for one application

seed_applications = [
    (6,  1, 6, "Submitted",            _future(14), 1, _past(5)),
    (6,  3, 6, "Submitted",            _future(25), 1, _past(2)),
    (6,  7, 6, "Draft",                _future(20), 1, _past(6)),
    (6, 11, 6, "Interview Completed",  _future(15), 1, _past(20)),
    (7,  2, 7, "Shortlisted",          _future(18), 1, _past(9)),
    (6,  5, 6, "Interview Scheduled",  _future(12), 1, _past(11)),
    (7,  8, 7, "Interview Completed",  _future(22), 1, _past(24)),
    (8,  4, 8, "Interview Requested",  _future(14), 1, _past(7)),
    (8,  6, 8, "Interview Scheduled",  _future(19), 1, _past(10)),
    (8,  9, 8, "Interview Completed",  _future(16), 1, _past(18)),
    (9,  1, 9, "Interview Completed",  _future(21), 1, _past(19)),
    (9,  5, 9, "Interview Completed",  _future(28), 1, _past(13)),
    (9, 10, 9, "Hired",                _future(20), 1, _past(40)),
    (10, 9, 10, "Interview Completed", _future(14), 1, _past(16)),
    (10, 2, 10, "Rejected",            _future(30), 1, _past(15)),
    (10, 7, 10, "Rejected",            _future(16), 1, _past(26)),
    (10, 11, 10, "Hired",              _future(23), 1, _past(38)),
    (6, 12, 6, "Interview Requested",  _future(25), 1, _past(5)),
    (9,  3, 9, "Rejected",             _future(17), 1, _past(21)),
    (6,  4, 6, "Shortlisted",          _future(22), 1, _past(4)),
]

cursor.executemany("""
INSERT INTO applications (user_id, job_posting_id, resume_id, application_status,
availability_date, declaration_accepted, submitted_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", seed_applications)

conn.commit()
conn.close()

print(f"Student-3 database initialized with applications table ({len(seed_applications)} seed records).")
