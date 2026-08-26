import json
import os
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
from services.integration_api import get_session_user
from views import html_formatters as fmt


normal_ui_bp = Blueprint("normal_ui", __name__)

# Public (browser-facing) URLs used for HTMX redirects and cross-origin actions.
FRONTEND_ORIGIN = os.getenv("FRONTEND_PUBLIC_URL", "http://localhost:16013")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:16014")

# Interview statuses mirror the linked application's status (Student 3).
STATUS_SHORTLISTED = "Shortlisted"                 # shortlisted, no invite sent yet
STATUS_REQUESTED = "Interview Requested"           # invite sent, awaiting applicant
STATUS_SCHEDULED = "Interview Scheduled"           # applicant accepted
STATUS_COMPLETED = "Interview Completed"           # staff marked complete
STATUS_WITHDRAWN = "Withdrawn"                     # applicant declined

VALID_STATUSES = {
    STATUS_SHORTLISTED,
    STATUS_REQUESTED,
    STATUS_SCHEDULED,
    STATUS_COMPLETED,
    STATUS_WITHDRAWN,
}

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


# --------------------------------------------------------------------------- #
# Session + HTMX helpers                                                       #
# --------------------------------------------------------------------------- #

def _require_session():
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
    """Staff see every interview; applicants only their own."""
    if user.get("role") == "staff":
        return interviews
    uid = str(user.get("user_id"))
    return [i for i in interviews if str(i.get("applicant_id")) == uid]


def _hx_response(triggers=None, redirect=None, status=200):
    resp = Response(status=status)
    if triggers:
        resp.headers["HX-Trigger"] = json.dumps(triggers)
    if redirect:
        resp.headers["HX-Redirect"] = redirect
    return resp


@normal_ui_bp.get("/")
def health():
    return jsonify({"service": "student-4-interview-service", "status": "running"})


@normal_ui_bp.get("/interviews")
def list_interviews():
    _, err = _require_session()
    if err:
        return err
    staff_id = request.args.get("staff_id", "").strip()
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
    if staff_id:
        interviews = [i for i in interviews if str(i.get("staff_id")) == staff_id]
    if applicant_id:
        interviews = [i for i in interviews if str(i.get("applicant_id")) == applicant_id]
    if status:
        interviews = [i for i in interviews if str(i.get("interview_status")) == status]

    return jsonify(interviews), 200


@normal_ui_bp.get("/interviews/to-complete")
def interviews_to_complete():
    """Scheduled interviews whose time has passed and still need notes.

    These are the interviews a staff member must write up (all five skill
    notes) to move them to "Interview Completed".
    """
    _, err = _require_session()
    if err:
        return err
    staff_id = request.args.get("staff_id", "").strip()

    try:
        response = get_interviews_response({})
        response.raise_for_status()
        interviews = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    interviews = [
        i for i in interviews
        if str(i.get("interview_status")) == STATUS_SCHEDULED
        and _is_past(i.get("interview_datetime"))
    ]
    interviews = integration_api.enrich_interviews(interviews)

    if staff_id:
        interviews = [i for i in interviews if str(i.get("staff_id")) == staff_id]

    return jsonify(interviews), 200


@normal_ui_bp.get("/interviews/<int:interview_id>")
def get_interview(interview_id):
    _, err = _require_session()
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


@normal_ui_bp.get("/schedulable-applications")
def schedulable_applications():
    """Shortlisted applications a staff member still needs to interview.

    Applications come from Student 3; postings ownership from Student 2.
    Applications that already have an interview request are filtered out.
    """
    _, err = _require_session()
    if err:
        return err
    staff_id = request.args.get("staff_id", "").strip()
    if not _positive_int(staff_id):
        return jsonify({"error": "A valid staff_id is required."}), 400

    applications = integration_api.shortlisted_for_staff(staff_id)

    scheduled = _scheduled_application_ids()
    applications = [
        app for app in applications
        if str(app.get("application_id")) not in scheduled
    ]
    return jsonify({"applications": applications}), 200


def _scheduled_application_ids():
    """Application IDs that already have an interview request."""
    try:
        response = get_interviews_response({})
        response.raise_for_status()
        interviews = response.json()
    except requests.RequestException:
        return set()
    return {str(row.get("application_id")) for row in interviews}


@normal_ui_bp.post("/interviews")
def schedule_interview():
    user, err = _require_session()
    if err:
        return err
    data = _read_input()

    errors = {}
    application_id = str(data.get("application_id", "")).strip()
    staff_id = str(data.get("staff_id", "")).strip()
    interview_datetime = str(data.get("interview_datetime", "")).strip()
    interview_link = str(data.get("interview_link", "")).strip()
    interview_notes = str(data.get("interview_notes", "")).strip()

    if not _positive_int(application_id):
        errors["application_id"] = "Application ID must be a positive number."
    if not _positive_int(staff_id):
        errors["staff_id"] = "Staff ID is required."
    if not _valid_datetime(interview_datetime):
        errors["interview_datetime"] = "Use the format YYYY-MM-DD HH:MM."
    elif not _is_future(interview_datetime):
        errors["interview_datetime"] = "Interview date/time must be in the future."
    if not _valid_link(interview_link):
        errors["interview_link"] = "Link must start with http:// or https://."

    if errors:
        if _wants_hx():
            return _hx_response(triggers={
                "showErrorToast": "Please check the form and try again."
            })
        return jsonify({"errors": errors}), 400

    payload = {
        "application_id": application_id,
        "staff_id": staff_id,
        "interview_datetime": interview_datetime,
        "interview_link": interview_link,
        "interview_status": STATUS_REQUESTED,
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
            redirect=f"{FRONTEND_ORIGIN}/?toast={quote('Interview scheduled.')}"
        )
    return jsonify(integration_api.enrich_one(interview)), 201


@normal_ui_bp.put("/interviews/<int:interview_id>")
def update_interview_route(interview_id):
    """Update mutable interview fields.

    Interview *details* (date/time, meeting link) are fixed once created — the
    only things staff can update afterwards are the assessment notes (and, via
    that, the status). Date/time and link edits are rejected.
    """
    _, err = _require_session()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    payload = {}
    errors = {}

    if "interview_datetime" in data or "interview_link" in data:
        errors["interview_details"] = (
            "Interview details cannot be changed after the interview is created."
        )

    new_status = None
    if "interview_status" in data:
        value = str(data["interview_status"]).strip()
        if value and value not in VALID_STATUSES:
            errors["interview_status"] = "Unknown status."
        elif value:
            payload["interview_status"] = value
            new_status = value

    if "interview_notes" in data:
        payload["interview_notes"] = str(data["interview_notes"]).strip()

    if errors:
        return jsonify({"errors": errors}), 400
    if not payload:
        return jsonify({"error": "No update details provided."}), 400

    return _apply_update(interview_id, payload, app_status=new_status)


@normal_ui_bp.post("/interviews/<int:interview_id>/accept")
def accept_interview(interview_id):
    """Applicant accepts the request -> Interview Scheduled."""
    _, err = _require_session()
    if err:
        return err
    return _apply_update(
        interview_id,
        {"interview_status": STATUS_SCHEDULED},
        app_status=STATUS_SCHEDULED,
        hx_success={"triggers": {
            "showToast": "Interview accepted.",
            "interviewChanged": True,
            "requestsChanged": True,
        }},
    )


@normal_ui_bp.post("/interviews/<int:interview_id>/decline")
def decline_interview(interview_id):
    """Applicant declines the request -> application is Withdrawn."""
    _, err = _require_session()
    if err:
        return err
    data = _read_input()
    notes = str(data.get("reason", "")).strip()
    payload = {"interview_status": STATUS_WITHDRAWN}
    if notes:
        payload["interview_notes"] = notes
    return _apply_update(
        interview_id,
        payload,
        app_status=STATUS_WITHDRAWN,
        hx_success={"redirect": f"{FRONTEND_ORIGIN}/requests?toast={quote('Interview declined. Application withdrawn.')}"},
    )


@normal_ui_bp.post("/interviews/<int:interview_id>/complete")
def complete_interview(interview_id):
    """Record assessment notes and mark the interview complete.

    Completing is only allowed once the interview has actually taken place
    (its date/time is in the past) and the applicant has accepted it
    (status "Interview Scheduled"). All five skill-area notes are required —
    saving them is what moves the interview to "Interview Completed".
    """
    _, err = _require_session()
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
        interview = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    if interview.get("interview_status") != STATUS_SCHEDULED:
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
        "interview_status": STATUS_COMPLETED,
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


@normal_ui_bp.delete("/interviews/<int:interview_id>")
def cancel_interview(interview_id):
    _, err = _require_session()
    if err:
        return err
    try:
        response = delete_interview(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
    except requests.RequestException as exc:
        return _db_error(exc)

    if _wants_hx():
        return _hx_response(
            redirect=f"{FRONTEND_ORIGIN}/list?toast={quote('Interview cancelled.')}"
        )
    return jsonify({"cancelled": interview_id}), 200


def _apply_update(interview_id, payload, app_status=None, hx_success=None):
    try:
        response = update_interview(interview_id, payload)
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


@normal_ui_bp.get("/ui/calendar")
def ui_calendar():
    user, err = _require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        interviews = []

    now = datetime.now()
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    if not year or not month:
        dts = sorted(
            d for d in (fmt._parse_dt(i.get("interview_datetime")) for i in interviews) if d
        )
        anchor = next((d for d in dts if d >= now), None) or (dts[0] if dts else now)
        year, month = anchor.year, anchor.month
    return fmt.render_calendar(interviews, year, month, backend_url=BACKEND_PUBLIC_URL), 200


@normal_ui_bp.get("/ui/interviews/rows")
def ui_interview_rows():
    user, err = _require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load interviews.</div>', 200

    status = request.args.get("status", "").strip()
    job_posting = request.args.get("job_posting", "").strip()
    date_from = _parse_date_only(request.args.get("from", "").strip())
    date_to = _parse_date_only(request.args.get("to", "").strip())
    search = request.args.get("search", "").strip().lower()
    sort = request.args.get("sort", "datetime")
    direction = request.args.get("dir", "asc")

    def _keep(it):
        if status and str(it.get("interview_status")).lower() != status.lower():
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


@normal_ui_bp.get("/ui/applications/rows")
def ui_applications_rows():
    user, err = _require_session()
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


@normal_ui_bp.get("/ui/schedule/options")
def ui_schedule_options():
    user, err = _require_session()
    if err:
        return err
    if user.get("role") != "staff":
        return '<option value="">Staff only</option>', 200
    apps = integration_api.shortlisted_for_staff(user.get("user_id"))
    scheduled = _scheduled_application_ids()
    apps = [a for a in apps if str(a.get("application_id")) not in scheduled]
    return fmt.render_schedule_options(apps), 200


@normal_ui_bp.get("/ui/to-complete/rows")
def ui_to_complete_rows():
    user, err = _require_session()
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
        if i.get("interview_status") == STATUS_SCHEDULED and _is_past(i.get("interview_datetime"))
    ]
    search = request.args.get("search", "").strip().lower()
    if search:
        interviews = [
            i for i in interviews
            if search in f"{i.get('applicant_name', '')} {i.get('application_id', '')}".lower()
        ]
    return fmt.render_to_complete_rows(interviews), 200


@normal_ui_bp.get("/ui/requests")
def ui_requests():
    user, err = _require_session()
    if err:
        return err
    try:
        interviews = _scope_to_user(_all_enriched(), user)
    except requests.RequestException:
        return '<div class="alert alert-error">Failed to load requests.</div>', 200
    return fmt.render_requests(interviews, backend_url=BACKEND_PUBLIC_URL), 200


@normal_ui_bp.get("/ui/interviews/<int:interview_id>/detail")
def ui_interview_detail(interview_id):
    user, err = _require_session()
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
