"""Application routes (HTML fragments and JSON for HTMX).

Implements the CRUD, submit and withdraw actions for candidate applications.
Session validation is delegated to the shared-api service. Resumes live in
student-1's backend service (see ``services.student1_api``); this module just references them by
``resume_id`` on the ``applications`` row.
"""

from __future__ import annotations

import json
import os

import requests
from flask import Blueprint, make_response, request

from services import database_api, postings_api, shared_api, student1_api
from views.html_formatters import (
    ALLOWED_RESUME_EXTS,
    ALLOWED_RESUME_MIME,
    INTERVIEW_ACTION_STATUSES,
    MAX_RESUME_BYTES,
    VALID_STATUSES,
    WITHDRAWABLE_STATUSES,
    render_apply_form,
    render_application_detail,
    render_candidate_profile,
    render_message,
    render_my_applications_table,
    render_pending_interviews_bar,
    render_staff_applications_table,
)

applications_bp = Blueprint("applications", __name__)

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16011")
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16010")

_DB_UNAVAILABLE = (
    "Could not reach the database service. Make sure the student-3-db "
    "container is running."
)


# --------------------------------------------------------------------------- #
# Session helpers                                                             #
# --------------------------------------------------------------------------- #

def _current_user() -> dict | None:
    cookie = request.headers.get("Cookie", "")
    return shared_api.get_session_user(cookie)


def _unauthorized():
    return render_message("Please log in first.", "error"), 401


def _forbidden(msg: str = "Not allowed."):
    return render_message(msg, "error"), 200


def _hx_trigger(response, event: str, value: str):
    response.headers["HX-Trigger"] = json.dumps({event: value})
    return response


def _toast_response(message: str, kind: str = "success"):
    resp = make_response("", 200)
    event = "showErrorToast" if kind == "error" else "showToast"
    return _hx_trigger(resp, event, message)


def _redirect_response(path: str, toast: str | None = None):
    url = f"{FRONTEND_PUBLIC_URL}{path}"
    if toast:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}toast={requests.utils.quote(toast)}"
    resp = make_response("", 200)
    resp.headers["HX-Redirect"] = url
    return resp


# --------------------------------------------------------------------------- #
# Health                                                                      #
# --------------------------------------------------------------------------- #

@applications_bp.get("/")
def index():
    return "<p>student-3 backend (Application Management) running</p>", 200


@applications_bp.get("/health")
def health():
    return {"status": "ok"}, 200


# --------------------------------------------------------------------------- #
# Applicant: list / detail                                                    #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/my-applications")
def my_applications():
    user = _current_user()
    if not user:
        return _unauthorized()
    try:
        resp = database_api.list_applications({"user_id": user["user_id"]})
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    apps = resp.json()
    posting_ids = [a["job_posting_id"] for a in apps]
    postings = postings_api.get_postings_map(posting_ids)
    return render_my_applications_table(
        apps, postings, frontend_url=FRONTEND_PUBLIC_URL
    ), 200


@applications_bp.get("/api/applications/<int:application_id>/detail")
def applicant_application_detail(application_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    application, error = _load_application(application_id)
    if error:
        return error
    if application["user_id"] != user["user_id"]:
        return _forbidden("You can only view your own applications.")
    cookie = request.headers.get("Cookie", "")
    posting = postings_api.get_job_posting(application["job_posting_id"]) or {}
    resume = _load_resume(application.get("resume_id"), cookie, user.get("role", "applicant"))
    return render_application_detail(
        application=application, posting=posting, user=user, resume=resume,
        backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL,
    ), 200


# --------------------------------------------------------------------------- #
# Applicant: apply form                                                       #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/apply/<int:job_posting_id>")
def apply_form(job_posting_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "applicant":
        return _forbidden("Only applicants can submit applications.")

    posting = postings_api.get_job_posting(job_posting_id)
    if not posting:
        return render_message("Job posting not found.", "error"), 200
    if posting.get("JobPosting_Status") != "Published":
        return render_message(
            "This job posting is no longer accepting applications.", "error"
        ), 200

    try:
        resp = database_api.list_applications(
            {"user_id": user["user_id"], "job_posting_id": job_posting_id}
        )
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    cookie = request.headers.get("Cookie", "")
    for existing in resp.json():
        if existing["application_status"] in ("Withdrawn", "Rejected"):
            continue
        if existing["application_status"] == "Draft":
            resume = _load_resume(existing.get("resume_id"), cookie, user.get("role", "applicant"))
            if resume is None:
                resume = student1_api.get_latest_profile_resume(cookie)
            return render_apply_form(
                backend_url=BACKEND_PUBLIC_URL, posting=posting,
                user=_applicant_context(user),
                application=existing, resume=resume,
            ), 200
        return render_message(
            f"You already applied for this job (status: {existing['application_status']}).",
            "info",
        ), 200

    profile_resume = student1_api.get_latest_profile_resume(cookie)
    return render_apply_form(
        backend_url=BACKEND_PUBLIC_URL, posting=posting,
        user=_applicant_context(user),
        resume=profile_resume,
    ), 200


def _applicant_context(user: dict) -> dict:
    return {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
    }


# --------------------------------------------------------------------------- #
# Applicant: save-draft / submit                                              #
# --------------------------------------------------------------------------- #

@applications_bp.post("/api/applications/save")
def save_new_draft():
    return _save_or_submit(action="save", application_id=None)


@applications_bp.post("/api/applications/submit")
def submit_new_application():
    return _save_or_submit(action="submit", application_id=None)


@applications_bp.put("/api/applications/<int:application_id>/save")
def save_existing_draft(application_id: int):
    return _save_or_submit(action="save", application_id=application_id)


@applications_bp.put("/api/applications/<int:application_id>/submit")
def submit_existing_draft(application_id: int):
    return _save_or_submit(action="submit", application_id=application_id)


def _save_or_submit(*, action: str, application_id: int | None):
    """Shared save/submit handler used by both create and update endpoints."""
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "applicant":
        return _forbidden("Only applicants can submit applications.")

    try:
        job_posting_id = int(request.form.get("job_posting_id", "0"))
    except (TypeError, ValueError):
        return render_message("Invalid job posting.", "error"), 200

    declaration = request.form.get("declaration_accepted") in ("1", "true", "on")
    resume_file = request.files.get("resume_file")

    if action == "submit" and not declaration:
        return render_message(
            "You must confirm the declaration before submitting.", "error"
        ), 200

    cookie = request.headers.get("Cookie", "")

    # If a new file was uploaded, push it to the applicant's student-1 profile
    # and reference the newly minted resume_id.
    resume_id_new: int | None = None
    if resume_file and resume_file.filename:
        error = _validate_resume(resume_file)
        if error:
            return render_message(error, "error"), 200
        raw = resume_file.read()
        resume_id_new = student1_api.upload_profile_resume(
            cookie=cookie,
            filename=resume_file.filename,
            mimetype=resume_file.mimetype or "application/pdf",
            raw_bytes=raw,
        )
        if resume_id_new is None:
            return render_message(
                "Could not save your resume to your profile. Please try again.",
                "error",
            ), 200

    # ----- Create-or-update the application row ---------------------------- #
    if application_id is None:
        # For submit, ensure the application ends up with a resume — either the
        # freshly uploaded one, or the applicant's latest profile resume.
        if action == "submit" and resume_id_new is None:
            resume_id_new = _resume_id_from_profile(cookie)
            if resume_id_new is None:
                return render_message(
                    "Please upload your resume before submitting.", "error"
                ), 200
        create_payload = {
            "user_id": user["user_id"],
            "job_posting_id": job_posting_id,
            "resume_id": resume_id_new,
            "declaration_accepted": 1 if declaration else 0,
            "application_status": "Draft",
        }
        try:
            resp = database_api.create_application(create_payload)
            if resp.status_code == 409:
                return _redirect_response(
                    f"/apply/{job_posting_id}",
                    toast="You already have an application for this posting.",
                )
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
            resp.raise_for_status()
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
        application_id = resp.json()["application_id"]
    else:
        existing, error = _load_application(application_id)
        if error:
            return error
        if existing["user_id"] != user["user_id"]:
            return _forbidden("You can only edit your own applications.")
        if existing["application_status"] != "Draft":
            return render_message(
                "Only Draft applications can be edited.", "error"
            ), 200
        if action == "submit" and resume_id_new is None and not existing.get("resume_id"):
            resume_id_new = _resume_id_from_profile(cookie)
            if resume_id_new is None:
                return render_message(
                    "Please upload your resume before submitting.", "error"
                ), 200
        update_payload = {
            "declaration_accepted": 1 if declaration else 0,
        }
        if resume_id_new is not None:
            update_payload["resume_id"] = resume_id_new
        try:
            resp = database_api.update_application(application_id, update_payload)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200

    if action == "submit":
        try:
            resp = database_api.submit_application(application_id)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Cannot submit."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
        return _redirect_response(
            f"/applications/{application_id}",
            toast="Application submitted successfully.",
        )

    return _redirect_response(
        f"/apply/{job_posting_id}",
        toast="Draft saved.",
    )


def _resume_id_from_profile(cookie: str) -> int | None:
    latest = student1_api.get_latest_profile_resume(cookie)
    if not latest:
        return None
    rid = latest.get("resume_id")
    return int(rid) if rid else None


def _validate_resume(file_storage) -> str | None:
    filename = (file_storage.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
        return "Resume must be a PDF or DOCX file."
    mimetype = (file_storage.mimetype or "").lower()
    if mimetype and mimetype not in ALLOWED_RESUME_MIME:
        if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
            return "Resume must be a PDF or DOCX file."
    try:
        file_storage.stream.seek(0, 2)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
    except Exception:
        size = 0
    if size > MAX_RESUME_BYTES:
        return "Resume must be 5 MB or smaller."
    return None


# --------------------------------------------------------------------------- #
# Applicant: withdraw / delete                                                #
# --------------------------------------------------------------------------- #

@applications_bp.put("/api/applications/<int:application_id>/withdraw")
def withdraw(application_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    application, error = _load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return _forbidden("You can only withdraw your own applications.")
    if application["application_status"] not in WITHDRAWABLE_STATUSES:
        return render_message(
            f"Cannot withdraw an application in status "
            f"'{application['application_status']}'.", "error",
        ), 200
    try:
        resp = database_api.withdraw_application(application_id)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot withdraw."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Your application has been successfully withdrawn.",
        "applicationWithdrawn": application_id,
    })
    return resp_out


@applications_bp.delete("/api/applications/<int:application_id>")
def delete_draft(application_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    application, error = _load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return _forbidden("You can only delete your own applications.")
    if application["application_status"] != "Draft":
        return render_message(
            "Only Draft applications can be deleted. Withdraw instead.", "error"
        ), 200
    try:
        resp = database_api.delete_application(application_id)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot delete."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    if request.headers.get("HX-Current-URL", "").rstrip("/").endswith(f"/apply/{application['job_posting_id']}"):
        return _redirect_response("/", toast="Draft application deleted.")

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Draft application deleted.",
        "applicationDeleted": application_id,
    })
    return resp_out


# --------------------------------------------------------------------------- #
# Staff: All Applications list & candidate profile                            #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/all-applications")
def all_applications():
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "staff":
        return _forbidden("Staff view only.")

    params = {}
    for key in ("status", "job_posting_id"):
        v = request.args.get(key, "").strip()
        if v:
            params[key] = v

    try:
        resp = database_api.list_applications(params)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    apps: list[dict] = resp.json()

    _staff_hidden = {"Draft", "Withdrawn"}
    apps = [a for a in apps if a.get("application_status") not in _staff_hidden]

    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    posting_ids = [a["job_posting_id"] for a in apps]
    user_ids = [a["user_id"] for a in apps]
    postings = postings_api.get_postings_map(posting_ids)
    users = shared_api.get_users_map(user_ids)

    def matches(a: dict) -> bool:
        posting = postings.get(a["job_posting_id"]) or {}
        candidate = users.get(a["user_id"]) or {}
        title = (posting.get("Job_Title") or "").lower()
        name = (
            f"{candidate.get('user_first_name', '')} "
            f"{candidate.get('user_last_name', '')}"
        ).lower()

        if q and not any(q in field for field in (name, title)):
            return False
        return True

    apps = [a for a in apps if matches(a)]

    if sort:
        reverse = order == "desc"
        key_map = {
            "id": lambda a: a["application_id"],
            "title": lambda a: (postings.get(a["job_posting_id"]) or {}).get("Job_Title", ""),
            "candidate": lambda a: (
                (users.get(a["user_id"]) or {}).get("user_last_name", "")
            ),
            "status": lambda a: a.get("application_status", ""),
        }
        if sort in key_map:
            apps = sorted(apps, key=key_map[sort], reverse=reverse)

    table = render_staff_applications_table(
        apps, postings, users, frontend_url=FRONTEND_PUBLIC_URL,
    )
    return table, 200


@applications_bp.get("/api/pending-summary")
def pending_summary():
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "staff":
        return _forbidden("Staff view only.")
    try:
        resp = database_api.list_applications({})
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    apps = [a for a in resp.json() if a.get("application_status") != "Withdrawn"]
    return render_pending_interviews_bar(apps), 200


@applications_bp.get("/api/staff/applications/<int:application_id>/profile")
def candidate_profile(application_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "staff":
        return _forbidden("Staff view only.")

    application, error = _load_application(application_id)
    if error:
        return error
    if application.get("application_status") == "Withdrawn":
        return render_message("Application not found.", "error"), 200
    posting = postings_api.get_job_posting(application["job_posting_id"]) or {}
    candidate = shared_api.get_user(application["user_id"]) or {}
    cookie = request.headers.get("Cookie", "")
    resume = _load_resume(application.get("resume_id"), cookie, user.get("role", "staff"))

    return render_candidate_profile(
        application=application, posting=posting, user=candidate,
        resume=resume, screening=None, backend_url=BACKEND_PUBLIC_URL,
    ), 200


# --------------------------------------------------------------------------- #
# Staff: status change                                                        #
# --------------------------------------------------------------------------- #

@applications_bp.put("/api/applications/<int:application_id>/status")
def update_status(application_id: int):
    user = _current_user()
    if not user:
        return _unauthorized()
    if user.get("role") != "staff":
        return _forbidden("Only staff can change application status.")

    new_status = ""
    if request.is_json:
        new_status = str((request.get_json(silent=True) or {}).get("application_status", "")).strip()
    if not new_status:
        new_status = request.args.get("application_status", "").strip()
    if not new_status:
        new_status = request.form.get("application_status", "").strip()

    if new_status not in VALID_STATUSES:
        return _toast_response(f"Unknown status: {new_status}", kind="error")

    try:
        resp = database_api.update_application(
            application_id, {"application_status": new_status}
        )
        if resp.status_code >= 400:
            return _toast_response(
                resp.json().get("error", "Cannot update status."), kind="error"
            )
    except requests.RequestException:
        return _toast_response(_DB_UNAVAILABLE, kind="error")

    return _toast_response(f"Status updated to {new_status}.")


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _load_application(application_id: int):
    try:
        resp = database_api.get_application(application_id)
        if resp.status_code == 404:
            return None, (render_message("Application not found.", "error"), 200)
        resp.raise_for_status()
    except requests.RequestException:
        return None, (render_message(_DB_UNAVAILABLE, "error"), 200)
    return resp.json(), None


def _load_resume(resume_id: int | None, cookie: str, role: str) -> dict | None:
    """Fetch resume metadata from student-1's backend service."""
    if not resume_id:
        return None
    return student1_api.get_resume_metadata(int(resume_id), cookie, role)
