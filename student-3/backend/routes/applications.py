"""Normal-mode routes for the Student 3 (Application) backend.

Returns the HTML fragments and JSON context envelopes that HTMX swaps into the
frontend: the applicant's own applications (list/detail/apply/save/submit/
withdraw/delete), the staff application list and candidate profile panel, and
the resume download stream.
"""

import json

import requests
from flask import Blueprint, Response, jsonify, make_response, request, stream_with_context

from services import database_api, integration_api
from services.config import (
    ALLOWED_RESUME_EXTS,
    ALLOWED_RESUME_MIME,
    DB_UNAVAILABLE,
    FRONTEND_PUBLIC_URL,
    INTERVIEWS_URL,
    INTERVIEW_ACTION_STATUSES,
    MAX_RESUME_BYTES,
    WITHDRAWABLE_STATUSES,
)
from views.html_formatters import (
    render_application_detail,
    render_apply_form,
    render_candidate_profile,
    render_message,
    render_my_applications_table,
    render_pending_interviews_bar,
    render_staff_applications_table,
)

applications_bp = Blueprint("applications", __name__)


# --------------------------------------------------------------------------- #
# Response helpers                                                            #
# --------------------------------------------------------------------------- #

def unauthorized():
    return render_message("Please log in first.", "error"), 401


def forbidden(msg="Not allowed."):
    return render_message(msg, "error"), 200


def toast_response(message, kind="success"):
    resp = make_response("", 200)
    event = "showErrorToast" if kind == "error" else "showToast"
    resp.headers["HX-Trigger"] = json.dumps({event: message})
    return resp


def redirect_response(path, toast=None):
    url = f"{FRONTEND_PUBLIC_URL}{path}"
    if toast:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}toast={requests.utils.quote(toast)}"
    resp = make_response("", 200)
    resp.headers["HX-Redirect"] = url
    return resp


def context_error(message, kind="error", status=200):
    return jsonify({"ok": False, "kind": kind, "message": message}), status


def context_ok(data):
    return jsonify({"ok": True, "data": data}), 200


# --------------------------------------------------------------------------- #
# Validation / loading helpers                                               #
# --------------------------------------------------------------------------- #

def validate_resume(file_storage):
    filename = (file_storage.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
        return "Resume must be a PDF file."
    mimetype = (file_storage.mimetype or "").lower()
    if mimetype and mimetype not in ALLOWED_RESUME_MIME:
        if not any(filename.endswith(ext) for ext in ALLOWED_RESUME_EXTS):
            return "Resume must be a PDF file."
    try:
        file_storage.stream.seek(0, 2)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
    except Exception:
        size = 0
    if size > MAX_RESUME_BYTES:
        return "Resume must be 5 MB or smaller."
    return None


def load_application(application_id):
    try:
        resp = database_api.get_application(application_id)
        if resp.status_code == 404:
            return None, (render_message("Application not found.", "error"), 200)
        resp.raise_for_status()
    except requests.RequestException:
        return None, (render_message(DB_UNAVAILABLE, "error"), 200)
    return resp.json(), None


def load_resume(resume_id, role, current_user_id=None):
    if not resume_id:
        return None
    return integration_api.get_resume_metadata(int(resume_id), role, current_user_id)


# --------------------------------------------------------------------------- #
# Applicant: list / detail / apply form                                       #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/context/apply/<int:job_posting_id>")
def apply_form_context(job_posting_id):
    user = integration_api.get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "applicant":
        return context_error("Only applicants can submit applications.")

    posting = integration_api.get_job_posting(job_posting_id)
    if not posting:
        return context_error("Job posting not found.")
    if posting.get("JobPosting_Status") != "Published":
        return context_error("This job posting is no longer accepting applications.")

    try:
        resp = database_api.list_applications_response(
            {"user_id": user["user_id"], "job_posting_id": job_posting_id}
        )
        resp.raise_for_status()
    except requests.RequestException:
        return context_error(DB_UNAVAILABLE)

    applicant_ctx = {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
    }

    application = None
    resume = None
    for existing in resp.json():
        if existing["application_status"] in ("Withdrawn", "Rejected"):
            continue
        if existing["application_status"] == "Draft":
            application = existing
            resume = load_resume(existing.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
            if resume is None:
                resume = integration_api.get_latest_profile_resume(user.get("user_id"))
            break
        return context_error(
            f"You already applied for this job (status: {existing['application_status']}).",
            kind="info",
        )

    if resume is None:
        resume = integration_api.get_latest_profile_resume(user.get("user_id"))

    return context_ok({
        "posting": posting,
        "user": applicant_ctx,
        "application": application,
        "resume": resume,
    })


@applications_bp.get("/api/context/applications/<int:application_id>/detail")
def applicant_application_detail_context(application_id):
    user = integration_api.get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application["user_id"] != user["user_id"]:
        return context_error("You can only view your own applications.")

    posting = integration_api.get_job_posting(application["job_posting_id"]) or {}
    resume = load_resume(application.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
    return context_ok({
        "application": application,
        "posting": posting,
        "user": {
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "email": user.get("email", ""),
        },
        "resume": resume,
        "withdrawable_statuses": list(WITHDRAWABLE_STATUSES),
        "interview_action_statuses": list(INTERVIEW_ACTION_STATUSES),
        "interviews_url": INTERVIEWS_URL,
    })


@applications_bp.get("/api/my-applications")
def my_applications():
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    try:
        resp = database_api.list_applications_response({"user_id": user["user_id"]})
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200
    apps = resp.json()
    postings = integration_api.get_postings_map([a["job_posting_id"] for a in apps])

    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    if status:
        apps = [a for a in apps if a.get("application_status") == status]
    if q:
        apps = [
            a for a in apps
            if q in (postings.get(a["job_posting_id"]) or {}).get("Job_Title", "").lower()
        ]
    if sort:
        reverse = order == "desc"
        key_map = {
            "id": lambda a: a["application_id"],
            "title": lambda a: (postings.get(a["job_posting_id"]) or {}).get("Job_Title", ""),
            "status": lambda a: a.get("application_status", ""),
        }
        if sort in key_map:
            apps = sorted(apps, key=key_map[sort], reverse=reverse)

    return render_my_applications_table(apps, postings), 200


@applications_bp.get("/api/applications/<int:application_id>/detail")
def applicant_application_detail(application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if application["user_id"] != user["user_id"]:
        return forbidden("You can only view your own applications.")
    posting = integration_api.get_job_posting(application["job_posting_id"]) or {}
    resume = load_resume(application.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
    return render_application_detail(application, posting, user, resume), 200


@applications_bp.get("/api/apply/<int:job_posting_id>")
def apply_form(job_posting_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "applicant":
        return forbidden("Only applicants can submit applications.")

    posting = integration_api.get_job_posting(job_posting_id)
    if not posting:
        return render_message("Job posting not found.", "error"), 200
    if posting.get("JobPosting_Status") != "Published":
        return render_message("This job posting is no longer accepting applications.", "error"), 200

    try:
        resp = database_api.list_applications_response(
            {"user_id": user["user_id"], "job_posting_id": job_posting_id}
        )
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200

    applicant_ctx = {
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "email": user.get("email", ""),
    }
    for existing in resp.json():
        if existing["application_status"] in ("Withdrawn", "Rejected"):
            continue
        if existing["application_status"] == "Draft":
            resume = load_resume(existing.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
            if resume is None:
                resume = integration_api.get_latest_profile_resume(user.get("user_id"))
            return render_apply_form(posting, applicant_ctx, existing, resume), 200
        return render_message(
            f"You already applied for this job (status: {existing['application_status']}).",
            "info",
        ), 200

    profile_resume = integration_api.get_latest_profile_resume(user.get("user_id"))
    return render_apply_form(posting, applicant_ctx, resume=profile_resume), 200


# --------------------------------------------------------------------------- #
# Applicant: save-draft / submit                                              #
# --------------------------------------------------------------------------- #

def _save_or_submit(action, application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "applicant":
        return forbidden("Only applicants can submit applications.")

    try:
        job_posting_id = int(request.form.get("job_posting_id", "0"))
    except (TypeError, ValueError):
        return render_message("Invalid job posting.", "error"), 200

    declaration = request.form.get("declaration_accepted") in ("1", "true", "on")
    resume_file = request.files.get("resume_file")

    if action == "submit" and not declaration:
        return render_message("You must confirm the declaration before submitting.", "error"), 200

    resume_id_new = None
    if resume_file and resume_file.filename:
        error = validate_resume(resume_file)
        if error:
            return render_message(error, "error"), 200
        raw = resume_file.read()
        resume_id_new = integration_api.upload_application_resume(
            resume_file.filename, resume_file.mimetype or "application/pdf", raw,
        )
        if resume_id_new is None:
            return render_message(
                "Could not save your resume to your profile. Please try again.", "error"), 200

    if application_id is None:
        if action == "submit" and resume_id_new is None:
            latest = integration_api.get_latest_profile_resume(user.get("user_id"))
            resume_id_new = int(latest["resume_id"]) if latest and latest.get("resume_id") else None
            if resume_id_new is None:
                return render_message("Please upload your resume before submitting.", "error"), 200
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
                return redirect_response(f"/apply/{job_posting_id}",
                                         toast="You already have an application for this posting.")
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
            resp.raise_for_status()
        except requests.RequestException:
            return render_message(DB_UNAVAILABLE, "error"), 200
        application_id = resp.json()["application_id"]
    else:
        existing, error = load_application(application_id)
        if error:
            return error
        if existing["user_id"] != user["user_id"]:
            return forbidden("You can only edit your own applications.")
        if existing["application_status"] != "Draft":
            return render_message("Only Draft applications can be edited.", "error"), 200
        if action == "submit" and resume_id_new is None and not existing.get("resume_id"):
            latest = integration_api.get_latest_profile_resume(user.get("user_id"))
            resume_id_new = int(latest["resume_id"]) if latest and latest.get("resume_id") else None
            if resume_id_new is None:
                return render_message("Please upload your resume before submitting.", "error"), 200
        update_payload = {"declaration_accepted": 1 if declaration else 0}
        if resume_id_new is not None:
            update_payload["resume_id"] = resume_id_new
        try:
            resp = database_api.update_application(application_id, update_payload)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
        except requests.RequestException:
            return render_message(DB_UNAVAILABLE, "error"), 200

    if action == "submit":
        try:
            resp = database_api.submit_application(application_id)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Cannot submit."), "error"), 200
        except requests.RequestException:
            return render_message(DB_UNAVAILABLE, "error"), 200
        return redirect_response(f"/applications/{application_id}",
                                 toast="Application submitted successfully.")

    return redirect_response(f"/apply/{job_posting_id}", toast="Draft saved.")


@applications_bp.post("/api/applications/save")
def save_new_draft():
    return _save_or_submit("save", None)


@applications_bp.post("/api/applications/submit")
def submit_new_application():
    return _save_or_submit("submit", None)


@applications_bp.put("/api/applications/<int:application_id>/save")
def save_existing_draft(application_id):
    return _save_or_submit("save", application_id)


@applications_bp.put("/api/applications/<int:application_id>/submit")
def submit_existing_draft(application_id):
    return _save_or_submit("submit", application_id)


# --------------------------------------------------------------------------- #
# Applicant: withdraw / delete                                                #
# --------------------------------------------------------------------------- #

@applications_bp.put("/api/applications/<int:application_id>/withdraw")
def withdraw(application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return forbidden("You can only withdraw your own applications.")
    if application["application_status"] not in WITHDRAWABLE_STATUSES:
        return render_message(
            f"Cannot withdraw an application in status '{application['application_status']}'.",
            "error"), 200
    try:
        resp = database_api.withdraw_application(application_id)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot withdraw."), "error"), 200
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200

    integration_api.remove_interviews_for_application(application_id)

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Your application has been successfully withdrawn.",
        "applicationWithdrawn": application_id,
    })
    return resp_out


@applications_bp.delete("/api/applications/<int:application_id>")
def delete_draft(application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if user.get("role") == "applicant" and application["user_id"] != user["user_id"]:
        return forbidden("You can only delete your own applications.")
    if application["application_status"] != "Draft":
        return render_message(
            "Only Draft applications can be deleted. Withdraw instead.", "error"), 200
    try:
        resp = database_api.delete_application(application_id)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot delete."), "error"), 200
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200

    if request.headers.get("HX-Current-URL", "").rstrip("/").endswith(
        f"/apply/{application['job_posting_id']}"
    ):
        return redirect_response("/", toast="Draft application deleted.")

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Draft application deleted.",
        "applicationDeleted": application_id,
    })
    return resp_out


# --------------------------------------------------------------------------- #
# Staff: application list / candidate profile / status changes                #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/context/staff/applications/<int:application_id>/profile")
def candidate_profile_context(application_id):
    user = integration_api.get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "staff":
        return context_error("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application.get("application_status") == "Withdrawn":
        return context_error("Application not found.")

    posting = integration_api.get_job_posting(application["job_posting_id"]) or {}
    candidate = integration_api.get_user(application["user_id"]) or {}
    profile = integration_api.get_profile_by_user_id(application["user_id"])
    resume = load_resume(application.get("resume_id"), "staff")

    return context_ok({
        "application": application,
        "posting": posting,
        "candidate": candidate,
        "profile": profile or {},
        "resume": resume,
    })


@applications_bp.get("/api/all-applications")
def all_applications():
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")

    params = {}
    for key in ("status", "job_posting_id"):
        v = request.args.get(key, "").strip()
        if v:
            params[key] = v

    try:
        resp = database_api.list_applications_response(params)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200

    apps = [a for a in resp.json() if a.get("application_status") not in ("Draft", "Withdrawn")]
    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    postings = integration_api.get_postings_map([a["job_posting_id"] for a in apps])
    users = integration_api.get_users_map([a["user_id"] for a in apps])

    def matches(a):
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
            "candidate": lambda a: (users.get(a["user_id"]) or {}).get("user_last_name", ""),
            "status": lambda a: a.get("application_status", ""),
        }
        if sort in key_map:
            apps = sorted(apps, key=key_map[sort], reverse=reverse)

    return render_staff_applications_table(apps, postings, users), 200


@applications_bp.get("/api/pending-summary")
def pending_summary():
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")
    try:
        resp = database_api.list_applications_response()
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(DB_UNAVAILABLE, "error"), 200
    apps = [a for a in resp.json() if a.get("application_status") != "Withdrawn"]
    return render_pending_interviews_bar(apps), 200


@applications_bp.get("/api/staff/applications/<int:application_id>/profile")
def candidate_profile(application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return error
    if application.get("application_status") == "Withdrawn":
        return render_message("Application not found.", "error"), 200
    posting = integration_api.get_job_posting(application["job_posting_id"]) or {}
    candidate = integration_api.get_user(application["user_id"]) or {}
    profile = integration_api.get_profile_by_user_id(application["user_id"])
    resume = load_resume(application.get("resume_id"), "staff")
    return render_candidate_profile(
        application, posting, candidate, resume, screening=None, profile=profile
    ), 200


@applications_bp.put("/api/applications/<int:application_id>/status")
def update_status(application_id):
    user = integration_api.get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Only staff can change application status.")

    new_status = ""
    if request.is_json:
        new_status = str((request.get_json(silent=True) or {}).get("application_status", "")).strip()
    if not new_status:
        new_status = request.args.get("application_status", "").strip()
    if not new_status:
        new_status = request.form.get("application_status", "").strip()

    if new_status not in ("Shortlisted", "Rejected"):
        return toast_response("Only Shortlisted or Rejected are allowed here.", "error")

    application, error = load_application(application_id)
    if error:
        return toast_response("Application not found.", "error")
    current_status = application.get("application_status")
    if new_status == "Shortlisted" and current_status != "Submitted":
        return toast_response(
            f"Only submitted applications can be updated here. Current status: {current_status}.",
            "error",
        )
    if new_status == "Rejected" and current_status == "Rejected":
        return toast_response("Application is already rejected.", "error")

    try:
        resp = database_api.update_application(application_id, {"application_status": new_status})
        if resp.status_code >= 400:
            return toast_response(resp.json().get("error", "Cannot update status."), "error")
    except requests.RequestException:
        return toast_response(DB_UNAVAILABLE, "error")
    return toast_response(f"Status updated to {new_status}.")


# --------------------------------------------------------------------------- #
# Resume download (streamed from student-1's database)                        #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/resumes/<int:resume_id>/download")
def download_resume(resume_id):
    user = integration_api.get_session_user()
    if not user:
        return "Unauthorized", 401
    try:
        upstream = integration_api.download_resume_stream(
            resume_id,
            user.get("role", "applicant"),
            user.get("user_id"),
        )
    except requests.RequestException:
        return "Backend unavailable", 502
    if upstream is None:
        return "Forbidden", 403
    if upstream.status_code == 404:
        return "Resume not found", 404
    if upstream.status_code != 200:
        return "Backend error", 502

    headers = {"Content-Type": upstream.headers.get("Content-Type", "application/octet-stream")}
    disposition = upstream.headers.get("Content-Disposition")
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=200, headers=headers,
    )
