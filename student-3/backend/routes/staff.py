"""Staff-facing routes (HTML fragments + JSON context for HTMX).

Covers the staff application list with search/sort, the pending-interviews
summary bar, the candidate profile panel and status changes.
"""

import requests
from flask import Blueprint, request

from config import (
    DATABASE_SERVICE_URL,
    TIMEOUT,
    _DB_UNAVAILABLE,
)
from routes.common import (
    context_error,
    context_ok,
    forbidden,
    load_application,
    load_resume,
    toast_response,
    unauthorized,
)
from services.database_api import (
    get_job_posting,
    get_profile_by_user_id,
    get_postings_map,
    get_session_user,
    get_user,
    get_users_map,
)
from views.html_formatters import (
    render_candidate_profile,
    render_message,
    render_pending_interviews_bar,
    render_staff_applications_table,
)

staff_bp = Blueprint("staff", __name__)


@staff_bp.get("/api/context/staff/applications/<int:application_id>/profile")
def candidate_profile_context(application_id):
    user = get_session_user()
    if not user:
        return context_error("Please log in first.", status=401)
    if user.get("role") != "staff":
        return context_error("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return context_error("Application not found.")
    if application.get("application_status") == "Withdrawn":
        return context_error("Application not found.")

    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}
    profile = get_profile_by_user_id(application["user_id"])
    resume = load_resume(application.get("resume_id"), "staff")

    return context_ok({
        "application": application,
        "posting": posting,
        "candidate": candidate,
        "profile": profile or {},
        "resume": resume,
    })


@staff_bp.get("/api/all-applications")
def all_applications():
    user = get_session_user()
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
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    apps = [a for a in resp.json() if a.get("application_status") not in ("Draft", "Withdrawn")]
    q = request.args.get("q", "").strip().lower()
    sort = request.args.get("sort", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    postings = get_postings_map([a["job_posting_id"] for a in apps])
    users = get_users_map([a["user_id"] for a in apps])

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


@staff_bp.get("/api/pending-summary")
def pending_summary():
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")
    try:
        resp = requests.get(f"{DATABASE_SERVICE_URL}/applications", timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    apps = [a for a in resp.json() if a.get("application_status") != "Withdrawn"]
    return render_pending_interviews_bar(apps), 200


@staff_bp.get("/api/staff/applications/<int:application_id>/profile")
def candidate_profile(application_id):
    user = get_session_user()
    if not user:
        return unauthorized()
    if user.get("role") != "staff":
        return forbidden("Staff view only.")

    application, error = load_application(application_id)
    if error:
        return error
    if application.get("application_status") == "Withdrawn":
        return render_message("Application not found.", "error"), 200
    posting = get_job_posting(application["job_posting_id"]) or {}
    candidate = get_user(application["user_id"]) or {}
    profile = get_profile_by_user_id(application["user_id"])
    resume = load_resume(application.get("resume_id"), "staff")
    return render_candidate_profile(
        application, posting, candidate, resume, screening=None, profile=profile
    ), 200


@staff_bp.put("/api/applications/<int:application_id>/status")
def update_status(application_id):
    user = get_session_user()
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
        resp = requests.put(f"{DATABASE_SERVICE_URL}/applications/{application_id}",
                            json={"application_status": new_status}, timeout=TIMEOUT)
        if resp.status_code >= 400:
            return toast_response(resp.json().get("error", "Cannot update status."), "error")
    except requests.RequestException:
        return toast_response(_DB_UNAVAILABLE, "error")
    return toast_response(f"Status updated to {new_status}.")
