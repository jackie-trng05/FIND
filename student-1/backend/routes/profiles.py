"""Normal-mode routes for the Student 1 (User Profile) backend.

Renders the HTML fragments the HTMX frontend swaps in: user identity details,
the profile panel (create/view/edit/delete) and the resume panel (single
resume per profile).
"""

import base64
import json

from flask import Blueprint, Response, make_response, request

from services import database_api, integration_api
from services.config import ALLOWED_FILE_TYPES, BACKEND_PUBLIC_URL, MAX_FILE_SIZE
from views.html_formatters import (
    render_message,
    render_profile_panel,
    render_resume_panel,
    render_user_details_panel,
)

profiles_bp = Blueprint("profiles", __name__)

EDITABLE_FIELDS = ("phone", "location", "professional_title", "summary", "interests")


def _cookie() -> str:
    return request.headers.get("Cookie", "")


def _payload_from_form() -> dict:
    return {field: request.form.get(field, "").strip() for field in EDITABLE_FIELDS}


def _get_my_profile(user_id: int) -> dict | None:
    resp = database_api.get_profile_by_user(user_id)
    return resp.json() if resp.status_code == 200 else None


def _panel_response(profile, role, *, message="", kind="error", toast=None, profile_changed=False):
    html = render_profile_panel(profile, backend_url=BACKEND_PUBLIC_URL, role=role, message=message, kind=kind)
    response = make_response(html, 200)
    triggers = {}
    if toast:
        triggers["showToast"] = toast
    if profile_changed:
        triggers["profileChanged"] = True
    if triggers:
        response.headers["HX-Trigger"] = json.dumps(triggers)
    return response


def _resume_panel(profile_id, *, message="", kind="error"):
    resumes = []
    if profile_id is not None:
        resp = database_api.list_resumes(profile_id)
        if resp.status_code == 200:
            resumes = resp.json()
    return render_resume_panel(profile_id, resumes, backend_url=BACKEND_PUBLIC_URL, message=message, kind=kind), 200


# --------------------------------------------------------------------------- #
# User identity (first/last name, on the shared users table)                   #
# --------------------------------------------------------------------------- #

@profiles_bp.get("/user")
def get_user_details():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    return render_user_details_panel(user, backend_url=BACKEND_PUBLIC_URL), 200


@profiles_bp.put("/user")
def update_user_details():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    if not first_name or not last_name:
        merged = dict(user, first_name=first_name, last_name=last_name)
        return render_user_details_panel(
            merged, backend_url=BACKEND_PUBLIC_URL, error="First name and last name are required."
        ), 200

    resp = integration_api.update_user_identity(_cookie(), first_name, last_name)
    if resp.status_code != 200:
        return render_user_details_panel(
            dict(user, first_name=first_name, last_name=last_name),
            backend_url=BACKEND_PUBLIC_URL, error="Failed to update details.",
        ), 200

    html = render_user_details_panel(dict(user, first_name=first_name, last_name=last_name), backend_url=BACKEND_PUBLIC_URL)
    response = make_response(html, 200)
    # userUpdated lets the navbar (outside this fragment's swap target) refresh
    # without a page reload.
    response.headers["HX-Trigger"] = json.dumps({
        "showToast": "Details updated.",
        "userUpdated": {"first_name": first_name, "last_name": last_name},
    })
    return response


# --------------------------------------------------------------------------- #
# Profile (create/view/edit/delete)                                            #
# --------------------------------------------------------------------------- #

@profiles_bp.get("/profile")
def get_profile_panel():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    profile = _get_my_profile(user["user_id"])
    return _panel_response(profile, user["role"])


@profiles_bp.post("/profile")
def create_profile():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401

    payload = _payload_from_form()
    if not payload["phone"]:
        return _panel_response(None, user["role"], message="Phone is required.")

    payload["user_id"] = user["user_id"]
    resp = database_api.create_profile(payload)
    if resp.status_code not in (200, 201):
        error = (resp.json() or {}).get("error", "Failed to create profile.")
        return _panel_response(None, user["role"], message=error)

    profile = resp.json()
    return _panel_response(profile, user["role"], message="Profile created.", kind="success", profile_changed=True)


@profiles_bp.put("/profile/<int:profile_id>")
def update_profile(profile_id):
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401

    check = database_api.get_profile(profile_id)
    if check.status_code != 200:
        return render_message("Profile not found.", "error"), 200
    if check.json()["user_id"] != user["user_id"]:
        return {"error": "Forbidden"}, 403

    payload = _payload_from_form()
    if not payload["phone"]:
        return _panel_response(check.json(), user["role"], message="Phone is required.")

    resp = database_api.update_profile(profile_id, payload)
    if resp.status_code != 200:
        error = (resp.json() or {}).get("error", "Failed to update profile.")
        return _panel_response(check.json(), user["role"], message=error)

    return _panel_response(resp.json(), user["role"], message="Profile updated.", kind="success")


@profiles_bp.delete("/profile/<int:profile_id>")
def delete_profile(profile_id):
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401

    check = database_api.get_profile(profile_id)
    if check.status_code != 200:
        return render_message("Profile not found.", "error"), 200
    if check.json()["user_id"] != user["user_id"]:
        return {"error": "Forbidden"}, 403

    database_api.delete_profile(profile_id)
    return _panel_response(None, user["role"], toast="Profile deleted.", profile_changed=True)


# --------------------------------------------------------------------------- #
# Resume (single resume per profile)                                           #
# --------------------------------------------------------------------------- #

@profiles_bp.get("/resume")
def get_resume_panel():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff cannot manage resumes.", "error"), 200

    profile = _get_my_profile(user["user_id"])
    return _resume_panel(profile["profile_id"] if profile else None)


@profiles_bp.post("/resume")
def upload_resume():
    user = integration_api.get_session_user()
    if not user:
        return {"error": "Not authenticated"}, 401
    if user["role"] == "staff":
        return render_message("Staff cannot manage resumes.", "error"), 200

    profile = _get_my_profile(user["user_id"])
    if not profile:
        return _resume_panel(None, message="Create your profile before uploading a resume.")
    profile_id = profile["profile_id"]

    file = request.files.get("file")
    if not file or not file.filename:
        return _resume_panel(profile_id, message="No file selected.")

    file_type = file.content_type or ""
    if file_type not in ALLOWED_FILE_TYPES:
        return _resume_panel(profile_id, message="Only PDF files are allowed.")

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return _resume_panel(profile_id, message="File exceeds 5MB limit.")

    payload = {
        "file_name": file.filename,
        "file_type": file_type,
        "file_data": base64.b64encode(file_bytes).decode("utf-8"),
    }
    resp = database_api.upload_resume(profile_id, payload)
    if resp.status_code != 201:
        error = (resp.json() or {}).get("error", "Upload failed.")
        return _resume_panel(profile_id, message=error)

    return _resume_panel(profile_id, message="Resume uploaded.", kind="success")


@profiles_bp.delete("/resume/<int:resume_id>")
def delete_resume(resume_id):
    user = integration_api.get_session_user()
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
    return _resume_panel(profile["profile_id"])


@profiles_bp.get("/resume/<int:resume_id>/download")
def download_resume(resume_id):
    user = integration_api.get_session_user()
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
