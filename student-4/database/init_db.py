import os
import sqlite3
import json

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


def _notes(technical, education, communication, problem_solving, professionalism):
    """Assessment notes are stored as JSON with a fixed set of skill areas."""
    return json.dumps({
        "Technical": technical,
        "Education": education,
        "Communication": communication,
        "Problem Solving": problem_solving,
        "Professionalism": professionalism,
    })


interviews = [
    # application_id values reference Student 3's applications table.
    #   app 4 = Michael Brown, "Frontend Developer" posting  -> scheduled, time
    #           has passed, so it appears in "Interviews To Complete".
    #   app 2 = Emily Johnson -> scheduled, time has passed, also awaiting notes
    #           in "Interviews To Complete".
    #   app 7 = Jessica Davis, "QA Automation Tester" posting -> completed, with
    #           the five skill-area notes filled in.
    # staff_id 1 = Alex Morgan (shared-db). Applicant/posting details are
    # resolved at read time from the Application, Job Posting and shared DBs.
    (1, 4, 1, "2026-08-10 10:00", "https://meet.find.app/int-1", "Interview Scheduled", ""),
    (2, 7, 1, "2026-08-04 14:00", "https://meet.find.app/int-2", "Interview Completed", _notes(
        "Strong grasp of test automation frameworks and Python.",
        "Relevant degree in Computer Science.",
        "Clear, concise communicator throughout.",
        "Worked through the debugging scenario methodically.",
        "Punctual and well-prepared.",
    )),
    (3, 2, 1, "2026-08-12 14:30", "https://meet.find.app/int-3", "Interview Scheduled", ""),
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
