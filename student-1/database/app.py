from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "student1.db")

ALLOWED_FILE_TYPES = {
    "application/pdf",
}
MAX_FILE_SIZE = 5 * 1024 * 1024


def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# --- Profile endpoints ---

@app.get("/profiles/<int:profile_id>")
def get_profile(profile_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(dict(row))


@app.get("/profiles/by-user/<int:user_id>")
def get_profile_by_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(dict(row))


@app.post("/profiles")
def create_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["user_id", "phone"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT profile_id FROM profiles WHERE user_id = ?", (data["user_id"],)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Profile already exists for this user"}), 409

    now = datetime.utcnow().isoformat()
    cursor = conn.execute("""
        INSERT INTO profiles (user_id, phone, location, professional_title, summary, interests, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data.get("phone", ""), data.get("location", ""),
        data.get("professional_title", ""), data.get("summary", ""),
        data.get("interests", ""), now, now,
    ))
    conn.commit()
    profile_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/profiles/<int:profile_id>")
def update_profile(profile_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    conn = get_db()
    existing = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Profile not found"}), 404

    phone = data.get("phone", existing["phone"])
    if not phone:
        conn.close()
        return jsonify({"error": "phone is required"}), 400

    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE profiles SET phone=?, location=?,
        professional_title=?, summary=?, interests=?, updated_at=?
        WHERE profile_id=?
    """, (
        phone,
        data.get("location", existing["location"]),
        data.get("professional_title", existing["professional_title"]),
        data.get("summary", existing["summary"]),
        data.get("interests", existing["interests"]),
        now, profile_id,
    ))
    conn.commit()
    row = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/profiles/<int:profile_id>")
def delete_profile(profile_id):
    conn = get_db()
    existing = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Profile not found"}), 404
    conn.execute("DELETE FROM profiles WHERE profile_id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Profile deleted"}), 200


# --- Resume endpoints ---

@app.get("/profiles/<int:profile_id>/resumes")
def get_resumes(profile_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT resume_id, profile_id, file_name, file_type, uploaded_at, updated_at FROM resumes WHERE profile_id = ?",
        (profile_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


def _validate_resume_payload(data):
    """Validate a resume upload payload. Returns (file_name, file_type, file_bytes, None)
    on success, or (None, None, None, (response_json, status_code)) on failure."""
    file_name = data.get("file_name", "")
    file_type = data.get("file_type", "")
    file_data_b64 = data.get("file_data", "")

    if not file_name or not file_type or not file_data_b64:
        return None, None, None, ({"error": "file_name, file_type, and file_data are required"}, 400)

    if file_type not in ALLOWED_FILE_TYPES:
        return None, None, None, ({"error": "Only PDF files are allowed"}, 400)

    try:
        file_bytes = base64.b64decode(file_data_b64)
    except Exception:
        return None, None, None, ({"error": "Invalid base64 file_data"}, 400)

    if len(file_bytes) > MAX_FILE_SIZE:
        return None, None, None, ({"error": "File exceeds 5MB limit"}, 400)

    return file_name, file_type, file_bytes, None


@app.post("/profiles/<int:profile_id>/resumes")
def upload_resume(profile_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    file_name, file_type, file_bytes, error = _validate_resume_payload(data)
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    profile = conn.execute("SELECT profile_id FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    if not profile:
        conn.close()
        return jsonify({"error": "Profile not found"}), 404

    now = datetime.utcnow().isoformat()
    try:
        cursor = conn.execute("""
            INSERT INTO resumes (profile_id, file_name, file_type, file_data, uploaded_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (profile_id, file_name, file_type, file_bytes, now, now))
    except sqlite3.IntegrityError:
        conn.close()
        # UNIQUE(profile_id) violation: this profile already has a resume.
        return jsonify({"error": "This profile already has a resume. Delete the existing resume before uploading a new one."}), 409
    conn.commit()
    resume_id = cursor.lastrowid
    conn.close()
    return jsonify({"resume_id": resume_id, "file_name": file_name, "file_type": file_type, "uploaded_at": now}), 201


@app.post("/resumes")
def upload_unlinked_resume():
    """Create a resume with no profile_id (application-only upload).

    Ownership is tracked by the caller (student-3's applications.user_id FK), not here.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    file_name, file_type, file_bytes, error = _validate_resume_payload(data)
    if error:
        return jsonify(error[0]), error[1]

    conn = get_db()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute("""
        INSERT INTO resumes (profile_id, file_name, file_type, file_data, uploaded_at, updated_at)
        VALUES (NULL, ?, ?, ?, ?, ?)
    """, (file_name, file_type, file_bytes, now, now))
    conn.commit()
    resume_id = cursor.lastrowid
    conn.close()
    return jsonify({"resume_id": resume_id, "file_name": file_name, "file_type": file_type, "uploaded_at": now}), 201


@app.get("/resumes/<int:resume_id>")
def get_resume_meta(resume_id):
    conn = get_db()
    row = conn.execute(
        "SELECT resume_id, profile_id, file_name, file_type, uploaded_at, updated_at FROM resumes WHERE resume_id = ?",
        (resume_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Resume not found"}), 404
    return jsonify(dict(row))


@app.get("/resumes/<int:resume_id>/file")
def get_resume_file(resume_id):
    conn = get_db()
    row = conn.execute("SELECT file_name, file_type, file_data FROM resumes WHERE resume_id = ?", (resume_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Resume not found"}), 404

    from flask import Response
    return Response(
        row["file_data"],
        mimetype=row["file_type"],
        headers={"Content-Disposition": f'attachment; filename="{row["file_name"]}"'}
    )


@app.delete("/resumes/<int:resume_id>")
def delete_resume(resume_id):
    conn = get_db()
    existing = conn.execute("SELECT resume_id FROM resumes WHERE resume_id = ?", (resume_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Resume not found"}), 404
    conn.execute("DELETE FROM resumes WHERE resume_id = ?", (resume_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Resume deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6001, debug=True)
