import os
import sqlite3
from datetime import datetime

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student5.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS evaluations (
    Evaluation_Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Application_Id INTEGER NOT NULL,
    User_Id INTEGER NOT NULL,
    Evaluation_TechnicalScore INTEGER NOT NULL CHECK(Evaluation_TechnicalScore BETWEEN 1 AND 5),
    Evaluation_EducationScore INTEGER NOT NULL CHECK(Evaluation_EducationScore BETWEEN 1 AND 5),
    Evaluation_CommunicationScore INTEGER NOT NULL CHECK(Evaluation_CommunicationScore BETWEEN 1 AND 5),
    Evaluation_ProblemSolvingScore INTEGER NOT NULL CHECK(Evaluation_ProblemSolvingScore BETWEEN 1 AND 5),
    Evaluation_ProfessionalismScore INTEGER NOT NULL CHECK(Evaluation_ProfessionalismScore BETWEEN 1 AND 5),
    Evaluation_OverallScore REAL NOT NULL,
    Evaluation_FinalRecommendation TEXT NOT NULL CHECK(Evaluation_FinalRecommendation IN ('Hire', 'Reject')),
    Evaluation_Status TEXT NOT NULL DEFAULT 'Draft' CHECK(Evaluation_Status IN ('Draft', 'Completed')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(Application_Id)
)
""")

cursor.execute("DELETE FROM evaluations")
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'evaluations'")

# An evaluation only exists once the interview is done, and its status has to
# agree with the application it points at:
#   application Interview Completed -> Draft (write-up still in progress)
#   application Hired               -> Completed / Hire
#   application Rejected            -> Completed / Reject

seed = [
    (7,  2, 4, 3, 4, 3, 4, 3.6, "Hire",   "Draft"),
    (10, 3, 4, 4, 3, 4, 4, 3.8, "Hire",   "Draft"),
    (11, 4, 3, 3, 3, 3, 3, 3.0, "Reject", "Draft"),
    (14, 4, 4, 3, 4, 3, 4, 3.6, "Hire",   "Draft"),
    (8,  2, 4, 4, 4, 4, 4, 4.0, "Hire",   "Draft"),
    (13, 1, 5, 4, 5, 4, 5, 4.6, "Hire",   "Completed"),
    (17, 4, 4, 5, 4, 5, 4, 4.4, "Hire",   "Completed"),
    (15, 4, 2, 3, 2, 2, 3, 2.4, "Reject", "Completed"),
    (16, 1, 2, 2, 3, 2, 2, 2.2, "Reject", "Completed"),
    (19, 1, 2, 3, 2, 2, 2, 2.2, "Reject", "Completed"),
]

cursor.executemany("""
INSERT INTO evaluations (
    Application_Id, User_Id,
    Evaluation_TechnicalScore, Evaluation_EducationScore, Evaluation_CommunicationScore,
    Evaluation_ProblemSolvingScore, Evaluation_ProfessionalismScore, Evaluation_OverallScore,
    Evaluation_FinalRecommendation, Evaluation_Status
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", seed)

conn.commit()
conn.close()

print(f"Student-5 database initialized with evaluations table ({len(seed)} seed records).")
