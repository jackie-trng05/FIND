import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "interview.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS interviews (
    interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    interview_datetime TEXT NOT NULL,
    interview_link TEXT,
    interview_status TEXT NOT NULL,
    interview_notes TEXT
)
""")

cursor.execute("DELETE FROM interviews")

interviews = [
    # application_id values reference Student 3's applications table.
    #   app 4 = Michael Brown, "Frontend Developer" posting  -> accepted
    #   app 7 = Jessica Davis, "QA Automation Tester" posting -> completed
    # staff_id 1 = Alex Morgan (shared-db). Applicant/posting details are
    # resolved at read time from the Application, Job Posting and shared DBs.
    (1, 4, 1, "2026-09-10 10:00", "https://meet.find.app/int-1", "Interview Scheduled", "Frontend developer interview."),
    (2, 7, 1, "2026-09-04 14:00", "https://meet.find.app/int-2", "Interview Completed", "Completed — pending evaluation."),
]

cursor.executemany(
    """
    INSERT INTO interviews (
        interview_id,
        application_id,
        staff_id,
        interview_datetime,
        interview_link,
        interview_status,
        interview_notes
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    interviews,
)

conn.commit()
conn.close()

print(f"Database initialized with {len(interviews)} interviews.")
