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
    Staff_Id INTEGER NOT NULL,
    HR_Staff_Name TEXT NOT NULL,
    HR_Staff_Number TEXT NOT NULL,
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

seed = [
    (101, 1, "Alex Morgan",    "HR-001", 5, 4, 4, 5, 4, 4.4, "Hire",      "Completed"),
    (102, 1, "Alex Morgan",    "HR-001", 3, 3, 4, 3, 4, 3.4, "Reject",    "Completed"),
    (103, 2, "Sarah Mitchell", "HR-002", 4, 5, 3, 4, 5, 4.2, "Hire",      "Completed"),
    (104, 2, "Sarah Mitchell", "HR-002", 2, 2, 3, 2, 3, 2.4, "Reject",    "Completed"),
    (105, 3, "James Chen",     "HR-003", 4, 4, 5, 4, 4, 4.2, "Hire",      "Completed"),
    (106, 3, "James Chen",     "HR-003", 5, 5, 4, 5, 5, 4.8, "Hire",      "Completed"),
    (107, 1, "Alex Morgan",    "HR-001", 3, 4, 3, 3, 3, 3.2, "Reject",    "Draft"),
    (108, 4, "Laura Williams", "HR-004", 4, 3, 4, 4, 3, 3.6, "Hire",      "Completed"),
    (109, 4, "Laura Williams", "HR-004", 1, 2, 2, 1, 2, 1.6, "Reject",    "Completed"),
    (110, 5, "Robert Taylor",  "HR-005", 4, 4, 4, 3, 4, 3.8, "Hire",      "Draft"),
]

cursor.executemany("""
INSERT INTO evaluations (
    Application_Id, Staff_Id, HR_Staff_Name, HR_Staff_Number,
    Evaluation_TechnicalScore, Evaluation_EducationScore, Evaluation_CommunicationScore,
    Evaluation_ProblemSolvingScore, Evaluation_ProfessionalismScore, Evaluation_OverallScore,
    Evaluation_FinalRecommendation, Evaluation_Status
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", seed)

conn.commit()
conn.close()

print("Student-5 database initialized with evaluations table (10 seed records).")
