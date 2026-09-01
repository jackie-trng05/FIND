import json
from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, request
import requests

from services.database_api import (
    create_interview,
    delete_interview,
    get_interview_response,
    get_interviews_response,
    update_interview,
)
from services import integration_api
from services.config import BACKEND_PUBLIC_URL, FRONTEND_PUBLIC_URL
from services.integration_api import get_session_user
from views import html_formatters as fmt


interviews_bp = Blueprint("interviews", __name__)

# Interview statuses mirror the linked application's status (Student 3).
STATUS_SHORTLISTED = "Shortlisted"                 # shortlisted, no invite sent yet
STATUS_REQUESTED = "Interview Requested"           # invite sent, awaiting applicant
STATUS_SCHEDULED = "Interview Scheduled"           # applicant accepted
STATUS_COMPLETED = "Interview Completed"           # staff marked complete
STATUS_WITHDRAWN = "Withdrawn"                     # applicant declined

# Interviews shown on the calendar and "All Interviews" list: only those whose
# linked application is an active part of the interview lifecycle.
VISIBLE_INTERVIEW_STATUSES = (STATUS_REQUESTED, STATUS_SCHEDULED, STATUS_COMPLETED)

# Skill areas a staff member must assess before completing an interview.
NOTE_SECTIONS = (
    "Technical",
    "Education",
    "Communication",
    "Problem Solving",
    "Professionalism",
)

DB_ERROR = "Failed to reach the interview database-service."


def _db_error(exc):
    return jsonify({"error": DB_ERROR, "detail": str(exc)}), 503


def _positive_int(value):
    try:
        return int(str(value).strip()) > 0
    except (TypeError, ValueError):
        return False


def _valid_datetime(value):
    try:
        datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M")
        return True
    except (TypeError, ValueError):
        return False


def _is_future(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M") > datetime.now()
    except (TypeError, ValueError):
        return False


def _is_past(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M") <= datetime.now()
    except (TypeError, ValueError):
        return False


def _valid_link(value):
    value = (value or "").strip()
    return value == "" or value.startswith("http://") or value.startswith("https://")


def _can_cancel(interview):
    """An interview can only be cancelled while it is still upcoming.

    That means an outstanding request (Interview Requested), or a scheduled
    interview whose date/time is still in the future. A scheduled interview
    that has already taken place is completed, not cancelled.
    """
    status = interview.get("application_status")
    if status == STATUS_REQUESTED:
        return True
    return status == STATUS_SCHEDULED and _is_future(interview.get("interview_datetime"))


# --------------------------------------------------------------------------- #
# Session + HTMX helpers                                                       #
# --------------------------------------------------------------------------- #

def require_session():
    """Return (user, None) when authenticated, else (None, 401 response)."""
    user = get_session_user()
    if not user:
        return None, (jsonify({"error": "Authentication required."}), 401)
    return user, None


def _wants_hx():
    return request.headers.get("HX-Request") == "true"


def _read_input():
    """Accept either a JSON body or an HTMX form submission."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data or {}


def _scope_to_user(interviews, user):
    """Staff see every interview; applicants only see their own."""
    if user.get("role") == "staff":
        return list(interviews)
    uid = str(user.get("user_id"))
    return [i for i in interviews if str(i.get("applicant_id")) == uid]


def _hx_response(triggers=None, redirect=None, status=200):
    resp = Response(status=status)
    if triggers:
        resp.headers["HX-Trigger"] = json.dumps(triggers)
    if redirect:
        resp.headers["HX-Redirect"] = redirect
    return resp


@interviews_bp.get("/")
def health():
    return jsonify({"service": "student-4-interview-service", "status": "running"})


@interviews_bp.get("/interviews")
def list_interviews():
    _, err = require_session()
    if err:
        return err
    user_id = request.args.get("user_id", "").strip()
    applicant_id = request.args.get("applicant_id", "").strip()
    status = request.args.get("status", "").strip()

    try:
        response = get_interviews_response({})
        response.raise_for_status()
        interviews = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    interviews = integration_api.enrich_interviews(interviews)

    # Ownership + status filtering happens here so the DB stays a thin store.
    if user_id:
        interviews = [i for i in interviews if str(i.get("user_id")) == user_id]
    if applicant_id:
        interviews = [i for i in interviews if str(i.get("applicant_id")) == applicant_id]
    if status:
        interviews = [i for i in interviews if str(i.get("application_status")) == status]

    return jsonify(interviews), 200


@interviews_bp.get("/interviews/to-complete")
def interviews_to_complete():
    """Scheduled interviews whose time has passed and still need notes.

    These are the interviews a staff member must write up (all five skill
    notes) to move them to "Interview Completed".
    """
    _, err = require_session()
    if err:
        return err
    user_id = request.args.get("user_id", "").strip()

    try:
        response = get_interviews_response({})
        response.raise_for_status()
        interviews = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    interviews = integration_api.enrich_interviews(interviews)
    interviews = [
        i for i in interviews
        if str(i.get("application_status")) == STATUS_SCHEDULED
        and _is_past(i.get("interview_datetime"))
    ]

    if user_id:
        interviews = [i for i in interviews if str(i.get("user_id")) == user_id]

    return jsonify(interviews), 200


@interviews_bp.get("/interviews/<int:interview_id>")
def get_interview(interview_id):
    _, err = require_session()
    if err:
        return err
    try:
        response = get_interview_response(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        return jsonify(integration_api.enrich_one(response.json())), 200
    except requests.RequestException as exc:
        return _db_error(exc)


@interviews_bp.get("/schedulable-applications")
def schedulable_applications():
    """Shortlisted applications a staff member still needs to interview.

    Applications come from Student 3; postings ownership from Student 2.
    Applications that already have an interview request are filtered out.
    """
    _, err = require_session()
    if err:
        return err
    user_id = request.args.get("user_id", "").strip()
    if not _positive_int(user_id):
        return jsonify({"error": "A valid user_id is required."}), 400

    applications = integration_api.shortlisted_for_staff(user_id)

    scheduled = _scheduled_application_ids()
    applications = [
        app for app in applications
        if str(app.get("application_id")) not in scheduled
    ]
    return jsonify({"applications": applications}), 200


def _scheduled_application_ids():
    """Application IDs that already have a live interview request.

    Declined interviews are deleted outright, so every remaining row here is
    live and there's no withdrawn status to filter out.
    """
    try:
        response = get_interviews_response({})
        response.raise_for_status()
        interviews = response.json()
    except requests.RequestException:
        return set()
    return {str(row.get("application_id")) for row in interviews}


@interviews_bp.post("/interviews")
def schedule_interview():
    user, err = require_session()
    if err:
        return err
    data = _read_input()

    errors = {}
    application_id = str(data.get("application_id", "")).strip()
    user_id = str(data.get("user_id", "")).strip()
    interview_datetime = str(data.get("interview_datetime", "")).strip()
    interview_link = str(data.get("interview_link", "")).strip()
    interview_notes = str(data.get("interview_notes", "")).strip()

    if not _positive_int(application_id):
        errors["application_id"] = "Application ID must be a positive number."
    if not _positive_int(user_id):
        errors["user_id"] = "Staff ID is required."
    if not _valid_datetime(interview_datetime):
        errors["interview_datetime"] = "Enter the interview date and time using the picker."
    elif not _is_future(interview_datetime):
        errors["interview_datetime"] = (
            "The interview date and time can't be in the past — please choose a future date and time."
        )
    if not _valid_link(interview_link):
        errors["interview_link"] = "Link must start with http:// or https://."

    if errors:
        if _wants_hx():
            message = (
                errors.get("interview_datetime")
                or errors.get("interview_link")
                or errors.get("application_id")
                or errors.get("user_id")
                or "Please check the form and try again."
            )
            return _hx_response(triggers={"showErrorToast": message})
        return jsonify({"errors": errors}), 400

    payload = {
        "application_id": application_id,
        "user_id": user_id,
        "interview_datetime": interview_datetime,
        "interview_link": interview_link,
        "interview_notes": interview_notes,
    }

    try:
        response = create_interview(payload)
        response.raise_for_status()
        interview = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    # Sending an invite moves the application to "Interview Requested".
    integration_api.set_application_status(application_id, STATUS_REQUESTED)
    if _wants_hx():
        return _hx_response(
            redirect=f"{FRONTEND_PUBLIC_URL}/?toast={quote('Interview scheduled.')}"
        )
    return jsonify(integration_api.enrich_one(interview)), 201


@interviews_bp.put("/interviews/<int:interview_id>")
def update_interview_route(interview_id):
    """Update mutable interview fields.

    Interview *details* (date/time, meeting link) are fixed once created —
    the only thing staff can update through this route is the assessment
    notes. Status transitions go through the dedicated accept/decline/complete
    endpoints, which sync the linked application's status instead.
    """
    _, err = require_session()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    payload = {}
    errors = {}

    if "interview_datetime" in data or "interview_link" in data:
        errors["interview_details"] = (
            "Interview details cannot be changed after the interview is created."
        )

    if "interview_notes" in data:
        payload["interview_notes"] = str(data["interview_notes"]).strip()

    if errors:
        return jsonify({"errors": errors}), 400
    if not payload:
        return jsonify({"error": "No update details provided."}), 400

    return _apply_update(interview_id, payload)


@interviews_bp.post("/interviews/<int:interview_id>/accept")
def accept_interview(interview_id):
    """Applicant accepts the request -> Interview Scheduled."""
    _, err = require_session()
    if err:
        return err
    return _apply_update(
        interview_id,
        app_status=STATUS_SCHEDULED,
        hx_success={"redirect": f"{FRONTEND_PUBLIC_URL}/requests?toast={quote('Interview accepted.')}"},
    )


@interviews_bp.post("/interviews/<int:interview_id>/decline")
def decline_interview(interview_id):
    """Applicant declines the request -> interview removed, application Shortlisted."""
    _, err = require_session()
    if err:
        return err
    try:
        response = get_interview_response(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        application_id = response.json().get("application_id")

        deleted = delete_interview(interview_id)
        deleted.raise_for_status()
    except requests.RequestException as exc:
        return _db_error(exc)

    integration_api.set_application_status(application_id, STATUS_SHORTLISTED)
    if _wants_hx():
        return _hx_response(
            redirect=f"{FRONTEND_PUBLIC_URL}/requests?toast={quote('Interview declined.')}"
        )
    return jsonify({"declined": interview_id}), 200


@interviews_bp.post("/interviews/<int:interview_id>/complete")
def complete_interview(interview_id):
    """Record assessment notes and mark the interview complete.

    Completing is only allowed once the interview has actually taken place
    (its date/time is in the past) and the applicant has accepted it
    (status "Interview Scheduled"). All five skill-area notes are required —
    saving them is what moves the interview to "Interview Completed".
    """
    _, err = require_session()
    if err:
        return err

    data = request.get_json(silent=True)
    if data is not None:
        raw_notes = data.get("interview_notes")
        if not isinstance(raw_notes, dict):
            return jsonify({"error": "Interview notes are required to complete."}), 400
    else:
        # HTMX form submission: notes arrive as note-<Section> fields.
        raw_notes = {s: request.form.get(f"note-{s}", "") for s in NOTE_SECTIONS}

    errors = {}
    cleaned = {}
    for section in NOTE_SECTIONS:
        value = str(raw_notes.get(section, "")).strip()
        if not value:
            errors[section] = "This section is required."
        cleaned[section] = value
    if errors:
        if _wants_hx():
            return _hx_response(triggers={
                "showErrorToast": "Please complete all five note sections."
            })
        return jsonify({"errors": errors}), 400

    try:
        response = get_interview_response(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        interview = integration_api.enrich_one(response.json())
    except requests.RequestException as exc:
        return _db_error(exc)

    if interview.get("application_status") != STATUS_SCHEDULED:
        if _wants_hx():
            return _hx_response(triggers={"showErrorToast": "Only a scheduled interview can be completed."})
        return jsonify({
            "error": "Only a scheduled interview can be completed."
        }), 400
    if _is_future(interview.get("interview_datetime")):
        if _wants_hx():
            return _hx_response(triggers={"showErrorToast": "This interview has not taken place yet."})
        return jsonify({
            "error": "This interview has not taken place yet, so it cannot be completed."
        }), 400

    payload = {
        "interview_notes": json.dumps(cleaned),
    }
    return _apply_update(
        interview_id,
        payload,
        app_status=STATUS_COMPLETED,
        hx_success={"triggers": {
            "showToast": "Interview completed.",
            "interviewChanged": True,
        }},
    )


@interviews_bp.delete("/interviews/<int:interview_id>")
def cancel_interview(interview_id):
    _, err = require_session()
    if err:
        return err

    try:
        current = get_interview_response(interview_id)
        if current.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        current.raise_for_status()
        interview = integration_api.enrich_one(current.json())
    except requests.RequestException as exc:
        return _db_error(exc)

    if not _can_cancel(interview):
        message = "This interview can no longer be cancelled."
        if _wants_hx():
            return _hx_response(triggers={"showErrorToast": message})
        return jsonify({"error": message}), 400

    try:
        response = delete_interview(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
    except requests.RequestException as exc:
        return _db_error(exc)

    if _wants_hx():
        return _hx_response(
            redirect=f"{FRONTEND_PUBLIC_URL}/list?toast={quote('Interview cancelled.')}"
        )
    return jsonify({"cancelled": interview_id}), 200


def _apply_update(interview_id, payload=None, app_status=None, hx_success=None):
    try:
        if payload:
            response = update_interview(interview_id, payload)
        else:
            response = get_interview_response(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        interview = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    # Keep the linked application's status in sync with the interview.
    if app_status:
        integration_api.set_application_status(interview.get("application_id"), app_status)

    if hx_success and _wants_hx():
        return _hx_response(
            triggers=hx_success.get("triggers"),
            redirect=hx_success.get("redirect"),
        )
    return jsonify(integration_api.enrich_one(interview)), 200


# --------------------------------------------------------------------------- #
# HTMX fragment endpoints (/ui/*) — consumed by the Flask frontend            #
# --------------------------------------------------------------------------- #

def _all_enriched():
    response = get_interviews_response({})
    response.raise_for_status()
    return integration_api.enrich_interviews(response.json())


def _parse_date_only(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


@interviews_bp.get("/ui/calendar")
def ui_calendar():
    user, err = require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        interviews = []
    interviews = [
        i for i in interviews
        if i.get("application_status") in VISIBLE_INTERVIEW_STATUSES
    ]

    now = datetime.now()
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month:
        year, month = now.year, now.month
    return fmt.render_calendar(interviews, year, month, backend_url=BACKEND_PUBLIC_URL), 200


@interviews_bp.get("/ui/interviews/rows")
def ui_interview_rows():
    user, err = require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load interviews.</div>', 200
    interviews = [
        i for i in interviews
        if i.get("application_status") in VISIBLE_INTERVIEW_STATUSES
    ]

    status = request.args.get("status", "").strip()
    job_posting = request.args.get("job_posting", "").strip()
    date_from = _parse_date_only(request.args.get("from", "").strip())
    date_to = _parse_date_only(request.args.get("to", "").strip())
    search = request.args.get("search", "").strip().lower()
    sort = request.args.get("sort", "datetime")
    direction = request.args.get("dir", "asc")

    def _keep(it):
        if status and str(it.get("application_status")).lower() != status.lower():
            return False
        if job_posting and str(it.get("job_posting_id") or "") != job_posting:
            return False
        dt = fmt._parse_dt(it.get("interview_datetime"))
        if date_from and dt and dt < date_from:
            return False
        if date_to and dt and dt > date_to.replace(hour=23, minute=59):
            return False
        if search:
            hay = f"{it.get('applicant_name', '')} {it.get('applicant_id', '')} {it.get('application_id', '')}".lower()
            if search not in hay:
                return False
        return True

    rows = [it for it in interviews if _keep(it)]
    return fmt.render_interview_rows(rows, role=user.get("role"), sort=sort, direction=direction, backend_url=BACKEND_PUBLIC_URL), 200


@interviews_bp.get("/ui/applications/rows")
def ui_applications_rows():
    user, err = require_session()
    if err:
        return err
    if user.get("role") != "staff":
        return '<div class="empty-state">Staff only.</div>', 200
    apps = integration_api.shortlisted_for_staff(user.get("user_id"))
    scheduled = _scheduled_application_ids()
    apps = [a for a in apps if str(a.get("application_id")) not in scheduled]
    search = request.args.get("search", "").strip().lower()
    if search:
        apps = [
            a for a in apps
            if search in f"{a.get('applicant_name', '')} {a.get('application_id', '')}".lower()
        ]
    return fmt.render_schedulable_rows(apps), 200


@interviews_bp.get("/ui/schedule/options")
def ui_schedule_options():
    user, err = require_session()
    if err:
        return err
    if user.get("role") != "staff":
        return '<option value="">Staff only</option>', 200
    apps = integration_api.shortlisted_for_staff(user.get("user_id"))
    scheduled = _scheduled_application_ids()
    apps = [a for a in apps if str(a.get("application_id")) not in scheduled]
    return fmt.render_schedule_options(apps), 200


@interviews_bp.get("/ui/to-complete/rows")
def ui_to_complete_rows():
    user, err = require_session()
    if err:
        return err
    if user.get("role") != "staff":
        return '<div class="empty-state">Staff only.</div>', 200
    try:
        interviews = _all_enriched()
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load interviews.</div>', 200
    interviews = [
        i for i in interviews
        if i.get("application_status") == STATUS_SCHEDULED and _is_past(i.get("interview_datetime"))
    ]
    search = request.args.get("search", "").strip().lower()
    if search:
        interviews = [
            i for i in interviews
            if search in f"{i.get('applicant_name', '')} {i.get('application_id', '')}".lower()
        ]
    return fmt.render_to_complete_rows(interviews), 200


@interviews_bp.get("/ui/requests")
def ui_requests():
    user, err = require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load requests.</div>', 200
    return fmt.render_requests(interviews, backend_url=BACKEND_PUBLIC_URL), 200


@interviews_bp.get("/ui/interviews/<int:interview_id>/detail")
def ui_interview_detail(interview_id):
    user, err = require_session()
    if err:
        return err
    try:
        response = get_interview_response(interview_id)
        if response.status_code == 404:
            return '<div class="empty-state">This interview is not available to you.</div>', 200
        response.raise_for_status()
        interview = integration_api.enrich_one(response.json())
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load interview.</div>', 200

    if user.get("role") != "staff" and str(interview.get("applicant_id")) != str(user.get("user_id")):
        return '<div class="empty-state">This interview is not available to you.</div>', 200

    is_past = _is_past(interview.get("interview_datetime"))
    return (
        fmt.render_interview_detail(
            interview, user.get("role"), backend_url=BACKEND_PUBLIC_URL, is_past=is_past
        ),
        200,
    )
