"""Initialise the Student 3 Application Management database.

Creates the ``applications`` table (Section 3 of the ASD registration form),
plus supporting tables for resumes, AI screenings, and staff-saved
"favorite filters" for the All Applications table.

Seeds the ``applications`` table with more than ten (10) records as required
by the Individual Responsibilities in the project specification.

The database is created at build time (see Dockerfile) and persisted in the
container. Re-running this script resets every table to the seed data.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DATABASE_NAME = os.path.join(DATA_DIR, "applications.db")

os.makedirs(DATA_DIR, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _future(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


def _past(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(
        microsecond=0
    ).isoformat()


# --------------------------------------------------------------------------- #
# Schema                                                                      #
# --------------------------------------------------------------------------- #

CREATE_APPLICATIONS_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    Application_Id           INTEGER PRIMARY KEY AUTOINCREMENT,
    User_Id                  INTEGER NOT NULL,               -- Applicant user_id (from shared-db)
    JobPosting_Id            INTEGER NOT NULL,               -- References student-2 job_postings
    Resume_Id                INTEGER,                        -- FK to resumes table
    Application_Status       TEXT    NOT NULL DEFAULT 'Draft',
    Availability_Date        TEXT    NOT NULL DEFAULT '',    -- ISO date (earliest start)
    Declaration_Accepted     INTEGER NOT NULL DEFAULT 0,
    Application_CreatedAt    TEXT    NOT NULL,
    Application_UpdatedAt    TEXT    NOT NULL,
    Application_SubmittedAt  TEXT
)
"""

CREATE_RESUMES_SQL = """
CREATE TABLE IF NOT EXISTS resumes (
    Resume_Id         INTEGER PRIMARY KEY AUTOINCREMENT,
    User_Id           INTEGER NOT NULL,
    Resume_Filename   TEXT    NOT NULL,
    Resume_MimeType   TEXT    NOT NULL,
    Resume_SizeBytes  INTEGER NOT NULL,
    Resume_Data       BLOB    NOT NULL,
    Resume_UploadedAt TEXT    NOT NULL
)
"""

CREATE_AI_SCREENINGS_SQL = """
CREATE TABLE IF NOT EXISTS ai_screenings (
    Screening_Id         INTEGER PRIMARY KEY AUTOINCREMENT,
    Application_Id       INTEGER NOT NULL UNIQUE,
    Recommendation       TEXT    NOT NULL DEFAULT 'Maybe',    -- Yes | No | Maybe
    Reasoning            TEXT    NOT NULL DEFAULT '',         -- Free-form explanation
    Screening_CreatedAt  TEXT    NOT NULL
)
"""

CREATE_FAVORITE_FILTERS_SQL = """
CREATE TABLE IF NOT EXISTS favorite_filters (
    Filter_Id         INTEGER PRIMARY KEY AUTOINCREMENT,
    Staff_UserId      INTEGER NOT NULL,          -- shared-db user_id of the staff owner
    Filter_Name       TEXT    NOT NULL,
    Filter_Query      TEXT    NOT NULL,          -- URL-encoded query string
    Filter_CreatedAt  TEXT    NOT NULL
)
"""


# --------------------------------------------------------------------------- #
# Seed data                                                                   #
# --------------------------------------------------------------------------- #
#
# Applicant user IDs in the shared-db (from shared/database/init_db.py):
#   6 = Emily Johnson    7 = Michael Brown   8 = Jessica Davis
#   9 = David Wilson    10 = Sophie Martinez
#
# JobPosting_Id values 1..12 come from the seeded student-2 job_postings table
# (Senior Software Engineer, Frontend Developer, Data Analyst, etc.).

# Realistic resume bodies used to seed the ``resumes`` table. Some candidates
# have backgrounds that strongly match their target roles (Emily, David) while
# others are deliberately weak matches (Jessica, Sophie) so the AI screening
# demo has a spread of Yes / Maybe / No recommendations.
_RESUME_BODIES: dict[int, str] = {
    # Emily Johnson - strong backend software engineer
    6: (
        "Emily Johnson - Senior Backend Software Engineer\n"
        "Email: applicant1@email.com\n\n"
        "SUMMARY\n"
        "Backend engineer with 6+ years designing and shipping Python microservices\n"
        "for high-traffic B2B products. Deep experience with REST API design,\n"
        "database performance tuning, and CI/CD automation.\n\n"
        "TECHNICAL SKILLS\n"
        "Python, Flask, FastAPI, PostgreSQL, SQL, Docker, Kubernetes, REST APIs,\n"
        "microservices, unit testing (pytest), GitHub Actions, AWS (ECS, RDS).\n\n"
        "EXPERIENCE\n"
        "Senior Backend Engineer - TechCo (2022 to 2026)\n"
        "  - Led the migration of the monolith to eight production microservices\n"
        "  - Owned API design, contract testing, and observability tooling\n"
        "Backend Developer - StartupX (2020 to 2022)\n"
        "  - Built Flask REST APIs consumed by a React web app and mobile clients\n\n"
        "EDUCATION\n"
        "BSc Computer Science, University of Sydney (2020)\n"
    ),
    # Michael Brown - solid frontend / HTMX developer
    7: (
        "Michael Brown - Frontend Developer\n"
        "Email: applicant2@email.com\n\n"
        "SUMMARY\n"
        "Frontend engineer specialising in accessible, framework-light web UIs.\n"
        "Comfortable across HTMX, Vue, and vanilla JavaScript stacks.\n\n"
        "TECHNICAL SKILLS\n"
        "HTML5, CSS3, JavaScript, TypeScript, HTMX, Vue 3, responsive design,\n"
        "WCAG accessibility, Figma, git, GitHub Actions basics.\n\n"
        "EXPERIENCE\n"
        "Frontend Developer - WebCorp (2023 to 2026)\n"
        "  - Rebuilt the customer portal in Vue 3 with an HTMX-driven admin panel\n"
        "  - Reduced Largest Contentful Paint by 42% through image and CSS tuning\n"
        "UI Engineer - ShopCo (2021 to 2023)\n"
        "  - Delivered pixel-accurate marketing pages from Figma designs\n\n"
        "EDUCATION\n"
        "BSc Software Engineering, RMIT (2021)\n"
    ),
    # Jessica Davis - retail / hospitality background (weak fit for tech roles)
    8: (
        "Jessica Davis - Retail Team Leader\n"
        "Email: applicant3@email.com\n\n"
        "SUMMARY\n"
        "Retail supervisor with 8 years of hands-on customer service, roster\n"
        "management, and merchandising experience across department and grocery\n"
        "stores. Trained in food safety and OH&S.\n\n"
        "SKILLS\n"
        "Customer service, point-of-sale operation, cash handling, stock control,\n"
        "team leadership, conflict resolution, rostering, MS Word, MS Excel basics.\n\n"
        "EXPERIENCE\n"
        "Retail Team Leader - BigStore (2020 to 2026)\n"
        "  - Supervised a team of 15 sales associates across two departments\n"
        "  - Reduced shrinkage by 12% through improved stock-take procedures\n"
        "Hospitality Supervisor - HotelChain (2018 to 2020)\n"
        "  - Managed front-of-house staff and guest relations\n\n"
        "EDUCATION\n"
        "Certificate IV in Retail Management, TAFE NSW (2019)\n"
    ),
    # David Wilson - senior DevOps / cloud engineer (strong for DevOps role)
    9: (
        "David Wilson - Senior DevOps Engineer\n"
        "Email: applicant4@email.com\n\n"
        "SUMMARY\n"
        "Cloud platform engineer with 8 years of experience running production\n"
        "Kubernetes on AWS. Owns the full CI/CD lifecycle and incident response.\n\n"
        "TECHNICAL SKILLS\n"
        "AWS (EKS, ECS, RDS, IAM, CloudFront), Kubernetes, Docker, Terraform,\n"
        "GitHub Actions, Jenkins, Python, Bash, Prometheus, Grafana, PagerDuty.\n\n"
        "EXPERIENCE\n"
        "Senior DevOps Engineer - CloudCo (2021 to 2026)\n"
        "  - Built a multi-region EKS platform serving 40M requests per day\n"
        "  - Designed the Terraform module library shared across 12 teams\n"
        "DevOps Engineer - DataCorp (2018 to 2021)\n"
        "  - Automated deployment pipelines using Jenkins and Ansible\n\n"
        "EDUCATION\n"
        "BSc Cloud Computing, UNSW (2018)\n"
        "AWS Solutions Architect - Professional\n"
    ),
    # Sophie Martinez - graduate marketing background (weak fit for most tech
    # roles; a reasonable maybe for the Marketing Specialist posting).
    10: (
        "Sophie Martinez - Graduate Marketing Coordinator\n"
        "Email: applicant5@email.com\n\n"
        "SUMMARY\n"
        "Recent marketing graduate with a passion for content and social media.\n"
        "Hands-on with SEO tooling and freelance content projects since 2023.\n\n"
        "SKILLS\n"
        "Content marketing, copywriting, SEO, Google Analytics, Meta Business\n"
        "Suite, Canva, WordPress, basic HTML/CSS.\n\n"
        "EXPERIENCE\n"
        "Marketing Intern - StartupCo (2025 to 2026)\n"
        "  - Ran the weekly newsletter and grew list from 800 to 3,400\n"
        "  - Wrote three long-form articles ranking on page 1 for target keywords\n"
        "Freelance content creator (2023 to 2025)\n"
        "  - Delivered blog and social copy for four small-business clients\n\n"
        "EDUCATION\n"
        "BA Marketing, University of Melbourne (2026)\n"
    ),
}


def _build_resume_pdf(body: str) -> bytes:
    """Render a resume body string into a valid PDF using ``fpdf2``.

    We generate real (though minimal) PDFs so that:
      * Downloading a seeded resume opens cleanly in Adobe / Chrome / preview
        apps (the previous ``%PDF-1.4`` text stubs were rejected as damaged).
      * The backend's ``resume_text.extract_text`` helper (which uses pypdf)
        can pull the resume text into the LLM prompt for AI screening.

    The document uses the built-in Helvetica font so no font assets are needed
    inside the database container image.
    """
    # Lazy import so that unit tests that only load ``init_db``'s constants
    # don't require fpdf2 at import time (it is installed via requirements.txt
    # for the runtime container).
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    width = pdf.epw  # effective printable width in mm
    lines = body.split("\n")
    # First non-empty line is the candidate's headline (name + role).
    title = next((line for line in lines if line.strip()), "Resume")
    rest = lines[lines.index(title) + 1:] if title in lines else lines

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.multi_cell(width, 8, title)
    pdf.ln(2)

    pdf.set_font("Helvetica", size=11)
    for line in rest:
        stripped = line.rstrip()
        # Bold uppercase section headings (SUMMARY, SKILLS, EXPERIENCE, ...).
        if stripped and stripped == stripped.upper() and stripped.replace(" ", "").isalpha():
            pdf.ln(1)
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.multi_cell(width, 6, stripped)
            pdf.set_font("Helvetica", size=11)
        elif stripped == "":
            pdf.ln(2)
        else:
            pdf.multi_cell(width, 5, stripped)

    output = pdf.output()
    # fpdf2 >= 2.5 returns a bytearray; earlier versions returned str.
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)


def _fake_resume_bytes(user_id: int, candidate_name: str) -> bytes:
    """Return a real PDF for the given applicant.

    The document body is taken from ``_RESUME_BODIES`` and rendered by
    ``_build_resume_pdf``. Falls back to a stub for any applicant that hasn't
    been given a bespoke resume yet.
    """
    body = _RESUME_BODIES.get(user_id) or (
        f"{candidate_name}\nProfile summary unavailable.\n"
    )
    return _build_resume_pdf(body)


# (User_Id, first_name, last_name)  -> used only to build the fake resume text
APPLICANT_INFO = {
    6: ("Emily", "Johnson"),
    7: ("Michael", "Brown"),
    8: ("Jessica", "Davis"),
    9: ("David", "Wilson"),
    10: ("Sophie", "Martinez"),
}


# (User_Id, JobPosting_Id, Availability_Date_offset_days, Status,
#  submitted_offset_days_ago_or_None, has_resume)
SEED_APPLICATIONS = [
    # Emily Johnson
    (6, 1, 14, "Submitted",             5, True),
    (6, 3, 21, "Shortlisted",          10, True),
    (6, 7, 30, "Draft",              None, True),
    # Michael Brown
    (7, 2, 10, "Interview Scheduled",  12, True),
    (7, 5, 28, "Submitted",             3, True),
    # Jessica Davis
    (8, 4, 14, "Rejected",             15, True),
    (8, 6, 21, "Interview Completed",  20, True),
    (8, 8, 45, "Draft",              None, True),
    # David Wilson
    (9, 1, 35, "Withdrawn",            18, True),
    (9, 5, 20, "Hired",                40, True),
    # Sophie Martinez
    (10, 2, 14, "Evaluation Completed", 25, True),
    (10, 7, 28, "Submitted",             1, True),
    # Appended last so existing Application_Ids stay stable (interviews in the
    # Student 4 seed reference these ids). Extra shortlisted app for Emily so
    # the interview "To Schedule" tab has content.
    (6, 11, 20, "Shortlisted",           8, True),
]


def initialise() -> None:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute(CREATE_APPLICATIONS_SQL)
    cursor.execute(CREATE_RESUMES_SQL)
    cursor.execute(CREATE_AI_SCREENINGS_SQL)
    cursor.execute(CREATE_FAVORITE_FILTERS_SQL)

    cursor.execute("DELETE FROM applications")
    cursor.execute("DELETE FROM resumes")
    cursor.execute("DELETE FROM ai_screenings")
    cursor.execute("DELETE FROM favorite_filters")

    # Seed resumes first so we can attach Resume_Id to applications.
    # Two resumes per applicant (an initial and an "updated" version) so the
    # resumes table has at least ten records per the project requirements.
    now = _now()
    resume_ids_by_user: dict[int, int] = {}
    for user_id, (first, last) in APPLICANT_INFO.items():
        for suffix in ("", "-updated"):
            payload = _fake_resume_bytes(user_id, f"{first} {last}")
            cursor.execute(
                """
                INSERT INTO resumes (
                    User_Id, Resume_Filename, Resume_MimeType, Resume_SizeBytes,
                    Resume_Data, Resume_UploadedAt
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    f"{first.lower()}-{last.lower()}{suffix}-resume.pdf",
                    "application/pdf",
                    len(payload),
                    payload,
                    now,
                ),
            )
            # Applications point at the most recent resume for the user.
            resume_ids_by_user[user_id] = cursor.lastrowid

    # Seed applications.
    application_ids: list[int] = []
    for row in SEED_APPLICATIONS:
        user_id, job_id, avail_offset, status, sub_offset, has_resume = row
        availability = _future(avail_offset)
        created = _past(sub_offset + 2) if sub_offset is not None else _past(1)
        submitted = _past(sub_offset) if sub_offset is not None else None
        declaration = 1 if status != "Draft" else 0
        resume_id = resume_ids_by_user.get(user_id) if has_resume else None
        cursor.execute(
            """
            INSERT INTO applications (
                User_Id, JobPosting_Id, Resume_Id, Application_Status,
                Availability_Date, Declaration_Accepted,
                Application_CreatedAt, Application_UpdatedAt,
                Application_SubmittedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, job_id, resume_id, status, availability, declaration,
                created, submitted or created, submitted,
            ),
        )
        application_ids.append(cursor.lastrowid)

    # Seed AI screenings for every non-Draft application so the ai_screenings
    # table also has at least ten records for staff demo purposes.
    # Recommendations reflect the actual fit between the seeded resume text
    # and the target job posting so the demo shows a spread of Yes / Maybe / No.
    #
    # user_id -> job_posting_id -> (Recommendation, Reasoning) override
    fit_map: dict[tuple[int, int], tuple[str, str]] = {
        # Emily Johnson (backend engineer)
        (6, 1): ("Yes", "Six years of backend Python and microservice experience align directly with the senior engineering requirements."),
        (6, 3): ("Maybe", "Strong SQL and analytical skills are present but the resume focuses on API engineering rather than reporting or data visualisation."),
        # Michael Brown (frontend developer)
        (7, 2): ("Yes", "The candidate has shipped production HTMX and Vue frontends and has the modern CSS and accessibility depth the role calls for."),
        (7, 5): ("No", "The resume shows no cloud, container or CI/CD ownership, which are the core DevOps requirements listed on the posting."),
        # Jessica Davis (retail) - deliberately weak matches for tech postings
        (8, 4): ("Maybe", "Strong people-management and customer-service background but no HR-specific tooling experience listed on the resume."),
        (8, 6): ("No", "Retail supervision background does not overlap with the pytest / Selenium test automation skills required for this role."),
        (8, 8): ("No", "Candidate has no design tooling, portfolio or user-research experience — the posting requires Figma and interaction design fundamentals."),
        # David Wilson (senior DevOps)
        (9, 1): ("Maybe", "Excellent platform engineering background but the posting is squarely a backend product-code role rather than infrastructure."),
        (9, 5): ("Yes", "Direct match: eight years running production Kubernetes on AWS with Terraform and GitHub Actions, exactly what the posting asks for."),
        # Sophie Martinez (marketing grad)
        (10, 2): ("No", "Marketing background with only basic HTML/CSS; the frontend developer role expects several years of production JavaScript work."),
        (10, 7): ("No", "Product manager posting requires stakeholder management and roadmap ownership experience the resume does not demonstrate."),
    }
    reasoning_default = {
        "Yes": "Candidate demonstrates strong alignment with the core requirements and appears well suited to progress.",
        "Maybe": "Candidate meets several requirements but has notable gaps; a phone screen is recommended to clarify fit.",
        "No": "Candidate lacks key skills or experience listed on the posting and is unlikely to be a strong match at this stage.",
    }
    for aid, row in zip(application_ids, SEED_APPLICATIONS):
        user_id, job_id, _, status, _, _ = row
        if status == "Draft":
            continue
        override = fit_map.get((user_id, job_id))
        if override:
            recommendation, reasoning = override
        else:
            recommendation = ("Yes", "Maybe", "No")[aid % 3]
            reasoning = reasoning_default[recommendation]
        cursor.execute(
            """
            INSERT INTO ai_screenings (
                Application_Id, Recommendation, Reasoning, Screening_CreatedAt
            ) VALUES (?, ?, ?, ?)
            """,
            (aid, recommendation, reasoning, now),
        )

    # Seed staff favorite filters (Staff user IDs 1..5). Ten presets so the
    # favorite_filters table meets the ten-record minimum too.
    filter_seeds = [
        (1, "Pending shortlist", "status=Submitted"),
        (1, "Ready to interview", "status=Shortlisted"),
        (1, "Ready to evaluate", "status=Interview Completed"),
        (2, "Recent hires", "status=Hired"),
        (2, "Withdrawn candidates", "status=Withdrawn"),
        (2, "Rejected candidates", "status=Rejected"),
        (3, "Emily's applications", "q=Emily"),
        (3, "Michael's applications", "q=Michael"),
        (4, "Interviews scheduled", "status=Interview Scheduled"),
        (5, "Evaluation stage", "status=Evaluation Completed"),
    ]
    cursor.executemany(
        """
        INSERT INTO favorite_filters (Staff_UserId, Filter_Name, Filter_Query, Filter_CreatedAt)
        VALUES (?, ?, ?, ?)
        """,
        [(sid, name, q, now) for (sid, name, q) in filter_seeds],
    )

    conn.commit()
    counts = {
        "applications": cursor.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
        "resumes": cursor.execute("SELECT COUNT(*) FROM resumes").fetchone()[0],
        "ai_screenings": cursor.execute("SELECT COUNT(*) FROM ai_screenings").fetchone()[0],
        "favorite_filters": cursor.execute("SELECT COUNT(*) FROM favorite_filters").fetchone()[0],
    }
    conn.close()
    print(f"Application database initialised: {counts} at {DATABASE_NAME}.")


if __name__ == "__main__":
    initialise()
