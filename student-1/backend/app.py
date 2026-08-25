from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
import requests
import base64

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
CORS(app, supports_credentials=True)

SHARED_API_URL = os.environ["SHARED_API_URL"]
DB_SERVICE_URL = os.environ["DB_SERVICE_URL"]

ALLOWED_FILE_TYPES = {
    "application/pdf",
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

    resp = requests.post(f"{DB_SERVICE_URL}/profiles", json=data)
    return jsonify(resp.json()), resp.status_code


@app.get("/api/profiles/me")
def get_my_profile():
    user, err = require_session()
    if err:
        return err

    resp = requests.get(f"{DB_SERVICE_URL}/profiles/by-user/{user['user_id']}")
    # Not having a profile yet is a normal state (not an error), so always respond 200
    profile = resp.json() if resp.status_code == 200 else None
    return jsonify({
        "profile": profile,
        "role": user["role"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
    }), 200


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
    return jsonify(resp.json()), resp.status_code


@app.put("/api/user")
def update_user_identity():
    user, err = require_session()
    if err:
        return err

    data = request.get_json() or {}
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    if not first_name or not last_name:
        return jsonify({"error": "First name and last name are required"}), 400

    cookie = request.headers.get("Cookie", "")
    resp = requests.put(f"{SHARED_API_URL}/api/auth/user", json={
        "first_name": first_name,
        "last_name": last_name,
    }, headers={"Cookie": cookie})
    return jsonify(resp.json()), resp.status_code



@app.post("/api/auth/logout")
def logout():
    cookie = request.headers.get("Cookie", "")
    resp = requests.post(f"{SHARED_API_URL}/api/auth/logout", headers={"Cookie": cookie})
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


def _parse_resume_payload():
    """Parse a resume upload request (multipart file or JSON body) into a DB payload.
    Returns (payload, None) on success, or (None, (response_json, status_code)) on failure."""
    if "file" in request.files:
        file = request.files["file"]
        if not file.filename:
            return None, ({"error": "No file selected"}, 400)

        file_type = file.content_type or ""
        if file_type not in ALLOWED_FILE_TYPES:
            return None, ({"error": "Only PDF files are allowed"}, 400)

        file_bytes = file.read()
        if len(file_bytes) > 5 * 1024 * 1024:
            return None, ({"error": "File exceeds 5MB limit"}, 400)

        return {
            "file_name": file.filename,
            "file_type": file_type,
            "file_data": base64.b64encode(file_bytes).decode("utf-8"),
        }, None

    data = request.get_json()
    if not data:
        return None, ({"error": "No file provided"}, 400)
    return data, None


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

    payload, err = _parse_resume_payload()
    if err:
        return jsonify(err[0]), err[1]

    resp = requests.post(f"{DB_SERVICE_URL}/profiles/{profile_id}/resumes", json=payload)
    return jsonify(resp.json()), resp.status_code


@app.post("/api/resumes")
def upload_unlinked_resume():
    """Upload a resume that is not the caller's default profile resume (e.g. a
    one-off resume attached to a specific job application). Not linked to a
    profile; the caller (student-3) is responsible for tracking ownership via
    its own applications.user_id FK.
    """
    user, err = require_session()
    if err:
        return err
    if user["role"] == "staff":
        return jsonify({"error": "Forbidden"}), 403

    payload, err = _parse_resume_payload()
    if err:
        return jsonify(err[0]), err[1]

    resp = requests.post(f"{DB_SERVICE_URL}/resumes", json=payload)
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


@app.get("/api/resumes/<int:resume_id>")
def get_resume_meta(resume_id):
    user, err = require_session()
    if err:
        return err

    meta_resp = requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    if meta_resp.status_code != 200:
        return jsonify(meta_resp.json()), meta_resp.status_code
    meta = meta_resp.json()

    # Resumes with no profile_id are application-only uploads (see student-3's
    # ApplicationService); ownership for those is enforced by the caller via
    # applications.user_id, not here.
    if user["role"] != "staff" and meta["profile_id"] is not None:
        profile_resp = requests.get(f"{DB_SERVICE_URL}/profiles/{meta['profile_id']}")
        if profile_resp.status_code != 200 or profile_resp.json()["user_id"] != user["user_id"]:
            return jsonify({"error": "Forbidden"}), 403

    return jsonify(meta), 200


@app.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id):
    user, err = require_session()
    if err:
        return err

    meta_resp = requests.get(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    if meta_resp.status_code != 200:
        return jsonify(meta_resp.json()), meta_resp.status_code
    meta = meta_resp.json()

    if user["role"] != "staff" and meta["profile_id"] is not None:
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
    # Application-only resumes (profile_id is None) have no student-1 profile to
    # check ownership against; consistent with get_resume_meta/download_resume,
    # any authenticated non-staff caller is trusted for those.
    if meta["profile_id"] is not None:
        profile_resp = requests.get(f"{DB_SERVICE_URL}/profiles/{meta['profile_id']}")
        if profile_resp.status_code != 200 or profile_resp.json()["user_id"] != user["user_id"]:
            return jsonify({"error": "Forbidden"}), 403

    resp = requests.delete(f"{DB_SERVICE_URL}/resumes/{resume_id}")
    return jsonify(resp.json()), resp.status_code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
