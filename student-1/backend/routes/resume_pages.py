"""Resume fragment routes (single resume per profile)."""

import base64
import os

from flask import Blueprint, Response, request

from services import database_api, shared_api
from views.html_formatters import render_message, render_resume_panel

resume_bp = Blueprint("resume_pages", __name__)

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16005")

ALLOWED_FILE_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def _get_my_profile(user_id: int) -> dict | None:
    resp = database_api.get_profile_by_user(user_id)
    return resp.json() if resp.status_code == 200 else None


def _panel(profile_id, *, message="", kind="error"):
    resumes = []
    if profile_id is not None:
        resp = database_api.list_resumes(profile_id)
        if resp.status_code == 200:
            resumes = resp.json()
    return render_resume_panel(profile_id, resumes, backend_url=BACKEND_PUBLIC_URL, message=message, kind=kind), 200


@resume_bp.get("/resume")
def get_resume_panel():
    user = shared_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff cannot manage resumes.", "error"), 200

    profile = _get_my_profile(user["user_id"])
    return _panel(profile["profile_id"] if profile else None)


@resume_bp.post("/resume")
def upload_resume():
    user = shared_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff cannot manage resumes.", "error"), 200

    profile = _get_my_profile(user["user_id"])
    if not profile:
        return _panel(None, message="Create your profile before uploading a resume.")
    profile_id = profile["profile_id"]

    file = request.files.get("file")
    if not file or not file.filename:
        return _panel(profile_id, message="No file selected.")

    file_type = file.content_type or ""
    if file_type not in ALLOWED_FILE_TYPES:
        return _panel(profile_id, message="Only PDF files are allowed.")

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return _panel(profile_id, message="File exceeds 5MB limit.")

    payload = {
        "file_name": file.filename,
        "file_type": file_type,
        "file_data": base64.b64encode(file_bytes).decode("utf-8"),
    }
    resp = database_api.upload_resume(profile_id, payload)
    if resp.status_code != 201:
        error = (resp.json() or {}).get("error", "Upload failed.")
        return _panel(profile_id, message=error)

    return _panel(profile_id, message="Resume uploaded.", kind="success")


@resume_bp.delete("/resume/<int:resume_id>")
def delete_resume(resume_id):
    user = shared_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff cannot manage resumes.", "error"), 200

    meta_resp = database_api.get_resume(resume_id)
    if meta_resp.status_code != 200:
        return render_message("Resume not found.", "error"), 200
    meta = meta_resp.json()

    profile = _get_my_profile(user["user_id"])
    if meta.get("profile_id") is None or not profile or meta["profile_id"] != profile["profile_id"]:
        return {"error": "Forbidden"}, 403

    database_api.delete_resume(resume_id)
    return _panel(profile["profile_id"])


@resume_bp.get("/resume/<int:resume_id>/download")
def download_resume(resume_id):
    user = shared_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401

    meta_resp = database_api.get_resume(resume_id)
    if meta_resp.status_code != 200:
        return {"error": "Resume not found"}, 404
    meta = meta_resp.json()

    if user["role"] != "staff":
        profile = _get_my_profile(user["user_id"])
        if meta.get("profile_id") is None or not profile or meta["profile_id"] != profile["profile_id"]:
            return {"error": "Forbidden"}, 403

    file_resp = database_api.get_resume_file(resume_id)
    if file_resp.status_code != 200:
        return {"error": "File not found"}, 404

    return Response(
        file_resp.content,
        mimetype=file_resp.headers.get("Content-Type", "application/octet-stream"),
        headers={"Content-Disposition": file_resp.headers.get("Content-Disposition", "")},
    )
