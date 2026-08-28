from flask import Flask, jsonify, request
import os
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/interview.db"

INTERVIEW_COLUMNS = (
    "interview_id, application_id, user_id, interview_datetime, "
    "interview_link, interview_notes"
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    return jsonify({"service": "student-4-interview-db", "status": "running"})


@app.get("/interviews")
def get_interviews():
    conn = get_db_connection()
    interviews = conn.execute(
        f"SELECT {INTERVIEW_COLUMNS} FROM interviews ORDER BY interview_datetime"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in interviews])


@app.get("/interviews/<int:interview_id>")
def get_interview(interview_id):
    conn = get_db_connection()
    interview = conn.execute(
        f"SELECT {INTERVIEW_COLUMNS} FROM interviews WHERE interview_id = ?",
        (interview_id,),
    ).fetchone()
    conn.close()

    if interview is None:
        return jsonify({"error": "Interview not found"}), 404

    return jsonify(dict(interview))


@app.post("/interviews")
def create_interview():
    data = request.get_json(silent=True) or {}

    required = ["application_id", "user_id", "interview_datetime"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO interviews (
            application_id, user_id, interview_datetime,
            interview_link, interview_notes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data["application_id"],
            data["user_id"],
            data["interview_datetime"],
            data.get("interview_link", ""),
            data.get("interview_notes", ""),
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    interview = conn.execute(
        f"SELECT {INTERVIEW_COLUMNS} FROM interviews WHERE interview_id = ?",
        (new_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(interview)), 201


@app.put("/interviews/<int:interview_id>")
def update_interview(interview_id):
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    existing = conn.execute(
        f"SELECT {INTERVIEW_COLUMNS} FROM interviews WHERE interview_id = ?",
        (interview_id,),
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Interview not found"}), 404

    existing = dict(existing)
    updated = {
        "application_id": data.get("application_id", existing["application_id"]),
        "user_id": data.get("user_id", existing["user_id"]),
        "interview_datetime": data.get("interview_datetime", existing["interview_datetime"]),
        "interview_link": data.get("interview_link", existing["interview_link"]),
        "interview_notes": data.get("interview_notes", existing["interview_notes"]),
    }

    conn.execute(
        """
        UPDATE interviews SET
            application_id = ?,
            user_id = ?,
            interview_datetime = ?,
            interview_link = ?,
            interview_notes = ?
        WHERE interview_id = ?
        """,
        (
            updated["application_id"],
            updated["user_id"],
            updated["interview_datetime"],
            updated["interview_link"],
            updated["interview_notes"],
            interview_id,
        ),
    )
    conn.commit()
    interview = conn.execute(
        f"SELECT {INTERVIEW_COLUMNS} FROM interviews WHERE interview_id = ?",
        (interview_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(interview))


@app.delete("/interviews/<int:interview_id>")
def delete_interview(interview_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT interview_id FROM interviews WHERE interview_id = ?",
        (interview_id,),
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Interview not found"}), 404

    conn.execute("DELETE FROM interviews WHERE interview_id = ?", (interview_id,))
    conn.commit()
    conn.close()

    return jsonify({"deleted": interview_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "6004")), debug=True)
