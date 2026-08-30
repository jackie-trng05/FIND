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

seed = [
    (2,  1, 5, 4, 4, 5, 4, 4.4, "Hire"),
    (5,  1, 3, 3, 4, 3, 4, 3.4, "Reject"),
    (6,  2, 4, 5, 3, 4, 5, 4.2, "Hire"),
    (8,  2, 2, 2, 3, 2, 3, 2.4, "Reject"),
    (10, 3, 4, 4, 5, 4, 4, 4.2, "Hire"),
    (12, 3, 5, 5, 4, 5, 5, 4.8, "Hire"),
    (14, 1, 3, 4, 3, 3, 3, 3.2, None),
    (16, 4, 4, 3, 4, 4, 3, 3.6, "Hire"),
    (17, 4, 1, 2, 2, 1, 2, 1.6, "Reject"),
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

print("Student-5 database initialized with evaluations table (10 seed records).")
