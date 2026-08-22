from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
import requests
import base64

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
CORS(app, supports_credentials=True)

SHARED_API_URL = os.environ["SHARED_API_URL"]
DB_SERVICE_URL = os.environ["DB_SERVICE_URL"]

ALLOWED_FILE_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def require_session():
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    resp = requests.get(f"{SHARED_API_URL}/api/auth/session", headers={"Cookie": cookie})
    if resp.status_code != 200:
        return None, (jsonify({"error": "Invalid or expired session"}), 401)
    return resp.json()["user"], None


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/profiles")
def create_profile():
    user, err = require_session()
    if err:
        return err

    data = request.get_json() or {}
    data["user_id"] = user["user_id"]
    if not data.get("first_name"):
        data["first_name"] = user.get("first_name", "")
    if not data.get("last_name"):
        data["last_name"] = user.get("last_name", "")

    resp = requests.post(f"{DB_SERVICE_URL}/profiles", json=data)
    return jsonify(resp.json()), resp.status_code


@app.get("/api/profiles/me")
def get_my_profile():
    user, err = require_session()
    if err:
        return err

    resp = requests.get(f"{DB_SERVICE_URL}/profiles/by-user/{user['user_id']}")
    # Attach role so the frontend can toggle role-specific UI (e.g. resume section) in one call
    body = resp.json()
    body["role"] = user["role"]
    return jsonify(body), resp.status_code


@app.get("/api/profiles/<int:profile_id>")
def get_profile(profile_id):
    user, err = require_session()
    if err:
        return err

    resp = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    if resp.status_code != 200:
        return jsonify(resp.json()), resp.status_code

    profile = resp.json()
    if profile["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(profile)


@app.put("/api/profiles/<int:profile_id>")
def update_profile(profile_id):
    user, err = require_session()
    if err:
        return err

    check = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    if check.status_code != 200:
        return jsonify(check.json()), check.status_code
    if check.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    resp = requests.put(f"{DB_SERVICE_URL}/profiles/{profile_id}", json=data)

    # Sync name back to the shared users table so login/session reflect the change
    if resp.status_code == 200 and ("first_name" in data or "last_name" in data):
        cookie = request.headers.get("Cookie", "")
        requests.put(f"{SHARED_API_URL}/api/auth/user",
                     json={"first_name": data.get("first_name", ""), "last_name": data.get("last_name", "")},
                     headers={"Cookie": cookie})

    return jsonify(resp.json()), resp.status_code


@app.delete("/api/profiles/<int:profile_id>")
def delete_profile(profile_id):
    user, err = require_session()
    if err:
        return err

    check = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    if check.status_code != 200:
        return jsonify(check.json()), check.status_code
    if check.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    resp = requests.delete(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    return jsonify(resp.json()), resp.status_code


@app.post("/api/profiles/<int:profile_id>/resumes")
def upload_resume(profile_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] == "staff":
        return jsonify({"error": "Forbidden"}), 403

    check = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    if check.status_code != 200:
        return jsonify(check.json()), check.status_code
    if check.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    if "file" in request.files:
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400

        file_type = file.content_type or ""
        if file_type not in ALLOWED_FILE_TYPES:
            return jsonify({"error": "Only PDF, DOC, and DOCX files are allowed"}), 400

        file_bytes = file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            return jsonify({"error": "File exceeds 10MB limit"}), 400

        payload = {
            "file_name": file.filename,
            "file_type": file_type,
            "file_data": base64.b64encode(file_bytes).decode("utf-8"),
        }
    else:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No file provided"}), 400
        payload = data

    resp = requests.post(f"{DB_SERVICE_URL}/profiles/{profile_id}/resumes", json=payload)
    return jsonify(resp.json()), resp.status_code


@app.get("/api/profiles/<int:profile_id>/resumes")
def get_resumes(profile_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] == "staff":
        return jsonify({"error": "Forbidden"}), 403

    check = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}")
    if check.status_code != 200:
        return jsonify(check.json()), check.status_code
    if check.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    resp = requests.get(f"{DB_SERVICE_URL}/profiles/{profile_id}/resumes")
    return jsonify(resp.json()), resp.status_code


@app.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] == "staff":
        return jsonify({"error": "Forbidden"}), 403

    meta_resp = requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    if meta_resp.status_code != 200:
        return jsonify(meta_resp.json()), meta_resp.status_code

    meta = meta_resp.json()
    profile_resp = requests.get(f"{DB_SERVICE_URL}/profiles/{meta['profile_id']}")
    if profile_resp.status_code != 200 or profile_resp.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    file_resp = requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}/file")
    if file_resp.status_code != 200:
        return jsonify({"error": "File not found"}), 404

    return Response(
        file_resp.content,
        mimetype=file_resp.headers.get("Content-Type", "application/octet-stream"),
        headers={"Content-Disposition": file_resp.headers.get("Content-Disposition", "")}
    )


@app.delete("/api/resumes/<int:resume_id>")
def delete_resume(resume_id):
    user, err = require_session()
    if err:
        return err
    if user["role"] == "staff":
        return jsonify({"error": "Forbidden"}), 403

    meta_resp = requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    if meta_resp.status_code != 200:
        return jsonify(meta_resp.json()), meta_resp.status_code

    meta = meta_resp.json()
    profile_resp = requests.get(f"{DB_SERVICE_URL}/profiles/{meta['profile_id']}")
    if profile_resp.status_code != 200 or profile_resp.json()["user_id"] != user["user_id"]:
        return jsonify({"error": "Forbidden"}), 403

    resp = requests.delete(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
