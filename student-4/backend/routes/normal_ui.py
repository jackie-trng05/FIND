from datetime import datetime

from flask import Blueprint, jsonify, request
import requests

from services.database_api import (
    create_interview,
    delete_interview,
    get_interview_response,
    get_interviews_response,
    update_interview,
)
from services import integration_api


normal_ui_bp = Blueprint("normal_ui", __name__)

# Interview statuses mirror the linked application's status (Student 3).
STATUS_SHORTLISTED = "Shortlisted"                 # shortlisted, no invite sent yet
STATUS_REQUESTED = "Interview Requested"           # invite sent, awaiting applicant
STATUS_SCHEDULED = "Interview Scheduled"           # applicant accepted
STATUS_RESCHEDULE_REQUESTED = "Reschedule Requested"  # applicant proposed a new time
STATUS_COMPLETED = "Interview Completed"           # staff marked complete
STATUS_WITHDRAWN = "Withdrawn"                     # applicant declined

VALID_STATUSES = {
    STATUS_SHORTLISTED,
    STATUS_REQUESTED,
    STATUS_SCHEDULED,
    STATUS_RESCHEDULE_REQUESTED,
    STATUS_COMPLETED,
    STATUS_WITHDRAWN,
}

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


def _valid_link(value):
    value = (value or "").strip()
    return value == "" or value.startswith("http://") or value.startswith("https://")


@normal_ui_bp.get("/")
def health():
    return jsonify({"service": "student-4-interview-service", "status": "running"})


@normal_ui_bp.get("/interviews")
def list_interviews():
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


@normal_ui_bp.get("/interviews/<int:interview_id>")
def get_interview(interview_id):
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
    data = request.get_json(silent=True) or {}

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
    return jsonify(integration_api.enrich_one(interview)), 201


@normal_ui_bp.put("/interviews/<int:interview_id>")
def update_interview_route(interview_id):
    data = request.get_json(silent=True) or {}
    payload = {}
    errors = {}

    if "interview_datetime" in data:
        value = str(data["interview_datetime"]).strip()
        if not _valid_datetime(value):
            errors["interview_datetime"] = "Use the format YYYY-MM-DD HH:MM."
        elif not _is_future(value):
            errors["interview_datetime"] = "Interview date/time must be in the future."
        else:
            payload["interview_datetime"] = value

    if "interview_link" in data:
        value = str(data["interview_link"]).strip()
        if not _valid_link(value):
            errors["interview_link"] = "Link must start with http:// or https://."
        else:
            payload["interview_link"] = value

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
    return _apply_update(
        interview_id, {"interview_status": STATUS_SCHEDULED}, app_status=STATUS_SCHEDULED
    )


@normal_ui_bp.post("/interviews/<int:interview_id>/decline")
def decline_interview(interview_id):
    """Applicant declines the request -> application is Withdrawn."""
    data = request.get_json(silent=True) or {}
    notes = str(data.get("reason", "")).strip()
    payload = {"interview_status": STATUS_WITHDRAWN}
    if notes:
        payload["interview_notes"] = notes
    return _apply_update(interview_id, payload, app_status=STATUS_WITHDRAWN)


@normal_ui_bp.post("/interviews/<int:interview_id>/complete")
def complete_interview(interview_id):
    """Staff marks the interview complete -> Interview Completed."""
    return _apply_update(
        interview_id, {"interview_status": STATUS_COMPLETED}, app_status=STATUS_COMPLETED
    )


@normal_ui_bp.post("/interviews/<int:interview_id>/reschedule")
def reschedule_interview(interview_id):
    """Applicant proposes a new time -> "Reschedule Requested" (awaits staff).

    The interview keeps the proposed time and moves to "Reschedule Requested"
    (and so does the application) until a staff member accepts (Interview
    Scheduled) or declines (back to Shortlisted) it.
    """
    data = request.get_json(silent=True) or {}
    new_datetime = str(data.get("interview_datetime", "")).strip()
    reason = str(data.get("reason", "")).strip()

    errors = {}
    if not _valid_datetime(new_datetime):
        errors["interview_datetime"] = "Use the format YYYY-MM-DD HH:MM."
    elif not _is_future(new_datetime):
        errors["interview_datetime"] = "Proposed date/time must be in the future."
    if errors:
        return jsonify({"errors": errors}), 400

    payload = {
        "interview_datetime": new_datetime,
        "interview_status": STATUS_RESCHEDULE_REQUESTED,
    }
    if reason:
        payload["interview_notes"] = reason
    return _apply_update(interview_id, payload, app_status=STATUS_RESCHEDULE_REQUESTED)


@normal_ui_bp.post("/interviews/<int:interview_id>/accept-reschedule")
def accept_reschedule(interview_id):
    """Staff accepts the proposed time -> Interview Scheduled."""
    return _apply_update(
        interview_id, {"interview_status": STATUS_SCHEDULED}, app_status=STATUS_SCHEDULED
    )


@normal_ui_bp.post("/interviews/<int:interview_id>/decline-reschedule")
def decline_reschedule(interview_id):
    """Staff declines the proposed time: cancel the interview and return the
    application to Shortlisted so it reappears in the "To Schedule" tab."""
    try:
        response = get_interview_response(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        interview = response.json()
    except requests.RequestException as exc:
        return _db_error(exc)

    application_id = interview.get("application_id")
    try:
        del_response = delete_interview(interview_id)
        del_response.raise_for_status()
    except requests.RequestException as exc:
        return _db_error(exc)

    integration_api.set_application_status(application_id, STATUS_SHORTLISTED)
    return jsonify({"declined": interview_id, "application_id": application_id}), 200


@normal_ui_bp.delete("/interviews/<int:interview_id>")
def cancel_interview(interview_id):
    try:
        response = delete_interview(interview_id)
        if response.status_code == 404:
            return jsonify({"error": "Interview not found."}), 404
        response.raise_for_status()
        return jsonify({"cancelled": interview_id}), 200
    except requests.RequestException as exc:
        return _db_error(exc)


def _apply_update(interview_id, payload, app_status=None):
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

    return jsonify(integration_api.enrich_one(interview)), 200
