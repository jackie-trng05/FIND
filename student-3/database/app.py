"""Student 3 Database microservice (Application Management).

A thin SQLite-backed REST API. It is the only service that talks to the
database file; the backend/API microservice communicates with it over HTTP.

Container port: 6003 (host port 16012 per the canonical port table).

Tables managed here:
  * applications        - Candidate applications (Draft / Submitted / ...)
  * resumes             - Uploaded resume BLOBs
  * ai_screenings       - Cached AI screening results per application
  * favorite_filters    - Staff-saved filter presets for the All Applications view
"""

import base64
import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_file
from io import BytesIO

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
DATABASE_NAME = os.path.join(DATA_DIR, "applications.db")
PORT = int(os.getenv("PORT", "6003"))

app = Flask(__name__)


EDITABLE_APPLICATION_FIELDS = (
    "User_Id",
    "JobPosting_Id",
    "Resume_Id",
    "Availability_Date",
    "Declaration_Accepted",
)

VALID_STATUSES = (
    "Draft",
    "Submitted",
    "Shortlisted",
    "Interview Requested",
    "Interview Scheduled",
    "Interview Completed",
    "Evaluation Completed",
    "Hired",
    "Rejected",
    "Withdrawn",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


# --------------------------------------------------------------------------- #
# Health                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/")
def index():
    return jsonify({"service": "student-3-db", "status": "running"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------------- #
# Applications                                                                #
# --------------------------------------------------------------------------- #

@app.get("/applications")
def list_applications():
    """Return applications, optionally filtered.

    Query params (all optional):
      user_id           - only applications belonging to this applicant
      job_posting_id    - only applications for this posting
      status            - exact status match
      q                 - free-text (currently searches Availability_Date)
    """
    user_id = request.args.get("user_id", "").strip()
    job_posting_id = request.args.get("job_posting_id", "").strip()
    status = request.args.get("status", "").strip()

    clauses = []
    params: list = []
    if user_id:
        clauses.append("User_Id = ?")
        params.append(user_id)
    if job_posting_id:
        clauses.append("JobPosting_Id = ?")
        params.append(job_posting_id)
    if status:
        clauses.append("Application_Status = ?")
        params.append(status)

    sql = "SELECT * FROM applications"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY Application_UpdatedAt DESC, Application_Id DESC"

    conn = get_db_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([_row_to_dict(r) for r in rows])


@app.get("/applications/<int:application_id>")
def get_application(application_id: int):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(_row_to_dict(row))


@app.post("/applications")
def create_application():
    data = request.get_json(silent=True) or {}

    try:
        user_id = int(data["User_Id"])
        job_posting_id = int(data["JobPosting_Id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "User_Id and JobPosting_Id are required integers"}), 400

    # Business rule: no duplicate active (non-Draft, non-Withdrawn, non-Rejected)
    # applications from the same candidate for the same posting. Draft duplicates
    # are also blocked so the candidate has a single working document per posting.
    conn = get_db_connection()
    existing = conn.execute(
        """
        SELECT Application_Id, Application_Status FROM applications
        WHERE User_Id = ? AND JobPosting_Id = ?
          AND Application_Status NOT IN ('Withdrawn', 'Rejected')
        """,
        (user_id, job_posting_id),
    ).fetchone()
    if existing is not None:
        conn.close()
        return jsonify({
            "error": "You already have an application for this job posting.",
            "application_id": existing["Application_Id"],
            "application_status": existing["Application_Status"],
        }), 409

    status = str(data.get("Application_Status", "Draft")).strip() or "Draft"
    if status not in VALID_STATUSES:
        conn.close()
        return jsonify({"error": f"Application_Status must be one of {VALID_STATUSES}"}), 400

    availability = str(data.get("Availability_Date", "")).strip()
    declaration = 1 if data.get("Declaration_Accepted") in (1, "1", True, "true") else 0
    resume_id = data.get("Resume_Id")
    if resume_id in ("", None):
        resume_id = None
    else:
        try:
            resume_id = int(resume_id)
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"error": "Resume_Id must be an integer"}), 400

    now = _now()
    submitted_at = now if status != "Draft" else None
    cursor = conn.execute(
        """
        INSERT INTO applications (
            User_Id, JobPosting_Id, Resume_Id, Application_Status,
            Availability_Date, Declaration_Accepted,
            Application_CreatedAt, Application_UpdatedAt, Application_SubmittedAt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, job_posting_id, resume_id, status, availability, declaration,
         now, now, submitted_at),
    )
    new_id = cursor.lastrowid
    conn.commit()
    row = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (new_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row)), 201


@app.put("/applications/<int:application_id>")
def update_application(application_id: int):
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Application not found"}), 404

    updates: dict = {}
    for field in EDITABLE_APPLICATION_FIELDS:
        if field in data:
            value = data[field]
            if field in ("User_Id", "JobPosting_Id"):
                try:
                    updates[field] = int(value)
                except (TypeError, ValueError):
                    conn.close()
                    return jsonify({"error": f"{field} must be an integer"}), 400
            elif field == "Resume_Id":
                if value in ("", None):
                    updates[field] = None
                else:
                    try:
                        updates[field] = int(value)
                    except (TypeError, ValueError):
                        conn.close()
                        return jsonify({"error": "Resume_Id must be an integer"}), 400
            elif field == "Declaration_Accepted":
                updates[field] = 1 if value in (1, "1", True, "true") else 0
            else:
                updates[field] = str(value).strip()

    if "Application_Status" in data:
        status = str(data["Application_Status"]).strip()
        if status not in VALID_STATUSES:
            conn.close()
            return jsonify({"error": f"Application_Status must be one of {VALID_STATUSES}"}), 400
        updates["Application_Status"] = status
        # Stamp a submission time the first time the record leaves Draft.
        if status != "Draft" and not existing["Application_SubmittedAt"]:
            updates["Application_SubmittedAt"] = _now()

    if not updates:
        conn.close()
        return jsonify({"error": "No editable fields supplied"}), 400

    updates["Application_UpdatedAt"] = _now()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [application_id]
    conn.execute(
        f"UPDATE applications SET {set_clause} WHERE Application_Id = ?", params
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row))


@app.put("/applications/<int:application_id>/submit")
def submit_application(application_id: int):
    """Move an application out of Draft into Submitted."""
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if existing["Application_Status"] != "Draft":
        conn.close()
        return jsonify({"error": "Only Draft applications can be submitted"}), 400
    if not existing["Resume_Id"]:
        conn.close()
        return jsonify({"error": "Resume is required to submit"}), 400
    if not existing["Declaration_Accepted"]:
        conn.close()
        return jsonify({"error": "Declaration must be accepted to submit"}), 400

    now = _now()
    conn.execute(
        """
        UPDATE applications
        SET Application_Status = 'Submitted',
            Application_SubmittedAt = ?,
            Application_UpdatedAt = ?
        WHERE Application_Id = ?
        """,
        (now, now, application_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row))


@app.put("/applications/<int:application_id>/withdraw")
def withdraw_application(application_id: int):
    withdrawable = (
        "Draft", "Submitted", "Shortlisted", "Interview Requested",
        "Interview Scheduled",
        "Interview Completed", "Evaluation Completed",
    )
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if existing["Application_Status"] not in withdrawable:
        conn.close()
        return jsonify({
            "error": f"Cannot withdraw application in status "
                     f"{existing['Application_Status']!r}"
        }), 400
    now = _now()
    conn.execute(
        """
        UPDATE applications
        SET Application_Status = 'Withdrawn', Application_UpdatedAt = ?
        WHERE Application_Id = ?
        """,
        (now, application_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM applications WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row))


@app.delete("/applications/<int:application_id>")
def delete_application(application_id: int):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT Application_Id, Application_Status, Resume_Id "
        "FROM applications WHERE Application_Id = ?",
        (application_id,),
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    # Only Draft applications may be hard-deleted; other statuses must be
    # withdrawn so the recruitment audit trail is preserved.
    if existing["Application_Status"] != "Draft":
        conn.close()
        return jsonify({
            "error": "Only Draft applications can be deleted. Withdraw instead."
        }), 400
    conn.execute(
        "DELETE FROM ai_screenings WHERE Application_Id = ?", (application_id,)
    )
    conn.execute(
        "DELETE FROM applications WHERE Application_Id = ?", (application_id,)
    )
    conn.commit()
    conn.close()
    return jsonify({"deleted": application_id})


# --------------------------------------------------------------------------- #
# Resumes                                                                     #
# --------------------------------------------------------------------------- #

@app.get("/resumes")
def list_resumes():
    user_id = request.args.get("user_id", "").strip()
    conn = get_db_connection()
    if user_id:
        rows = conn.execute(
            "SELECT Resume_Id, User_Id, Resume_Filename, Resume_MimeType, "
            "Resume_SizeBytes, Resume_UploadedAt FROM resumes "
            "WHERE User_Id = ? ORDER BY Resume_UploadedAt DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT Resume_Id, User_Id, Resume_Filename, Resume_MimeType, "
            "Resume_SizeBytes, Resume_UploadedAt FROM resumes "
            "ORDER BY Resume_UploadedAt DESC"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/resumes/<int:resume_id>")
def get_resume_metadata(resume_id: int):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT Resume_Id, User_Id, Resume_Filename, Resume_MimeType, "
        "Resume_SizeBytes, Resume_UploadedAt FROM resumes "
        "WHERE Resume_Id = ?",
        (resume_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Resume not found"}), 404
    return jsonify(dict(row))


@app.get("/resumes/<int:resume_id>/download")
def download_resume(resume_id: int):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT Resume_Filename, Resume_MimeType, Resume_Data "
        "FROM resumes WHERE Resume_Id = ?",
        (resume_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Resume not found"}), 404
    return send_file(
        BytesIO(row["Resume_Data"]),
        mimetype=row["Resume_MimeType"],
        as_attachment=True,
        download_name=row["Resume_Filename"],
    )


@app.post("/resumes")
def create_resume():
    """Accepts base64-encoded file payload from the backend service.

    JSON body:
      {
        "User_Id": int,
        "Resume_Filename": str,
        "Resume_MimeType": "application/pdf" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Resume_Data_Base64": str
      }
    """
    data = request.get_json(silent=True) or {}
    try:
        user_id = int(data["User_Id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "User_Id is required"}), 400

    filename = str(data.get("Resume_Filename", "")).strip()
    mimetype = str(data.get("Resume_MimeType", "")).strip()
    b64 = data.get("Resume_Data_Base64", "")

    if not filename or not mimetype or not b64:
        return jsonify({"error": "Resume_Filename, Resume_MimeType and Resume_Data_Base64 are required"}), 400

    try:
        payload = base64.b64decode(b64, validate=True)
    except Exception:
        return jsonify({"error": "Resume_Data_Base64 could not be decoded"}), 400

    now = _now()
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO resumes (
            User_Id, Resume_Filename, Resume_MimeType, Resume_SizeBytes,
            Resume_Data, Resume_UploadedAt
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, filename, mimetype, len(payload), payload, now),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({
        "Resume_Id": new_id,
        "User_Id": user_id,
        "Resume_Filename": filename,
        "Resume_MimeType": mimetype,
        "Resume_SizeBytes": len(payload),
        "Resume_UploadedAt": now,
    }), 201


# --------------------------------------------------------------------------- #
# AI screenings                                                               #
# --------------------------------------------------------------------------- #

@app.get("/ai-screenings/<int:application_id>")
def get_ai_screening(application_id: int):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM ai_screenings WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "No screening found"}), 404
    return jsonify(_row_to_dict(row))


@app.put("/ai-screenings/<int:application_id>")
def upsert_ai_screening(application_id: int):
    data = request.get_json(silent=True) or {}
    recommendation = str(data.get("Recommendation", "Maybe")).strip() or "Maybe"
    if recommendation not in ("Yes", "No", "Maybe"):
        recommendation = "Maybe"
    reasoning = str(data.get("Reasoning", "")).strip()
    now = _now()

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT Screening_Id FROM ai_screenings WHERE Application_Id = ?",
        (application_id,),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO ai_screenings (
                Application_Id, Recommendation, Reasoning, Screening_CreatedAt
            ) VALUES (?, ?, ?, ?)
            """,
            (application_id, recommendation, reasoning, now),
        )
    else:
        conn.execute(
            """
            UPDATE ai_screenings
            SET Recommendation = ?, Reasoning = ?, Screening_CreatedAt = ?
            WHERE Application_Id = ?
            """,
            (recommendation, reasoning, now, application_id),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM ai_screenings WHERE Application_Id = ?", (application_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row))


# --------------------------------------------------------------------------- #
# Favorite filters                                                            #
# --------------------------------------------------------------------------- #

@app.get("/favorite-filters")
def list_favorite_filters():
    staff_user_id = request.args.get("staff_user_id", "").strip()
    conn = get_db_connection()
    if staff_user_id:
        rows = conn.execute(
            "SELECT * FROM favorite_filters WHERE Staff_UserId = ? "
            "ORDER BY Filter_CreatedAt DESC",
            (staff_user_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM favorite_filters ORDER BY Filter_CreatedAt DESC"
        ).fetchall()
    conn.close()
    return jsonify([_row_to_dict(r) for r in rows])


@app.post("/favorite-filters")
def create_favorite_filter():
    data = request.get_json(silent=True) or {}
    try:
        staff_user_id = int(data["Staff_UserId"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Staff_UserId is required"}), 400
    name = str(data.get("Filter_Name", "")).strip()
    query = str(data.get("Filter_Query", "")).strip()
    if not name:
        return jsonify({"error": "Filter_Name is required"}), 400

    now = _now()
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO favorite_filters (Staff_UserId, Filter_Name, Filter_Query, Filter_CreatedAt)
        VALUES (?, ?, ?, ?)
        """,
        (staff_user_id, name, query, now),
    )
    new_id = cursor.lastrowid
    conn.commit()
    row = conn.execute(
        "SELECT * FROM favorite_filters WHERE Filter_Id = ?", (new_id,)
    ).fetchone()
    conn.close()
    return jsonify(_row_to_dict(row)), 201


@app.delete("/favorite-filters/<int:filter_id>")
def delete_favorite_filter(filter_id: int):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT Filter_Id FROM favorite_filters WHERE Filter_Id = ?", (filter_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Filter not found"}), 404
    conn.execute("DELETE FROM favorite_filters WHERE Filter_Id = ?", (filter_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": filter_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
