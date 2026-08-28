"""Initialise the Student 2 Job Posting database.

Creates the ``job_postings`` table (Section 3 of the ASD registration form) and
seeds it with more than ten (10) records as required by the Individual
Responsibilities in the project specification.

The database is created at build time (see Dockerfile) and persisted in the
container. Re-running this script resets the table to the seed data.
"""

import os
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DATABASE_NAME = os.path.join(DATA_DIR, "job_postings.db")

os.makedirs(DATA_DIR, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _bulletise_requirements(text: str) -> str:
    """Convert a semicolon- or newline-separated requirements string into
    one bullet-prefixed item per line (e.g. '- Python\\n- SQL')."""
    parts: list[str] = []
    for line in str(text or "").splitlines():
        for chunk in line.split(";"):
            item = chunk.strip().lstrip("-•* ").strip()
            if item:
                parts.append(item)
    return "\n".join(f"- {item}" for item in parts)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_postings (
    JobPosting_Id           INTEGER PRIMARY KEY AUTOINCREMENT,
    User_Id                 INTEGER NOT NULL,
    Job_Title               TEXT    NOT NULL,
    Job_Description         TEXT    NOT NULL DEFAULT '',
    Job_Type                TEXT    NOT NULL DEFAULT 'Full time',
    Location                TEXT    NOT NULL DEFAULT '',
    Salary_Range            TEXT    NOT NULL DEFAULT '',
    Requirements            TEXT    NOT NULL DEFAULT '',
    Application_Deadline    TEXT    NOT NULL DEFAULT '',
    JobPosting_Status       TEXT    NOT NULL DEFAULT 'Draft',
    JobPosting_CreatedAt    TEXT    NOT NULL,
    JobPosting_UpdatedAt    TEXT    NOT NULL,
    JobPosting_PublishedAt  TEXT
)
"""

# Columns: User_Id (shared-db users.user_id of the staff member who owns this
# posting), Job_Title, Job_Description, Job_Type, Location, Salary_Range,
# Requirements, Application_Deadline, JobPosting_Status, JobPosting_PublishedAt
SEED_ROWS = [
    (1, "Senior Software Engineer",
     "Design and build scalable microservices for our recruitment platform.",
     "Full time", "Sydney, NSW", "$140,000 - $165,000",
     "5+ years backend development; Python; REST APIs; Docker",
     "2026-09-30", "Published"),
    (1, "Frontend Developer (HTMX)",
     "Build fast, accessible interfaces using HTMX and modern CSS.",
     "Full time", "Melbourne, VIC", "$110,000 - $130,000",
     "3+ years frontend; HTML5; CSS3; JavaScript; HTMX",
     "2026-10-15", "Published"),
    (2, "Data Analyst",
     "Turn recruitment data into insights that guide hiring decisions.",
     "Full time", "Brisbane, QLD", "$95,000 - $115,000",
     "SQL; data visualisation; statistics",
     "2026-09-20", "Published"),
    (2, "HR Coordinator",
     "Support the people team across the full employee lifecycle.",
     "Part time", "Perth, WA", "$70,000 - $80,000 (pro-rata)",
     "Strong communication; MS Office; attention to detail",
     "2026-10-05", "Published"),
    (3, "DevOps Engineer",
     "Own our CI/CD pipelines and cloud container deployments.",
     "Full time", "Remote (Australia)", "$135,000 - $155,000",
     "GitHub Actions; AWS/Azure; Docker; Terraform",
     "2026-11-01", "Published"),
    (3, "QA Automation Tester",
     "Design automated test suites to keep releases reliable.",
     "Casual", "Adelaide, SA", "$55 - $65 per hour",
     "pytest; Selenium; test design",
     "2026-10-25", "Published"),
    (4, "Product Manager",
     "Shape the roadmap for our agentic AI recruitment features.",
     "Full time", "Sydney, NSW", "$150,000 - $175,000",
     "Product discovery; stakeholder management; agile delivery",
     "2026-11-10", "Published"),
    (4, "UX Designer",
     "Craft intuitive experiences for applicants and hiring staff.",
     "Full time", "Melbourne, VIC", "$105,000 - $125,000",
     "Figma; user research; interaction design",
     "2026-10-18", "Published"),
    (5, "Machine Learning Engineer",
     "Integrate open-source LLMs to power AI-assisted hiring.",
     "Full time", "Canberra, ACT", "$145,000 - $170,000",
     "Python; LLMs; Ollama; prompt engineering",
     "2026-11-15", "Draft"),
    (5, "IT Support Officer",
     "Provide first-line technical support across the business.",
     "Full time", "Hobart, TAS", "$65,000 - $78,000",
     "Troubleshooting; Windows; networking basics",
     "2026-10-08", "Draft"),
    (1, "Marketing Specialist",
     "Grow our employer brand and candidate pipeline.",
     "Part time", "Remote (Australia)", "$85,000 - $95,000 (pro-rata)",
     "Content marketing; SEO; social media",
     "2026-10-30", "Published"),
    (2, "Recruitment Consultant",
     "Manage end-to-end recruitment for technology clients.",
     "Full time", "Sydney, NSW", "$90,000 - $110,000 + commission",
     "Sourcing; interviewing; client management",
     "2026-11-05", "Draft"),
]


def initialise() -> None:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    cursor.execute("DELETE FROM job_postings")
    # Reset AUTOINCREMENT so seeded JobPosting_Ids stay 1..n
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'job_postings'")

    now = _now()
    rows = []
    for row in SEED_ROWS:
        (user_id, title, description, job_type, location, salary, requirements,
         deadline, status) = row
        published_at = now if status == "Published" else None
        rows.append((
            user_id, title, description, job_type, location, salary,
            _bulletise_requirements(requirements), deadline, status,
            now, now, published_at,
        ))

    cursor.executemany(
        """
        INSERT INTO job_postings (
            User_Id, Job_Title, Job_Description, Job_Type, Location,
            Salary_Range, Requirements,
            Application_Deadline, JobPosting_Status,
            JobPosting_CreatedAt, JobPosting_UpdatedAt, JobPosting_PublishedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0]
    conn.close()
    print(f"Job Posting database initialised with {count} records at {DATABASE_NAME}.")


if __name__ == "__main__":
    initialise()
