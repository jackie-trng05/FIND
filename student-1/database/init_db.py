import os
import sqlite3
from datetime import datetime

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student1.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    phone TEXT,
    location TEXT,
    professional_title TEXT,
    summary TEXT,
    interests TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS resumes (
    resume_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_data BLOB NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    parsed_at TEXT,
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE
)
""")

cursor.execute("DELETE FROM resumes")
cursor.execute("DELETE FROM profiles")

# Seeded user_ids 1-10 must stay in sync with shared/database/init_db.py seed data.
# user_id -> name (for reference only; names now live solely in the shared users table):
# 1 Alex Morgan, 2 Sarah Mitchell, 3 James Chen, 4 Laura Williams, 5 Robert Taylor,
# 6 Emily Johnson, 7 Michael Brown, 8 Jessica Davis, 9 David Wilson, 10 Sophie Martinez
seed_profiles = [
    (1, "+61400000001", "Sydney, Australia", "HR Manager", "Experienced HR professional with 10+ years in talent acquisition.", "Leadership, DEI initiatives"),
    (2, "+61400000002", "Melbourne, Australia", "Senior Recruiter", "Specialist in tech recruitment and employer branding.", "Employer branding, Tech hiring"),
    (3, "+61400000003", "Brisbane, Australia", "Recruitment Coordinator", "Detail-oriented coordinator managing interview logistics.", "Process improvement, Scheduling"),
    (4, "+61400000004", "Perth, Australia", "HR Director", "Strategic HR leader driving organisational change.", "Change management, Strategy"),
    (5, "+61400000005", "Adelaide, Australia", "Hiring Lead", "Results-driven hiring manager for engineering teams.", "Technical hiring, Team building"),
    (6, "+61400000006", "Sydney, Australia", "Software Engineer", "Full-stack developer seeking new opportunities.", "Python, React, Cloud computing"),
    (7, "+61400000007", "Melbourne, Australia", "Data Analyst", "Analytics professional with expertise in SQL and Python.", "Machine learning, Data visualisation"),
    (8, "+61400000008", "Sydney, Australia", "UX Designer", "User-centred designer passionate about accessibility.", "Accessibility, Design systems"),
    (9, "+61400000009", "Canberra, Australia", "Project Manager", "Certified PMP with agile delivery experience.", "Agile, Stakeholder management"),
    (10, "+61400000010", "Hobart, Australia", "Marketing Specialist", "Digital marketing expert focused on growth.", "SEO, Content strategy"),
]

cursor.executemany("""
INSERT INTO profiles (user_id, phone, location, professional_title, summary, interests)
VALUES (?, ?, ?, ?, ?, ?)
""", seed_profiles)

# Seed resumes from real PDF/DOCX files committed under seed_data/resumes (see seed_data/README.md);
# odd profile ids are PDF, even are DOCX, alternating to cover both supported file types.
SEED_RESUME_DIR = os.path.join(os.path.dirname(__file__), "seed_data", "resumes")
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

for i in range(1, 11):
    extension = ".pdf" if i % 2 == 1 else ".docx"
    file_name = f"resume_profile_{i}{extension}"
    with open(os.path.join(SEED_RESUME_DIR, file_name), "rb") as f:
        content = f.read()
    cursor.execute("""
    INSERT INTO resumes (profile_id, file_name, file_type, file_data)
    VALUES (?, ?, ?, ?)
    """, (i, file_name, MIME_TYPES[extension], content))

conn.commit()
conn.close()

print("Student-1 database initialized with profiles and resumes tables (10 seed records each).")
