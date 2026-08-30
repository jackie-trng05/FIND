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
    Evaluation_TechnicalScore INTEGER CHECK(Evaluation_TechnicalScore BETWEEN 1 AND 5),
    Evaluation_EducationScore INTEGER CHECK(Evaluation_EducationScore BETWEEN 1 AND 5),
    Evaluation_CommunicationScore INTEGER CHECK(Evaluation_CommunicationScore BETWEEN 1 AND 5),
    Evaluation_ProblemSolvingScore INTEGER CHECK(Evaluation_ProblemSolvingScore BETWEEN 1 AND 5),
    Evaluation_ProfessionalismScore INTEGER CHECK(Evaluation_ProfessionalismScore BETWEEN 1 AND 5),
    Evaluation_OverallScore REAL,
    Evaluation_FinalRecommendation TEXT CHECK(Evaluation_FinalRecommendation IN ('Hire', 'Reject')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(Application_Id)
)
""")

cursor.execute("DELETE FROM evaluations")

# Seed rows are kept consistent with the Student-3 application statuses so an
# application's status always matches whether (and how) it has been evaluated:
#   Hired    -> a finalized "Hire" evaluation
#   Rejected -> a finalized "Reject" evaluation
#   Evaluation In Progress -> a draft (no final recommendation yet)
#   Interview Completed    -> NO evaluation (still "ready for evaluation")
# (Application_Id, User_Id, Tech, Edu, Comm, ProblemSolving, Prof, Overall, Recommendation)
seed = [
    # Finalized — applications that are Hired.
    (13, 1, 5, 4, 4, 5, 4, 4.4, "Hire"),
    (17, 3, 4, 5, 3, 4, 5, 4.2, "Hire"),
    # Finalized — applications that are Rejected.
    (16, 2, 2, 2, 3, 2, 3, 2.4, "Reject"),
    (19, 4, 3, 2, 2, 1, 2, 2.0, "Reject"),
    # Drafts — applications that are Evaluation In Progress.
    (14, 1, 3, 4, 3, 3, 3, 3.2, None),
    (15, 5, 4, 4, 4, 3, 4, 3.8, None),
]

cursor.executemany("""
INSERT INTO evaluations (
    Application_Id, User_Id,
    Evaluation_TechnicalScore, Evaluation_EducationScore, Evaluation_CommunicationScore,
    Evaluation_ProblemSolvingScore, Evaluation_ProfessionalismScore, Evaluation_OverallScore,
    Evaluation_FinalRecommendation
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", seed)

conn.commit()
conn.close()

print("Student-5 database initialized with evaluations table (6 seed records).")
