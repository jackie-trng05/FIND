"""Student 2 Database microservice (Job Posting Management).

A thin SQLite-backed REST API. It is the only service that talks to the
database file; the backend/API microservice communicates with it over HTTP.

Container port: 6002 (host port 16009 per the canonical port table).
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DATABASE_NAME = os.path.join(DATA_DIR, "job_postings.db")
PORT = int(os.getenv("PORT", "6002"))

app = Flask(__name__)

# Columns a client is allowed to write. JobPosting_Id and the timestamp/status
# columns are managed by this service.
EDITABLE_FIELDS = (
    "User_Id",
    "Job_Title",
    "Job_Description",
    "Job_Type",
    "Location",
    "Salary_Range",
    "Requirements",
    "Application_Deadline",
)

VALID_STATUSES = ("Draft", "Published")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def index():
    return jsonify({"service": "student-2-db", "status": "running"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/job-postings")
def list_job_postings():
    """Return job postings, optionally filtered.

    Query params (all optional):
      status    - 'Draft' or 'Published'
      job_type  - e.g. 'Full time'
      location  - substring match
      q         - free-text search over title/description/requirements
    """
    status = request.args.get("status", "").strip()
    job_type = request.args.get("job_type", "").strip()
    location = request.args.get("location", "").strip()
    q = request.args.get("q", "").strip()

    clauses = []
    params = []
    if status:
        clauses.append("JobPosting_Status = ?")
        params.append(status)
    if job_type:
        clauses.append("Job_Type = ?")
        params.append(job_type)
    if location:
        clauses.append("Location LIKE ?")
        params.append(f"%{location}%")
    if q:
        clauses.append(
            "(Job_Title LIKE ? OR Job_Description LIKE ? OR Requirements LIKE ?)"
        )
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    sql = "SELECT * FROM job_postings"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY JobPosting_UpdatedAt DESC, JobPosting_Id DESC"

    conn = get_db_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/job-postings/<int:posting_id>")
def get_job_posting(posting_id: int):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Job posting not found"}), 404
    return jsonify(dict(row))


@app.post("/job-postings")
def create_job_posting():
    data = request.get_json(silent=True) or {}

    if not str(data.get("Job_Title", "")).strip():
        return jsonify({"error": "Job_Title is required"}), 400
    try:
        user_id = int(data.get("User_Id"))
    except (TypeError, ValueError):
        return jsonify({"error": "User_Id must be an integer"}), 400

    status = str(data.get("JobPosting_Status", "Draft")).strip() or "Draft"
    if status not in VALID_STATUSES:
        return jsonify({"error": f"JobPosting_Status must be one of {VALID_STATUSES}"}), 400

    now = _now()
    values = {field: str(data.get(field, "")).strip() for field in EDITABLE_FIELDS}
    values["User_Id"] = user_id
    values["Job_Type"] = values["Job_Type"] or "Full time"

    published_at = now if status == "Published" else None

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO job_postings (
            User_Id, Job_Title, Job_Description, Job_Type, Location,
            Salary_Range, Requirements,
            Application_Deadline, JobPosting_Status,
            JobPosting_CreatedAt, JobPosting_UpdatedAt, JobPosting_PublishedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["User_Id"], values["Job_Title"], values["Job_Description"],
            values["Job_Type"], values["Location"], values["Salary_Range"],
            values["Requirements"],
            values["Application_Deadline"],
            status, now, now, published_at,
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    row = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (new_id,)
    ).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/job-postings/<int:posting_id>")
def update_job_posting(posting_id: int):
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Job posting not found"}), 404

    updates = {}
    for field in EDITABLE_FIELDS:
        if field in data:
            if field == "User_Id":
                try:
                    updates[field] = int(data[field])
                except (TypeError, ValueError):
                    conn.close()
                    return jsonify({"error": "User_Id must be an integer"}), 400
            else:
                updates[field] = str(data[field]).strip()

    if "JobPosting_Status" in data:
        status = str(data["JobPosting_Status"]).strip()
        if status not in VALID_STATUSES:
            conn.close()
            return jsonify({"error": f"JobPosting_Status must be one of {VALID_STATUSES}"}), 400
        updates["JobPosting_Status"] = status

    if not updates:
        conn.close()
        return jsonify({"error": "No editable fields supplied"}), 400

    updates["JobPosting_UpdatedAt"] = _now()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [posting_id]
    conn.execute(
        f"UPDATE job_postings SET {set_clause} WHERE JobPosting_Id = ?", params
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.put("/job-postings/<int:posting_id>/publish")
def publish_job_posting(posting_id: int):
    return _set_status(posting_id, "Published")


@app.put("/job-postings/<int:posting_id>/unpublish")
def unpublish_job_posting(posting_id: int):
    return _set_status(posting_id, "Draft")


def _set_status(posting_id: int, status: str):
    now = _now()
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Job posting not found"}), 404

    published_at = now if status == "Published" else None
    conn.execute(
        """
        UPDATE job_postings
        SET JobPosting_Status = ?, JobPosting_PublishedAt = ?, JobPosting_UpdatedAt = ?
        WHERE JobPosting_Id = ?
        """,
        (status, published_at, now, posting_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/job-postings/<int:posting_id>")
def delete_job_posting(posting_id: int):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT JobPosting_Id FROM job_postings WHERE JobPosting_Id = ?", (posting_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Job posting not found"}), 404
    conn.execute("DELETE FROM job_postings WHERE JobPosting_Id = ?", (posting_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": posting_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
