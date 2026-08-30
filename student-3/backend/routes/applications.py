"""Applicant-facing routes (HTML fragments + JSON context for HTMX).

Covers listing/viewing an applicant's own applications, the apply form, saving
drafts, submitting, withdrawing and deleting draft applications.
"""

import json

import requests
from flask import Blueprint, make_response, request

from config import (
    DATABASE_SERVICE_URL,
    INTERVIEWS_DB_URL,
    INTERVIEWS_URL,
    INTERVIEW_ACTION_STATUSES,
    TIMEOUT,
    WITHDRAWABLE_STATUSES,
    _DB_UNAVAILABLE,
)
from routes.common import (
    context_error,
    context_ok,
    forbidden,
    load_application,
    load_resume,
    redirect_response,
    unauthorized,
    validate_resume,
)
from services.database_api import (
    get_job_posting,
    get_latest_profile_resume,
    get_postings_map,
    get_session_user,
    upload_application_resume,
)
from views.html_formatters import (
    render_application_detail,
    render_apply_form,
    render_message,
    render_my_applications_table,
)

applications_bp = Blueprint("applications", __name__)


# --------------------------------------------------------------------------- #
# Applicant: list / detail / apply form                                       #
# --------------------------------------------------------------------------- #

@applications_bp.get("/api/context/apply/<int:job_posting_id>")
def apply_form_context(job_posting_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "applicant":
        return context_error("Only applicants can submit applications.")

    posting = get_job_posting(job_posting_id)
    if not posting:
        return context_error("Job posting not found.")
    if posting.get("JobPosting_Status") != "Published":
        return context_error("This job posting is no longer accepting applications.")

    try:
        resp = requests.get(
            f"{DATABASE_SERVICE_URL}/applications",
            params={"user_id": user["user_id"], "job_posting_id": job_posting_id},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return context_error(_DB_UNAVAILABLE)

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
                resume = get_latest_profile_resume(user.get("user_id"))
            break
        return context_error(
            f"You already applied for this job (status: {existing['application_status']}).",
            kind="info",
        )

    if resume is None:
        resume = get_latest_profile_resume(user.get("user_id"))

    return context_ok({
        "posting": posting,
        "user": applicant_ctx,
        "application": application,
        "resume": resume,
    })


@applications_bp.get("/api/context/applications/<int:application_id>/detail")
def applicant_application_detail_context(application_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application["user_id"] != user["user_id"]:
        return context_error("You can only view your own applications.")

    posting = get_job_posting(application["job_posting_id"]) or {}
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
    user = get_session_user()
    if not user:
        return unauthorized()
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications",
                            params={"user_id": user["user_id"]}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    apps = resp.json()
    postings = get_postings_map([a["job_posting_id"] for a in apps])

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
    user = get_session_user()
    if not user:
        return unauthorized()
    application, error = load_application(application_id)
    if error:
        return error
    if application["user_id"] != user["user_id"]:
        return forbidden("You can only view your own applications.")
    posting = get_job_posting(application["job_posting_id"]) or {}
    resume = load_resume(application.get("resume_id"), user.get("role", "applicant"), user.get("user_id"))
    return render_application_detail(application, posting, user, resume), 200


@applications_bp.get("/api/apply/<int:job_posting_id>")
def apply_form(job_posting_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "applicant":
        return forbidden("Only applicants can submit applications.")

    posting = get_job_posting(job_posting_id)
    if not posting:
        return render_message("Job posting not found.", "error"), 200
    if posting.get("JobPosting_Status") != "Published":
        return render_message("This job posting is no longer accepting applications.", "error"), 200

    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications",
                            params={"user_id": user["user_id"], "job_posting_id": job_posting_id},
                            timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

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
                resume = get_latest_profile_resume(user.get("user_id"))
            return render_apply_form(posting, applicant_ctx, existing, resume), 200
        return render_message(
            f"You already applied for this job (status: {existing['application_status']}).",
            "info",
        ), 200

    profile_resume = get_latest_profile_resume(user.get("user_id"))
    return render_apply_form(posting, applicant_ctx, resume=profile_resume), 200


# --------------------------------------------------------------------------- #
# Applicant: save-draft / submit                                              #
# --------------------------------------------------------------------------- #

def _save_or_submit(action, application_id):
    user = get_session_user()
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
        resume_id_new = upload_application_resume(
            resume_file.filename, resume_file.mimetype or "application/pdf", raw,
        )
        if resume_id_new is None:
            return render_message(
                "Could not save your resume to your profile. Please try again.", "error"), 200

    if application_id is None:
        if action == "submit" and resume_id_new is None:
            latest = get_latest_profile_resume(user.get("user_id"))
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
            resp = requests.post(f"{DATABASE_SERVICE_URL}/applications",
                                 json=create_payload, timeout=TIMEOUT)
            if resp.status_code == 409:
                return redirect_response(f"/apply/{job_posting_id}",
                                         toast="You already have an application for this posting.")
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
            resp.raise_for_status()
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
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
            latest = get_latest_profile_resume(user.get("user_id"))
            resume_id_new = int(latest["resume_id"]) if latest and latest.get("resume_id") else None
            if resume_id_new is None:
                return render_message("Please upload your resume before submitting.", "error"), 200
        update_payload = {"declaration_accepted": 1 if declaration else 0}
        if resume_id_new is not None:
            update_payload["resume_id"] = resume_id_new
        try:
            resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                                json=update_payload, timeout=TIMEOUT)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Invalid data."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200

    if action == "submit":
        try:
            resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}/submit",
                                timeout=TIMEOUT)
            if resp.status_code >= 400:
                return render_message(resp.json().get("error", "Cannot submit."), "error"), 200
        except requests.RequestException:
            return render_message(_DB_UNAVAILABLE, "error"), 200
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

def _remove_linked_interviews(application_id):
    """Withdrawing an application removes any interview booked against it."""
    try:
        resp = requests.get(f"{INTERVIEWS_DB_URL}/interviews", timeout=TIMEOUT)
        resp.raise_for_status()
        interviews = resp.json()
    except (requests.RequestException, ValueError):
        return
    for row in interviews:
        if str(row.get("application_id")) != str(application_id):
            continue
        try:
            requests.delete(
                f"{INTERVIEWS_DB_URL}/interviews/{row.get('interview_id')}", timeout=TIMEOUT
            )
        except requests.RequestException:
            continue


@applications_bp.put("/api/applications/<int:application_id>/withdraw")
def withdraw(application_id):
    user = get_session_user()
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
        resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}/withdraw",
                            timeout=TIMEOUT)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot withdraw."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    _remove_linked_interviews(application_id)

    resp_out = make_response("", 200)
    resp_out.headers["HX-Trigger"] = json.dumps({
        "showToast": "Your application has been successfully withdrawn.",
        "applicationWithdrawn": application_id,
    })
    return resp_out


@applications_bp.delete("/api/applications/<int:application_id>")
def delete_draft(application_id):
    user = get_session_user()
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
        resp = requests.delete(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                               timeout=TIMEOUT)
        if resp.status_code >= 400:
            return render_message(resp.json().get("error", "Cannot delete."), "error"), 200
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

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
