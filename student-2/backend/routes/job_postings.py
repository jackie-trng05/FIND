"""JobPostingService routes (HTML fragments for HTMX).

Implements the backend/API functions from the registration form:
  CreateJobPosting    POST   /job-postings
  GetAllJobPostings   GET    /job-postings
  GetJobPosting       GET    /job-postings/{id}
  UpdateJobPosting    PUT    /job-postings/{id}
  PublishJobPosting   PUT    /job-postings/{id}/publish
  UnpublishJobPosting PUT    /job-postings/{id}/unpublish
  DeleteJobPosting    DELETE /job-postings/{id}

Each handler returns an HTML fragment that HTMX swaps into the page, or an
``HX-Redirect`` response that navigates the browser to another page.
"""

import os
from datetime import date

import requests
from flask import Blueprint, make_response, request

from services import database_api
from views.html_formatters import (
    normalize_requirements,
    render_message,
    render_posting_form,
    render_posting_panel,
    render_postings_table,
)

job_postings_bp = Blueprint("job_postings", __name__)

# Public URLs the browser uses (host-mapped ports).
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16008")
FRONTEND_PUBLIC_URL = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16007")

# Internal URL for the shared-api service used to validate the session cookie.
SHARED_API_URL = os.getenv("SHARED_API_URL", "http://find-shared-api:5000")

# Internal URL for the student-3 (applications) database service. Used to
# check whether the current applicant already has an application for a posting
# so the Apply button on the applicant panel can be disabled.
APPLICATIONS_DB_URL = os.getenv(
    "APPLICATIONS_DB_URL", "http://student-3-db:6003"
)

# Staff ID is assigned automatically (no auth layer in this service).
DEFAULT_STAFF_ID = os.getenv("DEFAULT_STAFF_ID", "101")

EDITABLE_FIELDS = (
    "Job_Title",
    "Job_Description",
    "Job_Type",
    "Location",
    "Salary_Range",
    "Requirements",
    "Application_Deadline",
)

_DB_UNAVAILABLE = (
    "Could not reach the database service. Make sure the student-2-db "
    "container is running."
)

# Fields that must be provided when creating/updating a posting.
REQUIRED_FIELDS = (
    ("Job_Title", "Job title"),
    ("Job_Type", "Job type"),
    ("Location", "Location"),
    ("Job_Description", "Description"),
    ("Requirements", "Requirements"),
)


def _missing_required(payload: dict) -> str | None:
    """Return an error message for the first missing required field, else None."""
    for field, label in REQUIRED_FIELDS:
        if not payload.get(field, "").strip():
            return f"{label} is required."
    return None


def _get_role() -> str:
    """Return 'staff' or 'applicant' based on the session cookie."""
    user = _get_session_user()
    if user is None:
        return "applicant"
    role = (user.get("role") or "").strip().lower()
    return "staff" if role == "staff" else "applicant"


def _get_session_user() -> dict | None:
    """Return the currently logged-in user dict, or None if unauthenticated."""
    cookie = request.headers.get("Cookie", "")
    if not cookie:
        return None
    try:
        resp = requests.get(
            f"{SHARED_API_URL}/api/auth/session",
            headers={"Cookie": cookie},
            timeout=5,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json().get("user")


def _get_existing_application(user_id: int, posting_id: int) -> dict | None:
    """Return the applicant's existing active application for this posting,
    or None if there isn't one.

    Withdrawn/Rejected applications are treated as "no application" so the
    candidate can apply again.
    """
    try:
        resp = requests.get(
            f"{APPLICATIONS_DB_URL}/applications",
            params={"user_id": user_id, "job_posting_id": posting_id},
            timeout=5,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    for row in resp.json() or []:
        status = row.get("application_status")
        if status not in ("Withdrawn", "Rejected"):
            return {
                "application_id": row.get("application_id"),
                "application_status": status,
            }
    return None


def _forbidden_for_applicants():
    """Return an HTMX-safe error fragment when an applicant tries to mutate."""
    return render_message("Applicants cannot modify job postings.", "error"), 200


def _validate_deadline(payload: dict) -> str | None:
    """Return an error if the deadline is in the past, else None."""
    deadline = payload.get("Application_Deadline", "").strip()
    if not deadline:
        return None
    try:
        if date.fromisoformat(deadline) < date.today():
            return "Application deadline cannot be in the past."
    except ValueError:
        return "Application deadline must be a valid date."
    return None


@job_postings_bp.get("/")
def index():
    return "<p>student-2 backend (Job Posting Management) running</p>", 200


@job_postings_bp.get("/health")
def health():
    return {"status": "ok"}, 200


def _redirect(path: str):
    """Return an empty response that tells HTMX to navigate the browser."""
    resp = make_response("", 200)
    resp.headers["HX-Redirect"] = f"{FRONTEND_PUBLIC_URL}{path}"
    return resp


@job_postings_bp.get("/job-postings")
def list_postings():
    """Return admin table rows, honouring the status/type/location/q filters."""
    params = {}
    for key in ("status", "job_type", "location", "q"):
        value = request.args.get(key, "").strip()
        if value:
            params[key] = value

    try:
        response = database_api.list_job_postings(params)
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200

    role = _get_role()
    # Applicants only ever see Published postings.
    postings = response.json()
    if role == "applicant":
        postings = [p for p in postings if p.get("JobPosting_Status") == "Published"]
    return render_postings_table(postings, frontend_url=FRONTEND_PUBLIC_URL, role=role), 200


def _load_posting(posting_id: int):
    """Fetch a posting or return (None, error_fragment)."""
    try:
        response = database_api.get_job_posting(posting_id)
        if response.status_code == 404:
            return None, (render_message("Job posting not found.", "error"), 200)
        response.raise_for_status()
    except requests.RequestException:
        return None, (render_message(_DB_UNAVAILABLE, "error"), 200)
    return response.json(), None


@job_postings_bp.get("/job-postings/<int:posting_id>")
def get_posting(posting_id: int):
    """Return the detail panel for a single posting page."""
    posting, error = _load_posting(posting_id)
    if error:
        return error
    user = _get_session_user()
    role = "staff" if (user and (user.get("role") or "").lower() == "staff") else "applicant"
    # Applicants may only view Published postings.
    if role == "applicant" and posting.get("JobPosting_Status") != "Published":
        return render_message("Job posting not found.", "error"), 200

    existing_application = None
    if role == "applicant" and user:
        existing_application = _get_existing_application(
            user.get("user_id"), posting_id
        )
    return (
        render_posting_panel(
            posting, backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL,
            role=role, existing_application=existing_application,
        ),
        200,
    )


@job_postings_bp.get("/job-postings/new")
def new_posting_form():
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    return render_posting_form(BACKEND_PUBLIC_URL), 200


@job_postings_bp.get("/job-postings/<int:posting_id>/edit")
def edit_posting_form(posting_id: int):
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    posting, error = _load_posting(posting_id)
    if error:
        return error
    return render_posting_form(BACKEND_PUBLIC_URL, posting), 200


def _payload_from_form() -> dict:
    payload = {field: request.form.get(field, "").strip() for field in EDITABLE_FIELDS}
    # Capitalise the first letter of the job title.
    title = payload.get("Job_Title", "")
    if title:
        payload["Job_Title"] = title[0].upper() + title[1:]
    # Capitalise the first letter of the location.
    location = payload.get("Location", "")
    if location:
        payload["Location"] = location[0].upper() + location[1:]
    # Normalise requirements into one bullet-prefixed item per line.
    payload["Requirements"] = normalize_requirements(payload.get("Requirements", ""))
    return payload


def _panel(posting_id: int):
    """Return the refreshed detail panel after a mutation."""
    posting, error = _load_posting(posting_id)
    if error:
        return error
    return (
        render_posting_panel(
            posting, backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL
        ),
        200,
    )


@job_postings_bp.post("/job-postings")
def create_posting():
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    payload = _payload_from_form()
    error = _missing_required(payload) or _validate_deadline(payload)
    if error:
        return render_message(error, "error"), 200
    # Staff ID is assigned automatically.
    payload["Staff_Id"] = DEFAULT_STAFF_ID

    try:
        response = database_api.create_job_posting(payload)
        if response.status_code == 400:
            return render_message(response.json().get("error", "Invalid data."), "error"), 200
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    # Success: send the browser back to the list page with a toast.
    return _redirect("/?toast=Job+posting+created+successfully")


@job_postings_bp.put("/job-postings/<int:posting_id>")
def update_posting(posting_id: int):
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    payload = _payload_from_form()
    error = _missing_required(payload) or _validate_deadline(payload)
    if error:
        data = dict(payload)
        data["JobPosting_Id"] = posting_id
        return render_posting_form(BACKEND_PUBLIC_URL, data, error=error), 200

    try:
        response = database_api.update_job_posting(posting_id, payload)
        if response.status_code == 404:
            return render_message("Job posting not found.", "error"), 200
        if response.status_code == 400:
            data = dict(payload)
            data["JobPosting_Id"] = posting_id
            message = response.json().get("error", "Invalid data.")
            return render_posting_form(BACKEND_PUBLIC_URL, data, error=message), 200
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    # Return the refreshed panel with a toast trigger for success feedback.
    posting, error = _load_posting(posting_id)
    if error:
        return error
    resp = make_response(
        render_posting_panel(
            posting, backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL
        ),
        200,
    )
    resp.headers["HX-Trigger"] = '{"showToast": "Changes saved successfully"}'
    return resp


@job_postings_bp.put("/job-postings/<int:posting_id>/publish")
def publish_posting(posting_id: int):
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    try:
        response = database_api.publish_job_posting(posting_id)
        if response.status_code == 404:
            return render_message("Job posting not found.", "error"), 200
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    posting, error = _load_posting(posting_id)
    if error:
        return error
    resp = make_response(
        render_posting_panel(
            posting, backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL
        ),
        200,
    )
    resp.headers["HX-Trigger"] = '{"showToast": "Job posting published successfully"}'
    return resp


@job_postings_bp.put("/job-postings/<int:posting_id>/unpublish")
def unpublish_posting(posting_id: int):
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    try:
        response = database_api.unpublish_job_posting(posting_id)
        if response.status_code == 404:
            return render_message("Job posting not found.", "error"), 200
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    posting, error = _load_posting(posting_id)
    if error:
        return error
    resp = make_response(
        render_posting_panel(
            posting, backend_url=BACKEND_PUBLIC_URL, frontend_url=FRONTEND_PUBLIC_URL
        ),
        200,
    )
    resp.headers["HX-Trigger"] = '{"showToast": "Job posting unpublished"}'
    return resp


@job_postings_bp.delete("/job-postings/<int:posting_id>")
def delete_posting(posting_id: int):
    if _get_role() == "applicant":
        return _forbidden_for_applicants()
    try:
        response = database_api.delete_job_posting(posting_id)
        if response.status_code == 404:
            return render_message("Job posting not found.", "error"), 200
        response.raise_for_status()
    except requests.RequestException:
        return render_message(_DB_UNAVAILABLE, "error"), 200
    # Success: the posting is gone, so navigate back to the list with a toast.
    return _redirect("/?toast=Job+posting+deleted+successfully")
