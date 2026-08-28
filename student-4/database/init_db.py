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
    user_id INTEGER NOT NULL,
    interview_datetime TEXT NOT NULL,
    interview_link TEXT,
    interview_notes TEXT
)
""")

cursor.execute("DELETE FROM interviews")
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'interviews'")


def _notes(technical, education, communication, problem_solving, professionalism):
    """Assessment notes are stored as JSON with a fixed set of skill areas."""
    return json.dumps({
        "Technical": technical,
        "Education": education,
        "Communication": communication,
        "Problem Solving": problem_solving,
        "Professionalism": professionalism,
    })


def _done(role):
    """Filled-in notes for an interview that has already been written up."""
    return _notes(
        f"Solid hands-on {role} knowledge; answered the scenario questions well.",
        "Qualifications line up with the requirements for the role.",
        "Explained their reasoning clearly and asked good questions.",
        "Broke the exercise down methodically before coding.",
        "Punctual, prepared and professional throughout.",
    )


def _mixed(role):
    """Notes for an interview with an adequate but unremarkable performance."""
    return _notes(
        f"Adequate {role} knowledge, but nothing that stood out as exceptional.",
        "Qualifications broadly match the role, though not a strong specialisation.",
        "Communicated clearly enough, though answers were sometimes brief.",
        "Got to a working answer eventually, but took longer than expected.",
        "Professional and on time, but seemed only moderately engaged.",
    )

interviews = [
    (1,  4,  1, "2026-08-15 10:00", "https://meet.find.app/int-1", _notes(
        "Could not answer basic technical questions and struggled through the live coding exercise.",
        "Educational background is only loosely related to the role's requirements.",
        "Explanations were unclear and often contradicted earlier answers.",
        "Unable to break the problem down; needed constant prompting to make any progress.",
        "Arrived ten minutes late and seemed unprepared for the interview.",
    )),
    (2,  5,  2, "2026-09-05 09:00", "https://meet.find.app/int-2", ""),
    (3,  6,  2, "2026-08-20 13:00", "https://meet.find.app/int-3", ""),
    (4,  7,  2, "2026-08-10 11:00", "https://meet.find.app/int-4", _done("data analysis")),
    (5,  8,  3, "2026-09-02 14:00", "https://meet.find.app/int-5", ""),
    (6,  9,  3, "2026-09-10 10:30", "https://meet.find.app/int-6", ""),
    (7,  10, 3, "2026-08-06 15:00", "https://meet.find.app/int-7", _done("UX design")),
    (8,  11, 4, "2026-08-12 09:30", "https://meet.find.app/int-8", _mixed("project management")),
    (9,  12, 1, "2026-08-18 16:00", "https://meet.find.app/int-9", _done("project management")),
    (10, 14, 4, "2026-08-04 10:00", "https://meet.find.app/int-10", _done("marketing")),
]

cursor.executemany(
    """
    INSERT INTO interviews (
        interview_id,
        application_id,
        user_id,
        interview_datetime,
        interview_link,
        interview_notes
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    interviews,
)

conn.commit()
conn.close()

print(f"Database initialized with {len(interviews)} interviews.")
