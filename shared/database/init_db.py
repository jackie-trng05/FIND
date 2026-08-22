import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "find.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL UNIQUE,
    user_password_hash TEXT NOT NULL,
    user_role TEXT NOT NULL CHECK(user_role IN ('applicant', 'staff')),
    user_first_name TEXT,
    user_last_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

cursor.execute("DELETE FROM sessions")
cursor.execute("DELETE FROM users")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


seed_users = [
    ("staff@find.com", hash_password("staff123"), "staff", "Alex", "Morgan"),
    ("hr.manager@find.com", hash_password("hr1234"), "staff", "Sarah", "Mitchell"),
    ("recruiter@find.com", hash_password("recruit1"), "staff", "James", "Chen"),
    ("senior.hr@find.com", hash_password("senior1"), "staff", "Laura", "Williams"),
    ("hiring.lead@find.com", hash_password("hiring1"), "staff", "Robert", "Taylor"),
    ("applicant1@email.com", hash_password("apply123"), "applicant", "Emily", "Johnson"),
    ("applicant2@email.com", hash_password("apply123"), "applicant", "Michael", "Brown"),
    ("applicant3@email.com", hash_password("apply123"), "applicant", "Jessica", "Davis"),
    ("applicant4@email.com", hash_password("apply123"), "applicant", "David", "Wilson"),
    ("applicant5@email.com", hash_password("apply123"), "applicant", "Sophie", "Martinez"),
]

cursor.executemany("""
INSERT INTO users (user_email, user_password_hash, user_role, user_first_name, user_last_name)
VALUES (?, ?, ?, ?, ?)
""", seed_users)

conn.commit()
conn.close()

print("Database initialized with User and Session tables (10 seed users).")
