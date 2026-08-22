from flask import Flask, jsonify, request
from flask_cors import CORS
import hashlib
import secrets
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, supports_credentials=True)

DB_SERVICE_URL = "http://find-shared-db:6000"


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.get("/")
def index():
    return jsonify({"service": "shared-api", "status": "running"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/auth/register")
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["email", "password", "role"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    email = data["email"].strip().lower()
    password = data["password"]
    role = data["role"]

    if role not in ("applicant", "staff"):
        return jsonify({"error": "Role must be 'applicant' or 'staff'"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    password_hash = hash_password(password)

    resp = requests.post(f"{DB_SERVICE_URL}/users", json={
        "user_email": email,
        "user_password_hash": password_hash,
        "user_role": role,
        "user_first_name": data.get("first_name", ""),
        "user_last_name": data.get("last_name", ""),
    })

    if resp.status_code == 409:
        return jsonify({"error": "Email already registered"}), 409
    if resp.status_code != 201:
        return jsonify({"error": "Registration failed"}), 500

    return jsonify({"message": "Registration successful"}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    resp = requests.get(f"{DB_SERVICE_URL}/users/by-email", params={"email": email})
    if resp.status_code == 404:
        return jsonify({"error": "Invalid email or password"}), 401

    user = resp.json()
    password_hash = hash_password(password)

    if user["user_password_hash"] != password_hash:
        return jsonify({"error": "Invalid email or password"}), 401

    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    requests.post(f"{DB_SERVICE_URL}/sessions", json={
        "user_id": user["user_id"],
        "session_token": token,
        "expires_at": expires_at,
    })

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["user_email"],
            "role": user["user_role"],
            "first_name": user["user_first_name"],
            "last_name": user["user_last_name"],
        },
    }), 200


@app.get("/api/auth/session")
def get_session():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "No token provided"}), 401

    resp = requests.get(f"{DB_SERVICE_URL}/sessions/by-token", params={"token": token})
    if resp.status_code == 404:
        return jsonify({"error": "Invalid or expired session"}), 401

    session = resp.json()
    if datetime.fromisoformat(session["expires_at"]) < datetime.utcnow():
        requests.delete(f"{DB_SERVICE_URL}/sessions/by-token", params={"token": token})
        return jsonify({"error": "Session expired"}), 401

    return jsonify({
        "user": {
            "user_id": session["user_id"],
            "email": session["user_email"],
            "role": session["user_role"],
            "first_name": session["user_first_name"],
            "last_name": session["user_last_name"],
        }
    }), 200


@app.post("/api/auth/logout")
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        requests.delete(f"{DB_SERVICE_URL}/sessions/by-token", params={"token": token})
    return jsonify({"message": "Logged out"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
