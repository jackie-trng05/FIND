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
    (1, 4, 1, "2026-08-10 10:00", "https://meet.find.app/int-1", "Interview Scheduled", ""),
    (2, 7, 1, "2026-08-04 14:00", "https://meet.find.app/int-2", "Interview Completed", _notes(
        "Strong grasp of test automation frameworks and Python.",
        "Relevant degree in Computer Science.",
        "Clear, concise communicator throughout.",
        "Worked through the debugging scenario methodically.",
        "Punctual and well-prepared.",
    )),
    (3, 2, 1, "2026-08-12 14:30", "https://meet.find.app/int-3", "Interview Completed", _notes(
        "Excellent knowledge of React and modern frontend tooling. Solved the live coding challenge efficiently.",
        "Bachelor's in Software Engineering with honours. Completed relevant online certifications.",
        "Articulate and confident. Explained complex concepts clearly.",
        "Approached the system design question with a well-structured plan.",
        "Professional demeanour, arrived early, asked thoughtful follow-up questions.",
    )),
    (4, 5, 1, "2026-08-06 09:00", "https://meet.find.app/int-4", "Interview Completed", _notes(
        "Basic understanding of backend APIs but struggled with database design questions.",
        "Relevant diploma but limited formal CS education.",
        "Responses were sometimes unclear and lacked depth.",
        "Had difficulty breaking down the problem into smaller steps.",
        "Polite and on time but seemed unprepared for technical questions.",
    )),
    (5, 6, 2, "2026-08-07 11:00", "https://meet.find.app/int-5", "Interview Completed", _notes(
        "Strong full-stack skills. Demonstrated deep understanding of microservices architecture.",
        "Master's in Computer Science with research experience in distributed systems.",
        "Excellent communicator. Explained trade-offs between approaches clearly.",
        "Solved the algorithmic challenge with an optimal solution on first attempt.",
        "Highly professional. Well-researched about the company and role.",
    )),
    (6, 8, 2, "2026-08-08 13:00", "https://meet.find.app/int-6", "Interview Completed", _notes(
        "Limited knowledge of the required tech stack. Could not complete the coding exercise.",
        "Associate degree, no formal CS training.",
        "Struggled to explain previous project experience coherently.",
        "Could not identify the root cause in the debugging scenario.",
        "Arrived late and appeared disorganised.",
    )),
    (7, 10, 3, "2026-08-09 10:00", "https://meet.find.app/int-7", "Interview Completed", _notes(
        "Solid understanding of Python and Django. Good knowledge of REST API design patterns.",
        "Bachelor's in Information Technology. Completed AWS certification.",
        "Communicated well but could be more concise in technical explanations.",
        "Good problem-solving approach. Used whiteboard effectively to diagram the solution.",
        "Professional and well-prepared. Asked insightful questions about team culture.",
    )),
    (8, 12, 3, "2026-08-11 15:00", "https://meet.find.app/int-8", "Interview Completed", _notes(
        "Outstanding technical depth across frontend and backend. Built a working prototype during the interview.",
        "PhD in Computer Science with publications in ML and software engineering.",
        "Exceptional communicator. Presented ideas with clarity and enthusiasm.",
        "Tackled the hardest problem variant and found an elegant solution.",
        "Impeccable professionalism. Followed up with a thoughtful thank-you email.",
    )),
    (9, 14, 1, "2026-08-13 09:30", "https://meet.find.app/int-9", "Interview Completed", _notes(
        "Decent grasp of JavaScript and Node.js. Needs improvement on TypeScript.",
        "Bachelor's in IT. Currently completing a bootcamp on cloud technologies.",
        "Communicates ideas adequately but could improve technical vocabulary.",
        "Took a methodical approach but ran out of time on the second problem.",
        "Friendly and professional. Showed genuine interest in learning.",
    )),
    (10, 15, 4, "2026-08-14 11:00", "https://meet.find.app/int-10", "Interview Completed", _notes(
        "Good knowledge of containerisation and CI/CD pipelines. Familiar with Kubernetes.",
        "Bachelor's in Computer Science with DevOps specialisation.",
        "Clear communicator. Explained deployment strategies well.",
        "Identified the bottleneck in the scenario quickly and proposed a practical fix.",
        "Well-prepared and professional throughout the interview.",
    )),
    (11, 16, 4, "2026-08-15 14:00", "https://meet.find.app/int-11", "Interview Completed", _notes(
        "Solid data analysis skills. Comfortable with SQL and Python pandas.",
        "Master's in Data Science. Published research on predictive modelling.",
        "Good communicator, especially when discussing statistical concepts.",
        "Applied a creative approach to the case study and arrived at a sound conclusion.",
        "Very professional. Brought a portfolio of past work to discuss.",
    )),
    (12, 17, 4, "2026-08-16 10:00", "https://meet.find.app/int-12", "Interview Completed", _notes(
        "Minimal technical knowledge relevant to the role.",
        "Unrelated degree. No certifications or self-study evidence.",
        "Difficulty explaining even basic concepts from their resume.",
        "Could not attempt the problem-solving exercise.",
        "Arrived on time but otherwise showed minimal engagement.",
    )),
    (13, 18, 1, "2026-08-20 09:00", "https://meet.find.app/int-13", "Interview Completed", _notes(
        "Strong understanding of React and state management patterns.",
        "Bachelor's in Software Engineering. Relevant internship experience.",
        "Communicated confidently. Good at explaining design decisions.",
        "Solved the take-home challenge creatively with clean code.",
        "Professional and enthusiastic about the opportunity.",
    )),
    (14, 19, 2, "2026-08-21 11:30", "https://meet.find.app/int-14", "Interview Completed", _notes(
        "Good grasp of database design and SQL optimisation.",
        "Bachelor's in Computer Science. Oracle certification.",
        "Articulate and well-organised in responses.",
        "Worked through the normalisation problem systematically.",
        "Professional demeanour. Asked good questions about the team.",
    )),
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
