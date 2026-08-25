from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app, supports_credentials=True)

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student3.db")

VALID_STATUSES = {
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
}

EDITABLE_FIELDS = (
    "user_id",
    "job_posting_id",
    "resume_id",
    "availability_date",
    "declaration_accepted",
)

WITHDRAWABLE_STATUSES = {
    "Draft",
    "Submitted",
    "Shortlisted",
    "Interview Requested",
    "Interview Scheduled",
    "Interview Completed",
    "Evaluation Completed",
}


def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# --- Application endpoints ---

@app.get("/applications")
def list_applications():
    user_id = request.args.get("user_id", "").strip()
    job_posting_id = request.args.get("job_posting_id", "").strip()
    status = request.args.get("status", "").strip()

    clauses = []
    params = []
    if user_id:
        clauses.append("user_id = ?")
        params.append(user_id)
    if job_posting_id:
        clauses.append("job_posting_id = ?")
        params.append(job_posting_id)
    if status:
        clauses.append("application_status = ?")
        params.append(status)

    sql = "SELECT * FROM applications"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY updated_at DESC, application_id DESC"

    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/applications/<int:application_id>")
def get_application(application_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(dict(row))


@app.post("/applications")
def create_application():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    try:
        user_id = int(data["user_id"])
        job_posting_id = int(data["job_posting_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "user_id and job_posting_id are required integers"}), 400

    status = str(data.get("application_status", "Draft")).strip() or "Draft"
    if status not in VALID_STATUSES:
        return jsonify({"error": f"application_status must be one of {sorted(VALID_STATUSES)}"}), 400

    resume_id = data.get("resume_id")
    if resume_id in ("", None):
        resume_id = None
    else:
        try:
            resume_id = int(resume_id)
        except (TypeError, ValueError):
            return jsonify({"error": "resume_id must be an integer"}), 400

    availability = str(data.get("availability_date", "")).strip()
    declaration = 1 if data.get("declaration_accepted") in (1, "1", True, "true") else 0

    conn = get_db()
    existing = conn.execute("""
        SELECT application_id, application_status FROM applications
        WHERE user_id = ? AND job_posting_id = ?
        AND application_status NOT IN ('Withdrawn', 'Rejected')
    """, (user_id, job_posting_id)).fetchone()
    if existing:
        conn.close()
        return jsonify({
            "error": "You already have an application for this job posting.",
            "application_id": existing["application_id"],
            "application_status": existing["application_status"],
        }), 409

    now = utc_now_iso()
    submitted_at = now if status != "Draft" else None
    cursor = conn.execute("""
        INSERT INTO applications (user_id, job_posting_id, resume_id, application_status,
        availability_date, declaration_accepted, created_at, updated_at, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, job_posting_id, resume_id, status,
        availability, declaration, now, now, submitted_at,
    ))
    conn.commit()
    application_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/applications/<int:application_id>")
def update_application(application_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Application not found"}), 404

    updates = {}
    for field in EDITABLE_FIELDS:
        if field in data:
            value = data[field]
            if field in ("user_id", "job_posting_id"):
                try:
                    updates[field] = int(value)
                except (TypeError, ValueError):
                    conn.close()
                    return jsonify({"error": f"{field} must be an integer"}), 400
            elif field == "resume_id":
                if value in ("", None):
                    updates[field] = None
                else:
                    try:
                        updates[field] = int(value)
                    except (TypeError, ValueError):
                        conn.close()
                        return jsonify({"error": "resume_id must be an integer"}), 400
            elif field == "declaration_accepted":
                updates[field] = 1 if value in (1, "1", True, "true") else 0
            else:
                updates[field] = str(value).strip()

    if "application_status" in data:
        status = str(data["application_status"]).strip()
        if status not in VALID_STATUSES:
            conn.close()
            return jsonify({"error": f"application_status must be one of {sorted(VALID_STATUSES)}"}), 400
        updates["application_status"] = status
        if status != "Draft" and not existing["submitted_at"]:
            updates["submitted_at"] = utc_now_iso()

    if not updates:
        conn.close()
        return jsonify({"error": "No editable fields supplied"}), 400

    updates["updated_at"] = utc_now_iso()
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [application_id]
    conn.execute(f"UPDATE applications SET {set_clause} WHERE application_id = ?", params)
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.put("/applications/<int:application_id>/submit")
def submit_application(application_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if existing["application_status"] != "Draft":
        conn.close()
        return jsonify({"error": "Only Draft applications can be submitted"}), 400
    if not existing["resume_id"]:
        conn.close()
        return jsonify({"error": "Resume is required to submit"}), 400
    if not existing["declaration_accepted"]:
        conn.close()
        return jsonify({"error": "Declaration must be accepted to submit"}), 400

    now = utc_now_iso()
    conn.execute("""
        UPDATE applications
        SET application_status = 'Submitted', submitted_at = ?, updated_at = ?
        WHERE application_id = ?
    """, (now, now, application_id))
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.put("/applications/<int:application_id>/withdraw")
def withdraw_application(application_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if existing["application_status"] not in WITHDRAWABLE_STATUSES:
        conn.close()
        return jsonify({"error": f"Cannot withdraw application in status {existing['application_status']!r}"}), 400

    now = utc_now_iso()
    conn.execute("""
        UPDATE applications
        SET application_status = 'Withdrawn', updated_at = ?
        WHERE application_id = ?
    """, (now, application_id))
    conn.commit()
    row = conn.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/applications/<int:application_id>")
def delete_application(application_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT application_id, application_status FROM applications WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Application not found"}), 404
    if existing["application_status"] != "Draft":
        conn.close()
        return jsonify({"error": "Only Draft applications can be deleted. Withdraw instead."}), 400
    conn.execute("DELETE FROM applications WHERE application_id = ?", (application_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Application deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6003, debug=True)
