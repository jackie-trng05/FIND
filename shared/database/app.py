from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DATABASE_NAME = "/app/data/find.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    return jsonify({"service": "shared-database", "status": "running"})


@app.get("/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/users")
def get_users():
    conn = get_db_connection()
    users = conn.execute(
        "SELECT user_id, user_email, user_role, user_first_name, user_last_name, created_at FROM users"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in users])


@app.get("/users/<int:user_id>")
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT user_id, user_email, user_role, user_first_name, user_last_name, created_at FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


@app.get("/users/by-email")
def get_user_by_email():
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email parameter required"}), 400

    conn = get_db_connection()
    user = conn.execute(
        "SELECT user_id, user_email, user_password_hash, user_role, user_first_name, user_last_name FROM users WHERE user_email = ?",
        (email,),
    ).fetchone()
    conn.close()
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


@app.post("/users")
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["user_email", "user_password_hash", "user_role"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    if data["user_role"] not in ("applicant", "staff"):
        return jsonify({"error": "user_role must be 'applicant' or 'staff'"}), 400

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO users (user_email, user_password_hash, user_role, user_first_name, user_last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data["user_email"].strip().lower(),
                data["user_password_hash"],
                data["user_role"],
                data.get("user_first_name", ""),
                data.get("user_last_name", ""),
            ),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"}), 409
    conn.close()
    return jsonify({"user_id": user_id, "message": "User created"}), 201


@app.post("/sessions")
def create_session():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["user_id", "session_token", "expires_at"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_db_connection()
    conn.execute(
        """INSERT INTO sessions (user_id, session_token, expires_at)
           VALUES (?, ?, ?)""",
        (data["user_id"], data["session_token"], data["expires_at"]),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Session created"}), 201


@app.get("/sessions/by-token")
def get_session_by_token():
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"error": "token parameter required"}), 400

    conn = get_db_connection()
    session = conn.execute(
        """SELECT s.session_id, s.user_id, s.session_token, s.expires_at,
                  u.user_email, u.user_role, u.user_first_name, u.user_last_name
           FROM sessions s JOIN users u ON s.user_id = u.user_id
           WHERE s.session_token = ?""",
        (token,),
    ).fetchone()
    conn.close()
    if session is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(dict(session))


@app.delete("/sessions/by-token")
def delete_session_by_token():
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"error": "token parameter required"}), 400

    conn = get_db_connection()
    conn.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Session deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000, debug=True)
